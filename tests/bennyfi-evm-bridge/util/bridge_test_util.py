from datetime import datetime
import json
import logging
import time
from typing import Callable
import pytest
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import (
    ChecksumAddress,
)

# from w3multicall.multicall import W3Multicall

from pathlib import Path
from leap.sugar import random_string
from leap.protocol import Asset
from tevmc.testing import open_web3
from tevmc.cleos_evm import CLEOSEVM

from tevmc.utils import to_wei
from web3.middleware.signing import construct_sign_and_send_raw_middleware
from web3 import Web3
from util.evm_transaction_signer import EVMTransactionSigner
from util.token import Token
from util.token_test_util import TokenTestUtil
from util.balances import Balances
from enum import Enum


class BridgeEVMToZeroStage(Enum):
    REQUEST_CREATED = 1
    REQUEST_PROCESSED = 2
    PROCESSED_REQUEST_NOTIFIED = 3
    REQUEST_COMPLETED = 4

class BridgeTestUtil:
    def __init__(self, bbf) -> None:
        self.bbf = bbf
        self.cleos: CLEOSEVM = bbf.cleos

    def assert_bridge_evm_to_zero(
        self,
        e_user: LocalAccount,
        z_user: str,
        token: Token,
        z_amount: int,
        stage: BridgeEVMToZeroStage = BridgeEVMToZeroStage.REQUEST_COMPLETED,
    ):
        tevmc = self.bbf.tevmc
        local_w3: Web3 = self.bbf.local_w3
        evm_transaction_signer = self.bbf.evm_transaction_signer

        e_user_balance = token.e_balance(e_user.address)
        z_user_balance = token.z_balance(z_user)
        e_bridge_balance = self.bbf.bridge_e_contract.functions.tokenBalances(
            token.contract.address
        ).call()
        z_bridge_eth_balance = local_w3.eth.get_balance(self.bbf.bridge_z_eth_addr)
        z_supply = token.z_supply()
        e_amount = token.z_to_e_amount(z_amount)
        self.cleos.logger.info(
            f"z user balance: {z_user_balance} z user balance type: {type(z_user_balance)} e user balance: {e_user_balance} bridge balance: {e_bridge_balance} z supply: {z_supply} z supply type: {type(z_supply)} z amount: {z_amount} e amount: {e_amount}"
        )
        self.cleos.logger.info("Set allowance to bridge e...")
        receipt = evm_transaction_signer.transact(
            token.contract,
            "approve",
            e_user.address,
            self.bbf.bridge_e_contract.address,
            e_amount,
        )
        assert receipt

        bridge_request_id = self.bbf.evm_bridge.e_to_z_next_req_id()
        fee = self.bbf.evm_bridge.fee()
        self.cleos.logger.info("Create bridge evm to zero request...")
        result = self.bbf.evm_bridge.bridge_e_to_z(e_user, z_user, token, e_amount, fee)
        assert result
        self.cleos.logger.info(f"receipt: {result['receipt']}")
        expected_event = {
            'bridgeRequestId': bridge_request_id,
            'to': z_user,
            'token': token.contract.address,
            'from': e_user.address,
            'amount': e_amount,
        }
        self.assert_bridge_e_to_z_req_queued_event(result["event"], expected_event)

        expected_bridge_request = {
            'id': bridge_request_id,
            'token': token,
            'from': e_user,
            'amount': e_amount,
            'zeroAmount': z_amount,
            'to': z_user,
            'zeroSymbol': token.z_symbol,
        }
        # assert bridge request
        self.assert_bridge_e_to_z_req(expected_bridge_request)

        # assert balances after request creation
        e_user_balance -= e_amount
        e_bridge_balance += e_amount
        z_bridge_eth_balance += fee
        assert token.e_balance(e_user.address) == e_user_balance, (
            f"e user balance does not match {token.e_balance(e_user.address)} != {e_user_balance}"
        )
        assert (
            token.e_balance(self.bbf.bridge_e_contract.address) == e_bridge_balance
        ), (
            f"e bridge balance does not match {token.e_balance(self.bbf.bridge_e_contract.address)} != {e_bridge_balance}"
        )
        assert self.bbf.evm_bridge.token_balance(token) == e_bridge_balance, (
            f"e bridge tracked token balance does not match {self.bbf.evm_bridge.token_balance(token)} != {e_bridge_balance}"
        )
        assert token.z_balance(z_user) == z_user_balance, (
            f"z user balance does not match {token.z_balance(z_user)} != {z_user_balance}"
        )
        assert token.z_supply() == z_supply, (
            f"z supply does not match {token.z_supply()} != {z_supply}"
        )
        assert (
            local_w3.eth.get_balance(self.bbf.bridge_z_eth_addr) == z_bridge_eth_balance
        ), (
            f"z bridge eth balance does not match {local_w3.eth.get_balance(self.bbf.bridge_z_eth_addr)} != {z_bridge_eth_balance}"
        )
        TokenTestUtil.assert_stats(token, z_supply, self.bbf.bridge_z_account)

        if stage == BridgeEVMToZeroStage.REQUEST_CREATED:
            return expected_bridge_request

        requests = [
                {
                    "request": expected_bridge_request,
                    "refund_reason": "",
                }
            ]
        self.assert_process_bridge_evm_to_zero_reqs(requests)

        if stage == BridgeEVMToZeroStage.REQUEST_PROCESSED:
            return expected_bridge_request
        
        self.assert_notify_processed_bridge_evm_to_zero_reqs(requests)

        if stage == BridgeEVMToZeroStage.PROCESSED_REQUEST_NOTIFIED:
            return expected_bridge_request

        self.assert_remove_processed_bridge_evm_to_zero_reqs(requests)

        return expected_bridge_request

    def assert_process_bridge_evm_to_zero_reqs(
        self,
        requests: list[dict],
        check_already_processed: bool = False
    ):    
        self.cleos.logger.info("Process bridge evm to zero requests...")
        already_processed = {}
        if check_already_processed:
            already_processed = self.bbf.zero_bridge.get_processed_bridge_e_to_z_requests_map()
        balances = Balances(self.bbf)
        reqs = [request["request"] for request in requests]
        balances.load_balances(reqs, "to", "from")
        result = self.bbf.zero_bridge.process_e_to_z_reqs()
        self.cleos.logger.info(json.dumps(result, indent=4))

        
        # Update expected balances and supplies, assert requests
        for request in requests:
            bridge_req = request["request"]
            token = bridge_req["token"]
            if request["refund_reason"] == "" and bridge_req["id"] not in already_processed:
                balances.update_zero_balance(bridge_req["to"], token, bridge_req["zeroAmount"])
                balances.update_supply(token, bridge_req["zeroAmount"])

            expected_processed_req = {
                'call_id': bridge_req["id"],
                'state': 'completed' if request["refund_reason"] == "" else 'mustrefund',
                'refund_reason': request["refund_reason"],
            }
            self.assert_processed_bridge_e_to_z_req(expected_processed_req)
            self.assert_bridge_e_to_zero_req_exists(bridge_req["id"])

        balances.assert_balances()

    def assert_notify_processed_bridge_evm_to_zero_reqs(
        self,
        requests: list[dict],
        check_notified: bool = False
    ):
        self.cleos.logger.info("Notify processed bridge evm to zero request...")

        balances = Balances(self.bbf)
        reqs = [request["request"] for request in requests]
        balances.load_balances(reqs, "to", "from")
        balances.add_evm_balances(self.bbf.bridge_e_contract)

        already_notified = {}
        if check_notified:
            for request in requests:
                if not self.bbf.evm_bridge.e_to_z_req_by_id(request["request"]["id"]):
                    already_notified[request["request"]["id"]] = True

        result = self.bbf.zero_bridge.notify_processed_e_to_z_reqs()
        self.cleos.logger.info(json.dumps(result, indent=4))

        completed_events = []
        refunded_events = []
        for request in requests:
            bridge_req = request["request"]
            token = bridge_req["token"]
            id = bridge_req["id"]
            expected_event = {
                'bridgeRequestId': id,
                'to': bridge_req["to"],
                'token': token.contract.address,
                'from': bridge_req["from"].address,
                'amount': bridge_req["amount"],
            }
            if id not in already_notified:
                if request["refund_reason"] != "":
                    balances.update_evm_balance(bridge_req["from"], token, bridge_req["amount"])
                    balances.update_evm_balance(self.bbf.bridge_e_contract, token, -1 * bridge_req["amount"])
                    expected_event['reason'] = request["refund_reason"]
                    refunded_events.append(expected_event)
                else:
                    completed_events.append(expected_event)
            self.assert_bridge_e_to_zero_req_exists(id, exists=False)
            self.assert_processed_bridge_e_to_zero_req_exists(
                id
            )

        balances.assert_balances()
        self.assert_bridge_e_to_z_req_completed_events(completed_events)
        self.assert_bridge_e_to_z_refund_completed_events(refunded_events)

    def assert_remove_processed_bridge_evm_to_zero_reqs(
        self,
        requests: list[dict],
        check_notified: bool = False
    ):    
        self.cleos.logger.info("Remove processed bridge evm to zero request...")
        result = self.bbf.zero_bridge.remove_processed_e_to_z_reqs()
        self.cleos.logger.info(json.dumps(result, indent=4))

        exists = False
        for request in requests:
            id = request["request"]["id"]
            if check_notified and self.bbf.evm_bridge.e_to_z_req_by_id(id):
                exists = True
            self.assert_processed_bridge_e_to_zero_req_exists(
                id, exists
            )

    def assert_bridge_e_to_z_req(self, expected: dict):
        actual = self.bbf.evm_bridge.e_to_z_req_by_id(expected["id"])
        assert actual is not None, f"bridge evm to zero request with id {expected['id']} does not exist"
        self.cleos.logger.info(f"bridge evm to zero request: {actual}")
        assert actual[0] == expected["id"], (
            f"evm to zero request ids does not match {actual[0]} != {expected['id']}"
        )
        assert actual[1] == expected["token"].contract.address, (
            f"token address does not match {actual[1]} != {expected['token'].contract.address}"
        )
        assert actual[2] == expected["from"].address, (
            f"sender address does not match {actual[2]} != {expected['user'].address}"
        )
        assert actual[3] == expected["amount"], (
            f"amount does not match {actual[3]} != {expected['amount']}"
        )
        assert actual[4] == expected["zeroAmount"], (
            f"zero amount does not match {actual[4]} != {expected['zeroAmount']}"
        )
        assert actual[5] == expected["to"], (
            f"zero user does not match {actual[5]} != {expected['to']}"
        )
        self.assert_is_recent_date(actual[6])
        assert actual[7] == expected["zeroSymbol"], (
            f"zero symbol does not match {actual[6]} != {expected['zeroSymbol']}"
        )
    


    def assert_bridge_e_to_z_req_queued_event(self, actual: dict, expected: dict):
        self.assert_bridge_e_to_z_req_base_event(actual, expected, "BridgeEVMToZeroRequestQueued")

    def assert_bridge_e_to_z_req_completed_events(self, expected_events: list[dict]):
        self.assert_events(expected_events, "BridgeEVMToZeroRequestCompleted", self.assert_bridge_e_to_z_req_completed_event)
    
    def assert_events(self, expected_events: list[dict], event_name: str, assert_method: Callable[[dict, dict], None]):
        if len(expected_events) == 0:
            return
        actual_events = self.bbf.evm_bridge.get_events(event_name, len(expected_events))
        for actual, expected in zip(actual_events, expected_events):
            assert_method(actual, expected)

    def assert_bridge_e_to_z_req_completed_event(self, actual: dict, expected: dict):
        self.assert_bridge_e_to_z_req_base_event(actual, expected, "BridgeEVMToZeroRequestCompleted")

    def assert_bridge_e_to_z_refund_completed_events(self, expected_events: list[dict]):
        self.assert_events(expected_events, "BridgeEVMToZeroRefundCompleted", self.assert_bridge_e_to_z_refund_completed_event)

    def assert_bridge_e_to_z_refund_completed_event(self, actual: dict, expected: dict):
        self.assert_bridge_e_to_z_req_base_event(actual, expected, "BridgeEVMToZeroRefundCompleted")
        assert actual["args"]["reason"] == expected["reason"], (
            f"refund reason for evm to zero refund completed event does not match {actual['args']['reason']} != {expected['reason']} request id: {expected['bridgeRequestId']}")
    
    def assert_bridge_e_to_z_req_base_event(self, actual: dict, expected: dict, event_name: str):
        self.cleos.logger.info(f"event: {actual}")
        context = f"Request id: {expected['bridgeRequestId']}"
        assert actual["event"] == event_name, (
            f"event name does not match {actual['event']} != {expected['event']} {context}"
        )
        args = actual["args"]
        assert args["bridgeRequestId"] == expected["bridgeRequestId"], (
            f"evm to zero request ids does not match {args['bridgeRequestId']} != {expected['bridgeRequestId']}"
        )
        # assert args["to"] == self.bbf.local_w3.keccak(text=expected["to"]), (
        #     f"to account does not match {args['to']} != {self.bbf.local_w3.keccak(text=expected['to'])}"
        # )
        assert args["to"] == expected["to"], (
            f"to account does not match {args['to']} != {expected['to']} {context}"
        )
        assert args["token"] == expected["token"], (
            f"token address does not match {args['token']} != {expected['token']} {context}"
        )
        assert args["from"] == expected["from"], (
            f"from address does not match {args['from']} != {expected['from']} {context}"
        )
        assert args["amount"] == expected["amount"], (
            f"amount does not match {args['amount']} != {expected['amount']} {context}"
        )
    
    def assert_processed_bridge_e_to_z_req(self, expected: dict):
    
        actual = (
            self.bbf.zero_bridge.get_processed_bridge_e_to_z_request(expected["call_id"])
        )
        assert actual is not None, (
            f"processed bridge evm to zero request with call id {expected['call_id']} does not exist"
        )
        assert int(actual["call_id"]) == expected["call_id"], (
            f"processed bridge evm to zero request call id does not match {int(actual['call_id'])} != {expected['call_id']}"
        )
        assert actual["state"] == expected["state"], (
            f"processed bridge evm to zero request state does not match {actual['state']} != {expected['state']}"
        )
        assert actual["refund_reason"] == expected["refund_reason"], (
            f"processed bridge evm to zero request refund reason does not match {actual['refund_reason']} != {expected['refund_reason']}"
        )
        self.assert_is_recent_date(actual["timestamp"])

    def assert_bridge_e_to_zero_req_exists(
        self, bridge_request_id: int, exists: bool = True
    ):
        request = self.bbf.evm_bridge.e_to_z_req_by_id(bridge_request_id)
        if exists:
            assert request is not None, (
                f"bridge evm to zero request with id {bridge_request_id} does not exist"
            )
        else:
            assert request is None, (
                f"bridge evm to zero request with id {bridge_request_id} exists"
            )

    def assert_processed_bridge_e_to_zero_req_exists(
        self, call_id: int, exists: bool = True
    ):
        request = self.bbf.zero_bridge.get_processed_bridge_e_to_z_request(call_id)
        if exists:
            assert request is not None, (
                f"processed bridge evm to zero request with call_id {call_id} does not exist"
            )
        else:
            assert request is None, (
                f"processed bridge evm to zero request with call_id {call_id} exists"
            )

    def assert_bridge_zero_to_evm(
        self,
        z_user: str,
        e_user: LocalAccount,
        token: Token,
        z_amount: int,
    ):
        tevmc = self.bbf.tevmc
        e_user_balance = token.e_balance(e_user.address)
        z_user_balance = token.z_balance(z_user)
        e_bridge_balance = self.bbf.bridge_e_contract.functions.tokenBalances(
            token.contract.address
        ).call()
        z_supply = token.z_supply()
        e_amount = token.z_to_e_amount(z_amount)
        asset_amount = token.to_asset(z_amount)
        self.cleos.logger.info(
            f"z user balance: {z_user_balance} z user balance type: {type(z_user_balance)} e user balance: {e_user_balance} bridge balance: {e_bridge_balance} z supply: {z_supply} z supply type: {type(z_supply)} z amount: {z_amount} e amount: {e_amount}"
        )

        result = self.bbf.zero_bridge.bridge_z_to_e(
            z_user, e_user.address, str(asset_amount)
        )
        self.cleos.logger.info(json.dumps(result, indent=4))

        e_user_balance += e_amount
        e_bridge_balance -= e_amount
        z_user_balance.amount -= z_amount
        z_supply.amount -= z_amount
        assert token.e_balance(e_user.address) == e_user_balance
        assert token.e_balance(self.bbf.bridge_e_contract.address) == e_bridge_balance
        assert (
            self.bbf.bridge_e_contract.functions.tokenBalances(
                token.contract.address
            ).call()
            == e_bridge_balance
        )
        assert token.z_balance(z_user) == z_user_balance
        assert token.z_supply() == z_supply
        TokenTestUtil.assert_stats(token, z_supply, self.bbf.bridge_z_account)
        self.assert_bridge_request(z_user, e_user, str(asset_amount), "completed")

    def assert_stake(
        self,
        pool_id: int,
        yield_source: str,
        token: Token,
        z_amount: int,
        staking_period_hrs: int,
    ):
        tevmc = self.bbf.tevmc
        mock_yield_source_adaptor_balance = token.e_balance(
            self.bbf.mock_yield_source_adaptor.address
        )
        stake_local_balance = token.z_balance(self.bbf.stake_local_account)
        e_bridge_balance = self.bbf.bridge_e_contract.functions.tokenBalances(
            token.contract.address
        ).call()
        z_supply = token.z_supply()
        e_amount = token.z_to_e_amount(z_amount)
        asset_amount = token.to_asset(z_amount)

        result = self.bbf.zero_bridge.stake(
            pool_id, yield_source, asset_amount, staking_period_hrs
        )
        self.cleos.logger.info(json.dumps(result, indent=4))

        mock_yield_source_adaptor_balance += e_amount
        e_bridge_balance -= e_amount
        stake_local_balance.amount -= z_amount
        z_supply.amount -= z_amount
        assert (
            token.e_balance(self.bbf.mock_yield_source_adaptor.address)
            == mock_yield_source_adaptor_balance
        )
        assert token.e_balance(self.bbf.bridge_e_contract.address) == e_bridge_balance
        assert (
            self.bbf.bridge_e_contract.functions.tokenBalances(
                token.contract.address
            ).call()
            == e_bridge_balance
        )
        assert token.z_balance(self.bbf.stake_local_account) == stake_local_balance
        assert token.z_supply() == z_supply
        TokenTestUtil.assert_stats(token, z_supply, self.bbf.bridge_z_account)
        self.assert_stake_request(
            pool_id, yield_source, str(asset_amount), staking_period_hrs, "completed"
        )
        self.assert_stake_info(
            pool_id, yield_source, token, e_amount, staking_period_hrs
        )

    def assert_unstake(
        self,
        pool_id: int,
        yield_source: str,
        token: Token,
        z_amount: int,
    ):
        tevmc = self.bbf.tevmc
        evm_transaction_signer = self.bbf.evm_transaction_signer

        mock_yield_source_adaptor_balance = token.e_balance(
            self.bbf.mock_yield_source_adaptor.address
        )
        stake_local_balance = token.z_balance(self.bbf.stake_local_account)
        e_bridge_balance = self.bbf.bridge_e_contract.functions.tokenBalances(
            token.contract.address
        ).call()
        z_supply = token.z_supply()
        e_amount = token.z_to_e_amount(z_amount)
        # self.cleos.logger.info("Set allowance to bridge e...")
        # receipt = evm_transaction_signer.transact(
        #     token.contract,
        #     "approve",
        #     self.bbf.mock_yield_source_adaptor.address,
        #     self.bbf.bridge_e_contract.address,
        #     e_amount,
        # )
        # assert receipt

        self.cleos.logger.info("Trigger Unstake...")
        receipt = evm_transaction_signer.transact(
            self.bbf.mock_yield_source_adaptor,
            "triggerUnstake",
            self.bbf.e_accounts[0].address,
            yield_source,
            pool_id,
            token.contract.address,
            e_amount,
            self.bbf.bridge_e_contract.address,
        )
        assert receipt

        mock_yield_source_adaptor_balance -= e_amount
        e_bridge_balance += e_amount
        stake_local_balance.amount += z_amount
        z_supply.amount += z_amount
        assert (
            token.e_balance(self.bbf.mock_yield_source_adaptor.address)
            == mock_yield_source_adaptor_balance
        )
        assert token.e_balance(self.bbf.bridge_e_contract.address) == e_bridge_balance
        assert (
            self.bbf.bridge_e_contract.functions.tokenBalances(
                token.contract.address
            ).call()
            == e_bridge_balance
        )
        assert token.z_balance(self.bbf.stake_local_account) == stake_local_balance
        assert token.z_supply() == z_supply
        TokenTestUtil.assert_stats(token, z_supply, self.bbf.bridge_z_account)
        self.assert_unstake_info(pool_id, token.to_asset(z_amount))

    def assert_bridge_request(
        self,
        fromAccount: str,
        to: LocalAccount,
        quantity: Asset,
        state: str,
    ):
        actual = self.bbf.zero_bridge.get_last_bridge_z_to_e_request()

        assert actual is not None
        assert actual["from"] == str(fromAccount)
        assert actual["to"] == to.address[2:].lower()
        assert actual["quantity"] == str(quantity)
        assert actual["state"] == state

    def assert_stake_request(
        self,
        pool_id: int,
        yield_source: str,
        quantity: Asset,
        staking_period_hrs: int,
        state: str,
    ):
        actual = self.bbf.zero_bridge.get_last_stake_request()

        assert actual is not None
        assert actual["pool_id"] == pool_id
        assert actual["yield_source"] == yield_source
        assert actual["quantity"] == str(quantity)
        assert actual["staking_period_hrs"] == staking_period_hrs
        assert actual["state"] == state

    def assert_stake_info(
        self,
        pool_id: int,
        yield_source: str,
        token: Token,
        amount: int,
        staking_period_hrs: int,
    ):
        actual = self.bbf.mock_yield_source_adaptor.functions.lastStakeInfo().call()
        self.cleos.logger.info(
            f"In assert_stake_info, results: {json.dumps(actual, indent=4)}"
        )
        assert actual[0] == pool_id
        assert actual[1] == yield_source
        assert actual[2] == token.contract.address
        assert actual[3] == amount
        assert actual[4] == staking_period_hrs

    def assert_unstake_info(self, pool_id: int, amount: Asset):
        results = self.cleos.get_table(
            self.bbf.stake_local_account, self.bbf.stake_local_account, "unstakeinfo"
        )
        self.cleos.logger.info(
            f"In assert_unstake_info, results: {json.dumps(results, indent=4)}"
        )
        assert len(results) == 1
        actual = results[0]
        assert actual["from"] == self.bbf.bridge_z_account
        assert actual["amount"] == str(amount)
        assert actual["memo"] == f"pool id: {pool_id}"

    def assert_zero_bridge_config(
        self,
        bridge_e_address: str,
        token_registry_address: str,
        stake_local_account: str,
        refund_delay_period_secs: int,
        batch_size: int,
        version: str,
        admin: str,
        active: bool,
    ):
        actual = self.bbf.zero_bridge.get_config()
        self.cleos.logger.info(f"In zero bridge config: {json.dumps(actual, indent=4)}")
        self.cleos.logger.info(
            f"bridge_e_address: {bridge_e_address}, token_registry_address: {token_registry_address}, stake_local_account: {stake_local_account}, version: {version}, admin: {admin}"
        )
        assert actual is not None
        assert actual["evm_bridge_address"] == bridge_e_address[2:].lower()
        assert (
            actual["evm_token_registry_address"] == token_registry_address[2:].lower()
        )
        assert actual["stake_local_contract"] == stake_local_account
        assert actual["version"] == version
        assert actual["admin"] == admin

    def assert_is_recent_date(self, timestamp: str | int):
        if isinstance(timestamp, str):
            timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
        elif isinstance(timestamp, int):
            timestamp = datetime.fromtimestamp(timestamp)
        else:
            assert False, "timestamp must be a str or int"
        assert (datetime.now() - timestamp).total_seconds() < 10, (
            f"timestamp is older than 10 seconds {timestamp} != {datetime.now().isoformat()}"
        )
