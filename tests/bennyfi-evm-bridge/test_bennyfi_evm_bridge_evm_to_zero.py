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
from util.bridge_test_util import BridgeTestUtil, BridgeEVMToZeroStage
from conftest import BenyBridgeFixture

DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 991000


def test_all(benybridge):
    bbf = benybridge
    tevmc = bbf.tevmc
    tevmc.logger.setLevel(logging.DEBUG)
    test_util = BridgeTestUtil(bbf)
    bbf.configure_zero_contract()
    tevmc.cleos.logger.info(
        "TEST PROCESS BRIDGE EVM TO ZERO REQUESTS"
    )

    tevmc.cleos.logger.info(
        "Should fail for no requests"
    )

    with pytest.raises(Exception) as e:
        bbf.zero_bridge.process_e_to_z_reqs()
    assert "No requests found" in repr(e.value)

    requests = []
    
    tevmc.cleos.logger.info(
        "Create requests to test process bridge evm to zero requests when all tokens have been unregistered"
    )

    req = test_util.assert_bridge_evm_to_zero(
        bbf.e_accounts[0],
        bbf.z_accounts[0],
        bbf.tokens[0],
        847348, 
        BridgeEVMToZeroStage.REQUEST_CREATED
    )

    requests.append({
        "request": req,
        "refund_reason": "Token not registered"
    })
    
    req = test_util.assert_bridge_evm_to_zero(
        bbf.e_accounts[1],
        bbf.z_accounts[1],
        bbf.tokens[1],
        437348, 
        BridgeEVMToZeroStage.REQUEST_CREATED
    )

    requests.append({
        "request": req,
        "refund_reason": "Token not registered"
    })

    bbf.token_registry.unregister_tokens(bbf.tokens)

    tevmc.cleos.logger.info(
        "Processing requests should fail for tokens not registered as all tokens have been unregistered"
    )

    test_util.assert_process_bridge_evm_to_zero_reqs(requests)
    test_util.assert_notify_processed_bridge_evm_to_zero_reqs(requests)
    test_util.assert_remove_processed_bridge_evm_to_zero_reqs(requests)

    bbf.token_registry.register_tokens(bbf.tokens)

    requests = []
    tevmc.cleos.logger.info(
        "Create request with non existent to account"
    )

    request = test_util.assert_bridge_evm_to_zero(
        bbf.e_accounts[0],
        "nonexistent",
        bbf.tokens[0],
        847348,
        BridgeEVMToZeroStage.REQUEST_CREATED
    )
    requests.append({
        "request": request,
        "refund_reason": "account does not exist"
    })

    tevmc.cleos.logger.info(
        "Create request with token that will be deactivated"
    )

    request = test_util.assert_bridge_evm_to_zero(
        bbf.e_accounts[0],
        bbf.z_accounts[1],
        bbf.tokens[1],
        147348,
        BridgeEVMToZeroStage.REQUEST_CREATED
    )
    requests.append({
        "request": request,
        "refund_reason": "Token is not active"
    })

    bbf.token_registry.set_active_status(bbf.tokens[1].contract.address, False)


    tevmc.cleos.logger.info(
        "Create request with token that will be unregistered"
    )

    request = test_util.assert_bridge_evm_to_zero(
        bbf.e_accounts[0],
        bbf.z_accounts[1],
        bbf.tokens[2],
        2473,
        BridgeEVMToZeroStage.REQUEST_CREATED
    )
    requests.append({
        "request": request,
        "refund_reason": "Token not registered"
    })

    bbf.token_registry.unregister_token(bbf.tokens[2].contract.address)

    tevmc.cleos.logger.info(
        "Create valid request"
    )

    request = test_util.assert_bridge_evm_to_zero(
        bbf.e_accounts[1],
        bbf.z_accounts[2],
        bbf.tokens[0],
        947348,
        BridgeEVMToZeroStage.REQUEST_CREATED
    )
    requests.append({
        "request": request,
        "refund_reason": ""
    })

    tevmc.cleos.logger.info(
        "Processing requests 1 should succeed and the others should fail for various reasons"
    )
    test_util.assert_process_bridge_evm_to_zero_reqs(requests)

    tevmc.cleos.logger.info(
        "Calling process requests when all requests have been processed, should be a no-op"
    )
    test_util.assert_process_bridge_evm_to_zero_reqs(requests, check_already_processed=True)

    tevmc.cleos.logger.info(
        "Creating a couple of valid requests, when there are already processed requests, should process the new ones only"
    )
    request = test_util.assert_bridge_evm_to_zero(
        bbf.e_accounts[2],
        bbf.z_accounts[1],
        bbf.tokens[0],
        517348,
        BridgeEVMToZeroStage.REQUEST_CREATED
    )
    requests.append({
        "request": request,
        "refund_reason": ""
    })

    request = test_util.assert_bridge_evm_to_zero(
        bbf.e_accounts[2],
        bbf.z_accounts[2],
        bbf.tokens[0],
        117348,
        BridgeEVMToZeroStage.REQUEST_CREATED
    )
    requests.append({
        "request": request,
        "refund_reason": ""
    })

    test_util.assert_process_bridge_evm_to_zero_reqs(requests, check_already_processed=True)

    tevmc.cleos.logger.info(
        "Calling remove processed requests when they haven't been notified should be a no-op"
    )
    test_util.assert_remove_processed_bridge_evm_to_zero_reqs(requests)
    
    test_util.assert_notify_processed_bridge_evm_to_zero_reqs(requests)

    tevmc.cleos.logger.info(
        "Calling notify processed requests when they have already been notified should be a no-op"
    )
    test_util.assert_notify_processed_bridge_evm_to_zero_reqs(requests)
    test_util.assert_remove_processed_bridge_evm_to_zero_reqs(requests)

