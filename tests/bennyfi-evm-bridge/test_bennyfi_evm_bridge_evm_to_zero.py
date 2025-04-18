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
    test_util.assert_remove_processed_bridge_evm_to_zero_reqs(requests, check_notified=True)
    
    test_util.assert_notify_processed_bridge_evm_to_zero_reqs(requests)

    tevmc.cleos.logger.info(
        "Calling notify processed requests when they have already been notified should be a no-op"
    )
    test_util.assert_notify_processed_bridge_evm_to_zero_reqs(requests, check_notified=True)
    test_util.assert_remove_processed_bridge_evm_to_zero_reqs(requests)

    requests = []
    tevmc.cleos.logger.info(
        "TEST BATCH SIZE IS RESPECTED"
    )

    tevmc.cleos.logger.info(
        "Creating 5 requests"
    )

    for i in range(5):
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

    bbf.zero_bridge.update_config(batch_size=1)

    tevmc.cleos.logger.info(
        "Calling process requests with a batch size of 1 should process 1 request at a time"
    )

    test_util.assert_process_bridge_evm_to_zero_reqs(requests[:1])

    assert bbf.zero_bridge.get_processed_bridge_e_to_z_request_count() == 1, f"Expected 1 processed request, got {bbf.zero_bridge.get_processed_bridge_e_to_z_request_count()}"

    tevmc.cleos.logger.info(
        "Calling process requests again with the same batch size should be a no-op"
    )

    test_util.assert_process_bridge_evm_to_zero_reqs(requests[:1], check_already_processed=True)

    assert bbf.zero_bridge.get_processed_bridge_e_to_z_request_count() == 1, f"Expected 1 processed request, got {bbf.zero_bridge.get_processed_bridge_e_to_z_request_count()}"

    bbf.zero_bridge.update_config(batch_size=2)

    tevmc.cleos.logger.info(
        "Calling process requests with a batch size of 2 should process one more request"
    )

    test_util.assert_process_bridge_evm_to_zero_reqs(requests[:2], check_already_processed=True)

    assert bbf.zero_bridge.get_processed_bridge_e_to_z_request_count() == 2, f"Expected 2 processed request, got {bbf.zero_bridge.get_processed_bridge_e_to_z_request_count()}"

    # setting version to avoid duplicate transaction error
    bbf.zero_bridge.update_config(batch_size=1, version="v2") 

    tevmc.cleos.logger.info(
        "Calling notify processed requests with a batch size of 1 should notify 1 request at a time"
    )

    test_util.assert_notify_processed_bridge_evm_to_zero_reqs(requests[:1])

    test_util.assert_bridge_e_to_zero_req_exists(requests[0]["request"]["id"], exists=False)
    test_util.assert_bridge_e_to_zero_req_exists(requests[1]["request"]["id"], exists=True)

    tevmc.cleos.logger.info(
        "Calling notify processed requests again with a batch size of 1 should be a no-op"
    )

    test_util.assert_notify_processed_bridge_evm_to_zero_reqs(requests[:1], check_notified=True)

    test_util.assert_bridge_e_to_zero_req_exists(requests[1]["request"]["id"], exists=True)

    bbf.zero_bridge.update_config(batch_size=10)

    tevmc.cleos.logger.info(
        "Calling remove processed requests should only remove one request, as only one has been notified, batch size should not matter"
    ) 

    test_util.assert_remove_processed_bridge_evm_to_zero_reqs(requests[:1])

    assert bbf.zero_bridge.get_processed_bridge_e_to_z_request_count() == 1, f"Expected 1 processed request, got {bbf.zero_bridge.get_processed_bridge_e_to_z_request_count()}"

    bbf.zero_bridge.update_config(batch_size=3, version="v3")

    tevmc.cleos.logger.info(
        "Calling process requests with a batch size of 3 should process 2 more requests"
    )

    # Remove first request as it has already been processed and removed
    requests = requests[1:]
    test_util.assert_process_bridge_evm_to_zero_reqs(requests[:3], check_already_processed=True)

    assert bbf.zero_bridge.get_processed_bridge_e_to_z_request_count() == 3, f"Expected 3 processed requests, got {bbf.zero_bridge.get_processed_bridge_e_to_z_request_count()}"

    bbf.zero_bridge.update_config(batch_size=4)

    tevmc.cleos.logger.info(
        "Calling process requests with a batch size of 4 should process 1 more requests"
    )

    test_util.assert_process_bridge_evm_to_zero_reqs(requests, check_already_processed=True)

    assert bbf.zero_bridge.get_processed_bridge_e_to_z_request_count() == 4, f"Expected 4 processed requests, got {bbf.zero_bridge.get_processed_bridge_e_to_z_request_count()}"
    
    bbf.zero_bridge.update_config(batch_size=3, version="v4")
    
    tevmc.cleos.logger.info(
        "Calling notify processed requests with a batch size of 3 should notify 2 more requests"
    )

    test_util.assert_notify_processed_bridge_evm_to_zero_reqs(requests[:3], check_notified=True)

    test_util.assert_bridge_e_to_zero_req_exists(requests[1]["request"]["id"], exists=False)
    test_util.assert_bridge_e_to_zero_req_exists(requests[2]["request"]["id"], exists=False)
    test_util.assert_bridge_e_to_zero_req_exists(requests[3]["request"]["id"], exists=True)

    bbf.zero_bridge.update_config(batch_size=4, version="v5")

    tevmc.cleos.logger.info(
        "Calling notify processed requests with a batch size of 4 should notify 1 more requests"
    )

    test_util.assert_notify_processed_bridge_evm_to_zero_reqs(requests, check_notified=True)
    test_util.assert_bridge_e_to_zero_req_exists(requests[3]["request"]["id"], exists=False)

    bbf.zero_bridge.update_config(batch_size=1, version="v7")

    tevmc.cleos.logger.info(
        "Calling remove processed requests with a batch size of 1 should remove 1 request"
    )

    test_util.assert_remove_processed_bridge_evm_to_zero_reqs(requests[:1], check_notified=True)
    assert bbf.zero_bridge.get_processed_bridge_e_to_z_request_count() == 3, f"Expected 3 processed requests, got {bbf.zero_bridge.get_processed_bridge_e_to_z_request_count()}"

    requests = requests[1:]
    bbf.zero_bridge.update_config(batch_size=2, version="v7")

    tevmc.cleos.logger.info(
        "Calling remove processed requests with a batch size of 2 should remove 2 request"
    )

    test_util.assert_remove_processed_bridge_evm_to_zero_reqs(requests[:2], check_notified=True)
    assert bbf.zero_bridge.get_processed_bridge_e_to_z_request_count() == 1, f"Expected 1 processed requests, got {bbf.zero_bridge.get_processed_bridge_e_to_z_request_count()}"

    requests = requests[2:]
    tevmc.cleos.logger.info(
        "Calling remove processed requests again should delete all remaining requests"
    )

    test_util.assert_remove_processed_bridge_evm_to_zero_reqs(requests, check_notified=True)
    assert bbf.zero_bridge.get_processed_bridge_e_to_z_request_count() == 0, f"Expected 0 processed requests, got {bbf.zero_bridge.get_processed_bridge_e_to_z_request_count()}"



