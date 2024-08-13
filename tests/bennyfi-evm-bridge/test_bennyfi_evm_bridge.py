#!/usr/bin/env python3

import json
import logging
import pytest
from eth_account import Account

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

DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 991000


def test_all(benybridge):
    bbf = benybridge
    tevmc = bbf.tevmc
    tevmc.logger.setLevel(logging.DEBUG)
    local_w3 = bbf.local_w3
    
    # tevmc.cleos.logger.info('Getting config table...')
    # rows = tevmc.cleos.get_table(bbf.bridge_z_account, bbf.bridge_z_account, 'bridgeconfig')
    # tevmc.cleos.logger.info(json.dumps(rows, indent=4))
    # assert rows[0]['version'] == 'v1.0'

    tevmc.cleos.logger.info("Set allowance to bridge e...")
    tx = bbf.mock_token_contract.functions.approve(bbf.bridge_e_contract.address, 1000).build_transaction(
        {
            "from": bbf.e_accounts[0].address,
            "gas": DEFAULT_GAS,
            "gasPrice": DEFAULT_GAS_PRICE,
            "nonce": local_w3.eth.get_transaction_count(
                bbf.e_accounts[0].address
            ),
        }
    )
    signed_tx = bbf.e_accounts[0].sign_transaction(tx)
    tx_hash = local_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    assert bbf.mock_token_contract.functions.allowance(bbf.e_accounts[0].address, bbf.bridge_e_contract.address).call() == 1000
    receipt = local_w3.eth.wait_for_transaction_receipt(tx_hash)
    assert receipt

    tevmc.cleos.logger.info("Bridge evm to zero...")
    tx = bbf.bridge_e_contract.functions.bridgeEVMToZero(bbf.z_accounts[0], bbf.mock_token_contract.address, 1000).build_transaction(
        {
            "from": bbf.e_accounts[0].address,
            "gas": DEFAULT_GAS,
            "gasPrice": DEFAULT_GAS_PRICE,
            "nonce": local_w3.eth.get_transaction_count(
                bbf.e_accounts[0].address
            ),
        }
    )
    signed_tx = bbf.e_accounts[0].sign_transaction(tx)
    tx_hash = local_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    assert bbf.bridge_e_contract.functions.tokenBalances(bbf.mock_token_contract.address).call() == 1000
    receipt = local_w3.eth.wait_for_transaction_receipt(tx_hash)
    assert receipt

    # try:
    #     tevmc.cleos.logger.info("Bridge evm to zero...")
    #     user1_z = "user1"
    #     tevmc.cleos.create_account_staked("eosio", user1_z)
    #     tx = bridge_e_contract.functions.bridgeEVMToZero(user1_z, mock_token_contract.address, 1000).build_transaction(
    #         {
    #             "from": user1_e.address,
    #             "gas": DEFAULT_GAS,
    #             "gasPrice": DEFAULT_GAS_PRICE,
    #             "nonce": local_w3.eth.get_transaction_count(
    #                 user1_e.address
    #             ),
    #         }
    #     )
    #     signed_tx = user1_e.sign_transaction(tx)
    #     tx_hash = local_w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    # except Exception as e:
    #     tevmc.cleos.logger.info(e)
    # assert bridge_e_contract.functions.tokenBalances(mock_token_contract.address).call() == 0
    # assert mock_token_contract.functions.balanceOf(user1_e.address).call() == 100000000000
    assert bbf.mock_token_contract.functions.balanceOf(bbf.e_accounts[0].address).call() == 99999999000
    tevmc.cleos.logger.info('Getting stats table...')
    rows = tevmc.cleos.get_table(bbf.bridge_z_account, 'MTK', 'stat')
    tevmc.cleos.logger.info(json.dumps(rows, indent=4))

    tevmc.cleos.logger.info('Getting accounts table...')
    rows = tevmc.cleos.get_table(bbf.bridge_z_account, bbf.z_accounts[0], 'accounts')
    tevmc.cleos.logger.info(json.dumps(rows, indent=4))

    tevmc.cleos.logger.info("Bridge z to evm...")
    result = tevmc.cleos.push_action(
        bbf.bridge_z_account,
        "bridgeztoevm",
        [
            bbf.z_accounts[0],
            "0.000009 MTK",
            bbf.e_accounts[0].address[2:],
        ],
        bbf.z_accounts[0],
        tevmc.cleos.private_keys[bbf.z_accounts[0]],
    )
    tevmc.cleos.logger.info(json.dumps(result, indent=4))

    tevmc.cleos.logger.info('Getting stats table...')
    rows = tevmc.cleos.get_table(bbf.bridge_z_account, 'MTK', 'stat')
    tevmc.cleos.logger.info(json.dumps(rows, indent=4))

    tevmc.cleos.logger.info('Getting accounts table...')
    rows = tevmc.cleos.get_table(bbf.bridge_z_account, bbf.z_accounts[0], 'accounts')
    tevmc.cleos.logger.info(json.dumps(rows, indent=4))

    tevmc.cleos.logger.info('Getting bridge requests table...')
    rows = tevmc.cleos.get_table(bbf.bridge_z_account, bbf.bridge_z_account, 'bridgereqs')
    tevmc.cleos.logger.info(json.dumps(rows, indent=4))
    
    assert bbf.mock_token_contract.functions.balanceOf(bbf.e_accounts[0].address).call() == 99999999900
