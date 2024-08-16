#!/usr/bin/env python3

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

from tevmc.utils import to_wei
from web3.middleware.signing import construct_sign_and_send_raw_middleware
import web3
from util.evm_transaction_signer import EVMTransactionSigner
from util.token import Token
from conftest import BenyBridgeFixture

DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 991000


def test_all(benybridge):
    bbf = benybridge
    tevmc = bbf.tevmc
    tevmc.logger.setLevel(logging.DEBUG)
    
    # token = bbf.tokens[0]
    # tevmc.cleos.logger.info(
    #     "TEST BRIDGE FROM EVM TO ZERO TOKEN WITH SAME NAME DIFFERENT PRECISION WITHOUT BRIDGE FEE"
    # )
    # assert_bridge_evm_to_zero(
    #     bbf, bbf.e_accounts[0], bbf.z_accounts[0], token, 847348
    # )

    # tevmc.cleos.logger.info(
    #     "TEST BRIDGE FROM ZERO TO EVM TOKEN WITH SAME NAME DIFFERENT PRECISION"
    # )
    # assert_bridge_zero_to_evm(
    #     bbf, bbf.z_accounts[0], bbf.e_accounts[0], token, 5173
    # )

    # set_fee(bbf, 1000)
    # tevmc.cleos.logger.info(
    #     "TEST BRIDGE MORE TOKENS FROM EVM TO ZERO TOKEN WITH SAME NAME DIFFERENT PRECISION WITH BRIDGE FEE"
    # )
    # token = bbf.tokens[0]
    # assert_bridge_evm_to_zero(
    #     bbf, bbf.e_accounts[0], bbf.z_accounts[0], token, 1349347
    # )

    # tevmc.cleos.logger.info(
    #     "BRDIGE TOKENS TO STAKE LOCAL ACCOUNT WITH SAME NAME DIFFERENT PRECISION"
    # )
    # assert_bridge_evm_to_zero(
    #     bbf, bbf.e_accounts[0], bbf.stake_local_account, token, 9847348
    # )
    # pool_id = 2
    # yield_source = token.yield_source_name()
    # tevmc.cleos.logger.info(
    #     "TEST STAKE TOKEN WITH SAME NAME DIFFERENT PRECISION"
    # )
    # assert_stake(bbf,pool_id, yield_source, token, 4847348, 24)

    # tevmc.cleos.logger.info(
    #     "TEST UNSTAKE TOKEN WITH SAME NAME DIFFERENT PRECISION"
    # )
    # assert_unstake(bbf,pool_id, yield_source, token, 3247348)

    # tevmc.cleos.logger.info(
    #     "TEST BRIDGE FROM EVM TO ZERO TOKEN WITH DIFFERENT NAME SAME PRECISION WITH FEE"
    # )
    # token = bbf.tokens[1]
    # assert_bridge_evm_to_zero(
    #     bbf, bbf.e_accounts[0], bbf.z_accounts[0], token, 142348
    # )

    token = bbf.tokens[1]
    tevmc.cleos.logger.info(
        "TEST BRIDGE FROM EVM TO ZERO TOKEN WITH DIFFERENT NAME SAME PRECISION WITH FEE TO DIFFERENT ACCOUNTS"
    )
    assert_bridge_evm_to_zero(
        bbf, bbf.e_accounts[1], bbf.z_accounts[2], token, 517342
    )

    tevmc.cleos.logger.info(
        "TEST BRIDGE FROM ZERO TO EVM TOKEN WITH DIFFERENT NAME SAME PRECISION"
    )
    assert_bridge_zero_to_evm(
        bbf, bbf.z_accounts[2], bbf.e_accounts[0], token, 21738
    )

    tevmc.cleos.logger.info(
        "BRDIGE TOKENS TO STAKE LOCAL ACCOUNT WITH DIFFERENT NAME SAME PRECISION"
    )
    assert_bridge_evm_to_zero(
        bbf, bbf.e_accounts[0], bbf.stake_local_account, token, 28453
    )

    pool_id = 5
    yield_source = token.yield_source_name()
    tevmc.cleos.logger.info(
        "TEST STAKE TOKEN WITH DIFFERENT NAME SAME PRECISION"
    )
    assert_stake(bbf,pool_id, yield_source, token, 28453, 24)

    tevmc.cleos.logger.info(
        "TEST UNSTAKE TOKEN WITH SAME NAME DIFFERENT PRECISION"
    )
    assert_unstake(bbf,pool_id, yield_source, token, 28453)


