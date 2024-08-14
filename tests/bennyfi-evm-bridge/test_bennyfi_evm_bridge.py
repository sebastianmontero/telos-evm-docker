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
    local_w3 = bbf.local_w3
    evm_transaction_signer = bbf.evm_transaction_signer

    # tevmc.cleos.logger.info('Getting config table...')
    # rows = tevmc.cleos.get_table(bbf.bridge_z_account, bbf.bridge_z_account, 'bridgeconfig')
    # tevmc.cleos.logger.info(json.dumps(rows, indent=4))
    # assert rows[0]['version'] == 'v1.0'
    tevmc.cleos.logger.info("TEST BRIDGE FROM EVM TO ZERO TOKEN WITH SAME NAME DIFFERENT PRECISION")
    assert_bridge_evm_to_zero(bbf, bbf.e_accounts[0], bbf.z_accounts[0], bbf.tokens[0], 847348)
    # token = bbf.tokens[0]
    # e_user = bbf.e_accounts[0]
    # z_user = bbf.z_accounts[0]
    # e_user_balance = token.e_balance(e_user.address)
    # z_user_balance = token.z_balance(z_user)
    # e_bridge_balance = bbf.bridge_e_contract.functions.tokenBalances(token.contract.address).call()
    # z_supply = token.z_supply()
    # z_amount = 847348
    # e_amount = token.z_to_e_amount(z_amount)
    # tevmc.cleos.logger.info(f"z user balance: {z_user_balance} z user balance type: {type(z_user_balance)} e user balance: {e_user_balance} bridge balance: {e_bridge_balance} z supply: {z_supply} z supply type: {type(z_supply)} z amount: {z_amount} e amount: {e_amount}")
    # tevmc.cleos.logger.info("Set allowance to bridge e...")
    # receipt = evm_transaction_signer.transact(
    #     token.contract,
    #     'approve',
    #     e_user.address,
    #     bbf.bridge_e_contract.address,
    #     e_amount
    # )
    # assert receipt

    # tevmc.cleos.logger.info("Bridge evm to zero...")
    # receipt = evm_transaction_signer.transact(
    #     bbf.bridge_e_contract,
    #     'bridgeEVMToZero',
    #     e_user.address,
    #     bbf.z_accounts[0],
    #     token.contract.address,
    #     e_amount
    # )
    # assert receipt

    # e_user_balance -= e_amount
    # e_bridge_balance += e_amount
    # z_user_balance.amount += z_amount
    # z_supply.amount += z_amount
    # assert token.e_balance(e_user.address) == e_user_balance
    # assert token.e_balance(bbf.bridge_e_contract.address) == e_bridge_balance
    # assert bbf.bridge_e_contract.functions.tokenBalances(token.contract.address).call() == e_bridge_balance
    # assert token.z_balance(z_user) == z_user_balance
    # assert token.z_supply() == z_supply
    # tevmc.cleos.logger.info('Getting stats table...')
    # rows = tevmc.cleos.get_table(bbf.bridge_z_account, 'MTK', 'stat')
    # tevmc.cleos.logger.info(json.dumps(rows, indent=4))

    # tevmc.cleos.logger.info('Getting accounts table...')
    # rows = tevmc.cleos.get_table(bbf.bridge_z_account, bbf.z_accounts[0], 'accounts')
    # tevmc.cleos.logger.info(json.dumps(rows, indent=4))

    # tevmc.cleos.logger.info("Bridge z to evm...")
    # result = tevmc.cleos.push_action(
    #     bbf.bridge_z_account,
    #     "bridgeztoevm",
    #     [
    #         bbf.z_accounts[0],
    #         "0.000090 MTA",
    #         bbf.e_accounts[0].address[2:],
    #     ],
    #     bbf.z_accounts[0],
    #     tevmc.cleos.private_keys[bbf.z_accounts[0]],
    # )
    # tevmc.cleos.logger.info(json.dumps(result, indent=4))

    # tevmc.cleos.logger.info('Getting stats table...')
    # rows = tevmc.cleos.get_table(bbf.bridge_z_account, 'MTK', 'stat')
    # tevmc.cleos.logger.info(json.dumps(rows, indent=4))

    # tevmc.cleos.logger.info('Getting accounts table...')
    # rows = tevmc.cleos.get_table(bbf.bridge_z_account, bbf.z_accounts[0], 'accounts')
    # tevmc.cleos.logger.info(json.dumps(rows, indent=4))

    # tevmc.cleos.logger.info('Getting bridge requests table...')
    # rows = tevmc.cleos.get_table(bbf.bridge_z_account, bbf.bridge_z_account, 'bridgereqs')
    # tevmc.cleos.logger.info(json.dumps(rows, indent=4))
    
    # assert token.contract.functions.balanceOf(bbf.e_accounts[0].address).call() == 9999999000


def assert_bridge_evm_to_zero(bbf: BenyBridgeFixture, e_user: LocalAccount, z_user: str, token: Token, z_amount: int):
    tevmc = bbf.tevmc
    evm_transaction_signer = bbf.evm_transaction_signer

    e_user_balance = token.e_balance(e_user.address)
    z_user_balance = token.z_balance(z_user)
    e_bridge_balance = bbf.bridge_e_contract.functions.tokenBalances(token.contract.address).call()
    z_supply = token.z_supply()
    e_amount = token.z_to_e_amount(z_amount)
    tevmc.cleos.logger.info(f"z user balance: {z_user_balance} z user balance type: {type(z_user_balance)} e user balance: {e_user_balance} bridge balance: {e_bridge_balance} z supply: {z_supply} z supply type: {type(z_supply)} z amount: {z_amount} e amount: {e_amount}")
    tevmc.cleos.logger.info("Set allowance to bridge e...")
    receipt = evm_transaction_signer.transact(
        token.contract,
        'approve',
        e_user.address,
        bbf.bridge_e_contract.address,
        e_amount
    )
    assert receipt

    tevmc.cleos.logger.info("Bridge evm to zero...")
    receipt = evm_transaction_signer.transact(
        bbf.bridge_e_contract,
        'bridgeEVMToZero',
        e_user.address,
        bbf.z_accounts[0],
        token.contract.address,
        e_amount
    )
    assert receipt

    e_user_balance -= e_amount
    e_bridge_balance += e_amount
    z_user_balance.amount += z_amount
    z_supply.amount += z_amount
    assert token.e_balance(e_user.address) == e_user_balance
    assert token.e_balance(bbf.bridge_e_contract.address) == e_bridge_balance
    assert bbf.bridge_e_contract.functions.tokenBalances(token.contract.address).call() == e_bridge_balance
    assert token.z_balance(z_user) == z_user_balance
    assert token.z_supply() == z_supply
    assert_stats(
        bbf,
        token, 
        z_supply
    )


def assert_stats(bbf: BenyBridgeFixture, token: Token, expected_supply: Asset):
    stats = token.z_stats()
    assert stats['supply'] == str(expected_supply)
    assert stats['max_supply'] == token.to_asset(4611686018427390000).to_string()
    assert stats['issuer'] == bbf.bridge_z_account