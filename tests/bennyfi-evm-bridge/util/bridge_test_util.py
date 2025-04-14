from datetime import datetime
import json
import logging
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
      event = result['event']
      #   self.cleos.logger.info(f"receipt: {result['receipt']}")
      self.cleos.logger.info(f"event: {event}")
      # assert event was thrown
      assert event["event"] == "BridgeEVMToZeroRequestQueued"
      args = event["args"]
      assert args["bridgeRequestId"] == bridge_request_id, f"evm to zero request ids does not match {args['bridgeRequestId']} != {bridge_request_id}"
      assert args["to"] == self.bbf.local_w3.keccak(text=z_user), f"to account does not match {args['to']} != {self.bbf.local_w3.keccak(text=z_user)}"
      assert args["token"] == token.contract.address, f"token address does not match {args['token']} != {token.contract.address}"
      assert args["sender"] == e_user.address, f"sender address does not match {args['sender']} != {e_user.address}"
      assert args["amount"] == e_amount, f"amount does not match {args['amount']} != {e_amount}"
      self.cleos.logger.info("Validated event")

      # assert bridge request
      bridge_request = self.bbf.evm_bridge.e_to_z_req_by_id(bridge_request_id)
      self.cleos.logger.info(f"bridge request: {bridge_request}") 
      assert bridge_request[0] == bridge_request_id, f"evm to zero request ids does not match {bridge_request[0]} != {bridge_request_id}"
      assert bridge_request[1] == token.contract.address, f"token address does not match {bridge_request[1]} != {token.contract.address}"
      assert bridge_request[2] == e_user.address, f"sender address does not match {bridge_request[2]} != {e_user.address}"
      assert bridge_request[3] == e_amount, f"amount does not match {bridge_request[3]} != {e_amount}"
      assert bridge_request[4] == z_amount, f"zero amount does not match {bridge_request[4]} != {z_amount}"
      assert bridge_request[5] == z_user, f"zero user does not match {bridge_request[5]} != {z_user}"
      self.assert_is_recent_date(bridge_request[6])
      assert bridge_request[7] == token.z_symbol, f"zero symbol does not match {bridge_request[6]} != {token.z_symbol}"
      
      # assert balances after request creation
      e_user_balance -= e_amount
      e_bridge_balance += e_amount
      z_bridge_eth_balance += fee
      assert token.e_balance(e_user.address) == e_user_balance, f"e user balance does not match {token.e_balance(e_user.address)} != {e_user_balance}"
      assert token.e_balance(self.bbf.bridge_e_contract.address) == e_bridge_balance, f"e bridge balance does not match {token.e_balance(self.bbf.bridge_e_contract.address)} != {e_bridge_balance}"
      assert (
          self.bbf.evm_bridge.token_balance(token) == e_bridge_balance
      ), f"e bridge tracked token balance does not match {self.bbf.evm_bridge.token_balance(token)} != {e_bridge_balance}"
      assert token.z_balance(z_user) == z_user_balance, f"z user balance does not match {token.z_balance(z_user)} != {z_user_balance}"
      assert token.z_supply() == z_supply, f"z supply does not match {token.z_supply()} != {z_supply}"
      assert local_w3.eth.get_balance(self.bbf.bridge_z_eth_addr) == z_bridge_eth_balance, f"z bridge eth balance does not match {local_w3.eth.get_balance(self.bbf.bridge_z_eth_addr)} != {z_bridge_eth_balance}"
      self.assert_stats(token, z_supply), "z supply does not match"

      self.cleos.logger.info("Process bridge evm to zero request...")
      result = self.bbf.zero_bridge.process_e_to_z_reqs(bridge_request_id)
      self.cleos.logger.info(json.dumps(result, indent=4))
      z_user_balance.amount += z_amount
      z_supply.amount += z_amount
      assert token.z_balance(z_user) == z_user_balance, f"z user balance does not match {token.z_balance(z_user)} != {z_user_balance}"
      assert token.z_supply() == z_supply, f"z supply does not match {token.z_supply()} != {z_supply}"
      self.assert_stats(token, z_supply), "z supply does not match"

      # assert processed bridge evm to zero request
      processed_bridge_e_to_z_req = self.bbf.zero_bridge.get_last_processed_bridge_e_to_z_request()
      assert processed_bridge_e_to_z_req['id'] == bridge_request_id - 1, f"processed bridge evm to zero request id does not match {processed_bridge_e_to_z_req['id']} != {bridge_request_id - 1}"
      assert int(processed_bridge_e_to_z_req['call_id']) == bridge_request_id, f"processed bridge evm to zero request call id does not match {int(processed_bridge_e_to_z_req['call_id'])} != {bridge_request_id}"
      assert processed_bridge_e_to_z_req['state'] == "completed", f"processed bridge evm to zero request state does not match {processed_bridge_e_to_z_req['state']} != completed"
      assert processed_bridge_e_to_z_req['refund_reason'] == "", f"processed bridge evm to zero request refund reason does not match {processed_bridge_e_to_z_req['refund_reason']} != ''"  
      self.assert_is_recent_date(processed_bridge_e_to_z_req['timestamp'])

      self.assert_bridge_e_to_zero_req_exists(bridge_request_id)

      self.cleos.logger.info("Notify processed bridge evm to zero request...")
      result = self.bbf.zero_bridge.notify_processed_e_to_z_reqs(bridge_request_id)
      self.cleos.logger.info(json.dumps(result, indent=4))
      self.assert_bridge_e_to_zero_req_exists(bridge_request_id, exists=False)
      self.assert_processed_bridge_e_to_zero_req_exists(processed_bridge_e_to_z_req['id'])
      #   Make sure the e user and e bridge balances were not affected as it is not a refund
      assert token.e_balance(e_user.address) == e_user_balance, f"e user balance does not match {token.e_balance(e_user.address)} != {e_user_balance}"
      assert token.e_balance(self.bbf.bridge_e_contract.address) == e_bridge_balance, f"e bridge balance does not match {token.e_balance(self.bbf.bridge_e_contract.address)} != {e_bridge_balance}"
      
      self.cleos.logger.info("Remove processed bridge evm to zero request...")
      result = self.bbf.zero_bridge.remove_processed_e_to_z_reqs(bridge_request_id)
      self.cleos.logger.info(json.dumps(result, indent=4))
      self.assert_processed_bridge_e_to_zero_req_exists(processed_bridge_e_to_z_req['id'], exists=False)
      
      
      

  def assert_bridge_e_to_zero_req_exists(self, bridge_request_id: int, exists: bool = True):
    try:
      self.bbf.evm_bridge.e_to_z_req_by_id(bridge_request_id)
      assert exists, f"bridge evm to zero request with id {bridge_request_id} exists"
    except Exception as e:
      self.cleos.logger.info(f"Bridge evm to zero request not found error:{e}\n--")
      assert not exists, f"bridge evm to zero request with id {bridge_request_id} does not exist"

  def assert_processed_bridge_e_to_zero_req_exists(self, id: int, exists: bool = True):
    request = self.bbf.zero_bridge.get_processed_bridge_e_to_z_request(id)
    if exists:
      assert request is not None, f"processed bridge evm to zero request with id {id} does not exist"
    else:
      assert request is None, f"processed bridge evm to zero request with id {id} exists"

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

      result = self.bbf.zero_bridge.bridge_z_to_e(z_user, e_user.address, str(asset_amount))
      self.cleos.logger.info(json.dumps(result, indent=4))

      e_user_balance += e_amount
      e_bridge_balance -= e_amount
      z_user_balance.amount -= z_amount
      z_supply.amount -= z_amount
      assert token.e_balance(e_user.address) == e_user_balance
      assert token.e_balance(self.bbf.bridge_e_contract.address) == e_bridge_balance
      assert (
          self.bbf.bridge_e_contract.functions.tokenBalances(token.contract.address).call()
          == e_bridge_balance
      )
      assert token.z_balance(z_user) == z_user_balance
      assert token.z_supply() == z_supply
      self.assert_stats(token, z_supply)
      self.assert_bridge_request(z_user, e_user, str(asset_amount), "completed")

  def assert_stake(
      self,
      pool_id: int,
      yield_source: str,
      token: Token,
      z_amount: int,
      staking_period_hrs: int
  ):
      tevmc = self.bbf.tevmc
      mock_yield_source_adaptor_balance = token.e_balance(self.bbf.mock_yield_source_adaptor.address)
      stake_local_balance = token.z_balance(self.bbf.stake_local_account)
      e_bridge_balance = self.bbf.bridge_e_contract.functions.tokenBalances(
          token.contract.address
      ).call()
      z_supply = token.z_supply()
      e_amount = token.z_to_e_amount(z_amount)
      asset_amount = token.to_asset(z_amount)
      
      result = self.bbf.zero_bridge.stake(pool_id, yield_source, asset_amount, staking_period_hrs)
      self.cleos.logger.info(json.dumps(result, indent=4))

      mock_yield_source_adaptor_balance += e_amount
      e_bridge_balance -= e_amount
      stake_local_balance.amount -= z_amount
      z_supply.amount -= z_amount
      assert token.e_balance(self.bbf.mock_yield_source_adaptor.address) == mock_yield_source_adaptor_balance
      assert token.e_balance(self.bbf.bridge_e_contract.address) == e_bridge_balance
      assert (
          self.bbf.bridge_e_contract.functions.tokenBalances(token.contract.address).call()
          == e_bridge_balance
      )
      assert token.z_balance(self.bbf.stake_local_account) == stake_local_balance
      assert token.z_supply() == z_supply
      self.assert_stats(token, z_supply)
      self.assert_stake_request(pool_id, yield_source, str(asset_amount), staking_period_hrs, "completed")
      self.assert_stake_info(pool_id, yield_source, token, e_amount, staking_period_hrs)


  def assert_unstake(
      self,
      pool_id: int,
      yield_source: str,
      token: Token,
      z_amount: int,
  ):
      tevmc = self.bbf.tevmc
      evm_transaction_signer = self.bbf.evm_transaction_signer

      mock_yield_source_adaptor_balance = token.e_balance(self.bbf.mock_yield_source_adaptor.address)
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
      assert token.e_balance(self.bbf.mock_yield_source_adaptor.address) == mock_yield_source_adaptor_balance
      assert token.e_balance(self.bbf.bridge_e_contract.address) == e_bridge_balance
      assert (
          self.bbf.bridge_e_contract.functions.tokenBalances(token.contract.address).call()
          == e_bridge_balance
      )
      assert token.z_balance(self.bbf.stake_local_account) == stake_local_balance
      assert token.z_supply() == z_supply
      self.assert_stats(token, z_supply)
      self.assert_unstake_info(pool_id, token.to_asset(z_amount))


  def assert_stats(self, token: Token, expected_supply: Asset):
      stats = token.z_stats()
      if expected_supply.amount == 0:
          assert stats is None, "stats is not None"
      else:    
        assert stats["supply"] == str(expected_supply), f"supply does not match {stats['supply']} != {expected_supply}"
        assert stats["max_supply"] == str(token.to_asset(4611686018427387903)), f"max_supply does not match {stats['max_supply']} != {token.to_asset(4611686018427387903)}"
        assert stats["issuer"] == self.bbf.bridge_z_account, f"issuer does not match {stats['issuer']} != {self.bbf.bridge_z_account}"


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
      staking_period_hrs: int
  ):
      actual = self.bbf.mock_yield_source_adaptor.functions.lastStakeInfo().call()
      self.cleos.logger.info(f'In assert_stake_info, results: {json.dumps(actual, indent=4)}')
      assert actual[0] == pool_id
      assert actual[1] == yield_source
      assert actual[2] == token.contract.address
      assert actual[3] == amount
      assert actual[4] == staking_period_hrs

  def assert_unstake_info(
      self,
      pool_id: int,
      amount: Asset
  ):
      results = self.cleos.get_table(
          self.bbf.stake_local_account, self.bbf.stake_local_account, "unstakeinfo"
      )
      self.cleos.logger.info(f'In assert_unstake_info, results: {json.dumps(results, indent=4)}')
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
      refund_delay_period_mins: int,
      batch_size: int,
      version: str,
      admin: str,
      active: bool
  ):
      actual = self.bbf.zero_bridge.get_config()
      self.cleos.logger.info(f'In zero bridge config: {json.dumps(actual, indent=4)}')
      self.cleos.logger.info(f'bridge_e_address: {bridge_e_address}, token_registry_address: {token_registry_address}, stake_local_account: {stake_local_account}, version: {version}, admin: {admin}')
      assert actual is not None
      assert actual["evm_bridge_address"] == bridge_e_address[2:].lower()
      assert actual["evm_token_registry_address"] == token_registry_address[2:].lower()
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
    assert (datetime.now() - timestamp).total_seconds() < 10, f"timestamp is older than 10 seconds {timestamp} != {datetime.now().isoformat()}"