def assert_bridge_evm_to_zero(
    bbf: BenyBridgeFixture,
    e_user: LocalAccount,
    z_user: str,
    token: Token,
    z_amount: int,
):
    tevmc = bbf.tevmc
    local_w3 = bbf.local_w3
    evm_transaction_signer = bbf.evm_transaction_signer

    e_user_balance = token.e_balance(e_user.address)
    z_user_balance = token.z_balance(z_user)
    e_bridge_balance = bbf.bridge_e_contract.functions.tokenBalances(
        token.contract.address
    ).call()
    z_bridge_eth_balance = local_w3.eth.get_balance(bbf.bridge_z_eth_addr)
    z_supply = token.z_supply()
    e_amount = token.z_to_e_amount(z_amount)
    tevmc.cleos.logger.info(
        f"z user balance: {z_user_balance} z user balance type: {type(z_user_balance)} e user balance: {e_user_balance} bridge balance: {e_bridge_balance} z supply: {z_supply} z supply type: {type(z_supply)} z amount: {z_amount} e amount: {e_amount}"
    )
    tevmc.cleos.logger.info("Set allowance to bridge e...")
    receipt = evm_transaction_signer.transact(
        token.contract,
        "approve",
        e_user.address,
        bbf.bridge_e_contract.address,
        e_amount,
    )
    assert receipt
    fee = bbf.bridge_e_contract.functions.fee().call()
    tevmc.cleos.logger.info("Bridge evm to zero...")
    receipt = evm_transaction_signer.transact(
        bbf.bridge_e_contract,
        "bridgeEVMToZero",
        {
            "from": e_user.address,
            "value": fee,
        },
        z_user,
        token.contract.address,
        e_amount,
    )
    assert receipt

    e_user_balance -= e_amount
    e_bridge_balance += e_amount
    z_user_balance.amount += z_amount
    z_supply.amount += z_amount
    z_bridge_eth_balance += fee
    assert token.e_balance(e_user.address) == e_user_balance
    assert token.e_balance(bbf.bridge_e_contract.address) == e_bridge_balance
    assert (
        bbf.bridge_e_contract.functions.tokenBalances(token.contract.address).call()
        == e_bridge_balance
    )
    assert token.z_balance(z_user) == z_user_balance
    assert token.z_supply() == z_supply
    assert local_w3.eth.get_balance(bbf.bridge_z_eth_addr) == z_bridge_eth_balance
    assert_stats(bbf, token, z_supply)


def assert_bridge_zero_to_evm(
    bbf: BenyBridgeFixture,
    z_user: str,
    e_user: LocalAccount,
    token: Token,
    z_amount: int,
):
    tevmc = bbf.tevmc
    e_user_balance = token.e_balance(e_user.address)
    z_user_balance = token.z_balance(z_user)
    e_bridge_balance = bbf.bridge_e_contract.functions.tokenBalances(
        token.contract.address
    ).call()
    z_supply = token.z_supply()
    e_amount = token.z_to_e_amount(z_amount)
    asset_amount = token.to_asset(z_amount)
    tevmc.cleos.logger.info(
        f"z user balance: {z_user_balance} z user balance type: {type(z_user_balance)} e user balance: {e_user_balance} bridge balance: {e_bridge_balance} z supply: {z_supply} z supply type: {type(z_supply)} z amount: {z_amount} e amount: {e_amount}"
    )
    result = tevmc.cleos.push_action(
        bbf.bridge_z_account,
        "bridgeztoevm",
        [
            z_user,
            str(asset_amount),
            e_user.address[2:],
        ],
        z_user,
        tevmc.cleos.private_keys[z_user],
    )
    tevmc.cleos.logger.info(json.dumps(result, indent=4))

    e_user_balance += e_amount
    e_bridge_balance -= e_amount
    z_user_balance.amount -= z_amount
    z_supply.amount -= z_amount
    assert token.e_balance(e_user.address) == e_user_balance
    assert token.e_balance(bbf.bridge_e_contract.address) == e_bridge_balance
    assert (
        bbf.bridge_e_contract.functions.tokenBalances(token.contract.address).call()
        == e_bridge_balance
    )
    assert token.z_balance(z_user) == z_user_balance
    assert token.z_supply() == z_supply
    assert_stats(bbf, token, z_supply)
    assert_bridge_request(bbf, z_user, e_user, str(asset_amount), "completed")

def assert_stake(
    bbf: BenyBridgeFixture,
    pool_id: int,
    yield_source: str,
    token: Token,
    z_amount: int,
    staking_period_hrs: int
):
    tevmc = bbf.tevmc
    mock_yield_source_adaptor_balance = token.e_balance(bbf.mock_yield_source_adaptor.address)
    stake_local_balance = token.z_balance(bbf.stake_local_account)
    e_bridge_balance = bbf.bridge_e_contract.functions.tokenBalances(
        token.contract.address
    ).call()
    z_supply = token.z_supply()
    e_amount = token.z_to_e_amount(z_amount)
    asset_amount = token.to_asset(z_amount)
    
    result = tevmc.cleos.push_action(
        bbf.bridge_z_account,
        "stake",
        [
            pool_id,
            yield_source,
            asset_amount,
            staking_period_hrs,
        ],
        bbf.stake_local_account,
        tevmc.cleos.private_keys[bbf.stake_local_account],
    )
    tevmc.cleos.logger.info(json.dumps(result, indent=4))

    mock_yield_source_adaptor_balance += e_amount
    e_bridge_balance -= e_amount
    stake_local_balance.amount -= z_amount
    z_supply.amount -= z_amount
    assert token.e_balance(bbf.mock_yield_source_adaptor.address) == mock_yield_source_adaptor_balance
    assert token.e_balance(bbf.bridge_e_contract.address) == e_bridge_balance
    assert (
        bbf.bridge_e_contract.functions.tokenBalances(token.contract.address).call()
        == e_bridge_balance
    )
    assert token.z_balance(bbf.stake_local_account) == stake_local_balance
    assert token.z_supply() == z_supply
    assert_stats(bbf, token, z_supply)
    assert_stake_request(bbf, pool_id, yield_source, str(asset_amount), staking_period_hrs, "completed")
    assert_stake_info(bbf, pool_id, yield_source, token, e_amount, staking_period_hrs)


def assert_unstake(
    bbf: BenyBridgeFixture,
    pool_id: int,
    yield_source: str,
    token: Token,
    z_amount: int,
):
    tevmc = bbf.tevmc
    evm_transaction_signer = bbf.evm_transaction_signer

    mock_yield_source_adaptor_balance = token.e_balance(bbf.mock_yield_source_adaptor.address)
    stake_local_balance = token.z_balance(bbf.stake_local_account)
    e_bridge_balance = bbf.bridge_e_contract.functions.tokenBalances(
        token.contract.address
    ).call()
    z_supply = token.z_supply()
    e_amount = token.z_to_e_amount(z_amount)
    # tevmc.cleos.logger.info("Set allowance to bridge e...")
    # receipt = evm_transaction_signer.transact(
    #     token.contract,
    #     "approve",
    #     bbf.mock_yield_source_adaptor.address,
    #     bbf.bridge_e_contract.address,
    #     e_amount,
    # )
    # assert receipt

    tevmc.cleos.logger.info("Trigger Unstake...")
    receipt = evm_transaction_signer.transact(
        bbf.mock_yield_source_adaptor,
        "triggerUnstake",
        bbf.e_accounts[0].address,
        yield_source,
        pool_id,
        token.contract.address,
        e_amount,
        bbf.bridge_e_contract.address,
    )
    assert receipt

    mock_yield_source_adaptor_balance -= e_amount
    e_bridge_balance += e_amount
    stake_local_balance.amount += z_amount
    z_supply.amount += z_amount
    assert token.e_balance(bbf.mock_yield_source_adaptor.address) == mock_yield_source_adaptor_balance
    assert token.e_balance(bbf.bridge_e_contract.address) == e_bridge_balance
    assert (
        bbf.bridge_e_contract.functions.tokenBalances(token.contract.address).call()
        == e_bridge_balance
    )
    assert token.z_balance(bbf.stake_local_account) == stake_local_balance
    assert token.z_supply() == z_supply
    assert_stats(bbf, token, z_supply)
    assert_unstake_info(bbf, pool_id, token.to_asset(z_amount))


def assert_stats(bbf: BenyBridgeFixture, token: Token, expected_supply: Asset):
    stats = token.z_stats()
    assert stats["supply"] == str(expected_supply)
    assert stats["max_supply"] == str(token.to_asset(4611686018427387903))
    assert stats["issuer"] == bbf.bridge_z_account


def assert_bridge_request(
    bbf: BenyBridgeFixture,
    fromAccount: str,
    to: LocalAccount,
    quantity: Asset,
    state: str,
):
    results = bbf.cleos.get_table(
        bbf.bridge_z_account, bbf.bridge_z_account, "bridgereqs", limit=1, reverse=True
    )
    assert len(results) == 1
    actual = results[0]
    assert actual["from"] == str(fromAccount)
    assert actual["to"] == to.address[2:].lower()
    assert actual["quantity"] == str(quantity)
    assert actual["state"] == state

def assert_stake_request(
    bbf: BenyBridgeFixture,
    pool_id: int,
    yield_source: str,
    quantity: Asset,
    staking_period_hrs: int,
    state: str,
):
    results = bbf.cleos.get_table(
        bbf.bridge_z_account, bbf.bridge_z_account, "stakereqs", limit=1, reverse=True
    )
    bbf.cleos.logger.info(f'In assert_stake_request, results: {json.dumps(results, indent=4)}')
    assert len(results) == 1
    actual = results[0]
    assert actual["pool_id"] == pool_id
    assert actual["yield_source"] == yield_source
    assert actual["quantity"] == str(quantity)
    assert actual["staking_period_hrs"] == staking_period_hrs
    assert actual["state"] == state


def assert_stake_info(
    bbf: BenyBridgeFixture,
    pool_id: int,
    yield_source: str,
    token: Token,
    amount: int,
    staking_period_hrs: int
):
    actual = bbf.mock_yield_source_adaptor.functions.lastStakeInfo().call()
    bbf.cleos.logger.info(f'In assert_stake_info, results: {json.dumps(actual, indent=4)}')
    assert actual[0] == pool_id
    assert actual[1] == yield_source
    assert actual[2] == token.contract.address
    assert actual[3] == amount
    assert actual[4] == staking_period_hrs

def assert_unstake_info(
    bbf: BenyBridgeFixture,
    pool_id: int,
    amount: Asset
):
    results = bbf.cleos.get_table(
        bbf.stake_local_account, bbf.stake_local_account, "unstakeinfo"
    )
    bbf.cleos.logger.info(f'In assert_unstake_info, results: {json.dumps(results, indent=4)}')
    assert len(results) == 1
    actual = results[0]
    assert actual["from"] == bbf.bridge_z_account
    assert actual["amount"] == str(amount)
    assert actual["memo"] == f"pool id: {pool_id}"    


def set_fee(bbf: BenyBridgeFixture, fee: int):
    receipt = bbf.evm_transaction_signer.transact(
            bbf.bridge_e_contract,
            "setFee",
            bbf.cleos.evm_default_account.address,
            fee
            )
    assert receipt