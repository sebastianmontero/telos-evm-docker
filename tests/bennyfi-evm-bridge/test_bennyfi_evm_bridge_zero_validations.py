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
from leap.errors import ChainAPIError

from tevmc.utils import to_wei
from web3.middleware.signing import construct_sign_and_send_raw_middleware
import web3
from util.evm_transaction_signer import EVMTransactionSigner
from util.token import Token
from util.bridge_test_util import BridgeTestUtil
from util.function_encoder import FunctionEncoder
from conftest import BenyBridgeFixture


DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 991000


def test_all(benybridge):
    bbf = benybridge
    local_w3 = bbf.local_w3
    tevmc = bbf.tevmc
    tevmc.logger.setLevel(logging.DEBUG)
    test_util = BridgeTestUtil(bbf)
    token = bbf.tokens[0]
    zero_bridge = bbf.zero_bridge

    z_user = bbf.z_accounts[0]
    e_user = bbf.e_accounts[0]
    pool_id = 3
    yield_source = token.yield_source_name()
    amount = 100
    asset_amount = "10.0000 MTA"
    staking_period_hrs = 400
    version = "v1.0"
    tevmc.cleos.logger.info(
        "CONTRACT NOT INITIALIZED VALIDATIONS"
    )
    tevmc.cleos.logger.info(
        "bridgeztoevm: Should fail for not initialized contract"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.bridge_z_to_e(z_user, e_user.address, asset_amount)
    assert "contract must be configured first" in repr(e.value)

    tevmc.cleos.logger.info(
        "stake: Should fail for not initialized contract"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.stake(pool_id, yield_source, asset_amount, staking_period_hrs)
    assert "contract must be configured first" in repr(e.value)

    tevmc.cleos.logger.info(
        "evmnotify: Should fail for not initialized contract"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(e_user.address, b'')
    assert "contract must be configured first" in repr(e.value)

    tevmc.cleos.logger.info(
        "SETCONFIG TESTS"
    )
    refund_delay_period_mins = 5
    batch_size = 40
    admin = bbf.bridge_z_admin
    tevmc.cleos.logger.info(
        "setconfig: Should fail for calling from non contract account"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.set_config(
            bbf.bridge_e_contract.address,
            bbf.token_registry_contract.address,
            bbf.stake_local_account,
            refund_delay_period_mins,
            batch_size,
            version,
            admin,
            True,
            z_user)
    assert "missing required authority of contract or admin" in repr(e.value)

    tevmc.cleos.logger.info(
        "setconfig: Should fail for non existant stake local account"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.set_config(
            bbf.bridge_e_contract.address,
            bbf.token_registry_contract.address,
            'nonexistant',
            refund_delay_period_mins,
            batch_size,
            version,
            admin)
    assert "stake local contract account doesn't exist" in repr(e.value)

    tevmc.cleos.logger.info(
        "setconfig: Should fail for non existent admin account"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.set_config(
            bbf.bridge_e_contract.address,
            bbf.token_registry_contract.address,
            bbf.stake_local_account,
            refund_delay_period_mins,
            batch_size,
            version,
            "nonexistent")
    assert "initial admin account doesn't exist" in repr(e.value)

    tevmc.cleos.logger.info(
        "setconfig: Should fail for refund delay period equal to 0"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.set_config(
            bbf.bridge_e_contract.address,
            bbf.token_registry_contract.address,
            bbf.stake_local_account,
            0,
            batch_size,
            version,
            admin)
    assert "refund delay period must be greater than 0" in repr(e.value)

    tevmc.cleos.logger.info(
        "setconfig: Should fail for batch size equal to 0"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.set_config(
            bbf.bridge_e_contract.address,
            bbf.token_registry_contract.address,
            bbf.stake_local_account,
            refund_delay_period_mins,
            0,
            version,
            admin)
    assert "batch size must be greater than 0" in repr(e.value)

    tevmc.cleos.logger.info(
        "setconfig: Should fail for non existent bridge account"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.set_config(
            "0x0000000000000000000000000000000000000000",
            bbf.token_registry_contract.address,
            bbf.stake_local_account,
            refund_delay_period_mins,
            batch_size,
            version,
            admin)
    assert "bridge account doesn't exist" in repr(e.value)

    tevmc.cleos.logger.info(
        "setconfig: Should fail for non existent token registry account"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.set_config(
            bbf.bridge_e_contract.address,
            "0x0000000000000000000000000000000000000000",
            bbf.stake_local_account,
            refund_delay_period_mins,
            batch_size,
            version,
            admin)
    assert "token registry account doesn't exist" in repr(e.value)

    tevmc.cleos.logger.info(
        "setconfig: Should work"
    )
    zero_bridge.set_config(
        bbf.bridge_e_contract.address,
        bbf.token_registry_contract.address,
        bbf.stake_local_account,
        refund_delay_period_mins,
        batch_size,
        version,
        admin)
    
    test_util.assert_zero_bridge_config(
        bbf.bridge_e_contract.address,
        bbf.token_registry_contract.address,
        bbf.stake_local_account,
        refund_delay_period_mins,
        batch_size,
        version,
        admin,
        True
    )
    
    tevmc.cleos.logger.info(
        "setconfig: Should fail for calling from non contract or admin account"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.set_config(
            bbf.bridge_e_contract.address,
            bbf.token_registry_contract.address,
            bbf.stake_local_account,
            refund_delay_period_mins,
            batch_size,
            version,
            admin,
            True,
            z_user)
    assert "missing required authority of contract or admin" in repr(e.value)

    tevmc.cleos.logger.info(
        "setconfig: Should work when calling from admin account"
    )
    zero_bridge.set_config(
        bbf.bridge_e_contract.address,
        bbf.token_registry_contract.address,
        bbf.z_accounts[2],
        2,
        20,
        "v2.0",
        z_user,
        True,
        admin)
    
    test_util.assert_zero_bridge_config(
        bbf.bridge_e_contract.address,
        bbf.token_registry_contract.address,
        bbf.z_accounts[2],
        2,
        20,
        "v2.0",
        z_user,
        True
    )

    tevmc.cleos.logger.info(
        "setconfig: Should work when calling from contract account"
    )
    zero_bridge.set_config(
        bbf.bridge_e_contract.address,
        bbf.token_registry_contract.address,
        bbf.stake_local_account,
        refund_delay_period_mins,
        batch_size,
        version,
        admin,
        False)
    
    test_util.assert_zero_bridge_config(
        bbf.bridge_e_contract.address,
        bbf.token_registry_contract.address,
        bbf.stake_local_account,
        refund_delay_period_mins,
        batch_size,
        version,
        admin,
        False
    )

    tevmc.cleos.logger.info(
        "CONTRACT NOT ACTIVE VALIDATIONS"
    )
    tevmc.cleos.logger.info(
        "bridgeztoevm: Should fail for not active contract"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.bridge_z_to_e(z_user, e_user.address, asset_amount)
    assert "contract has been paused" in repr(e.value)

    tevmc.cleos.logger.info(
        "stake: Should fail for not active contract"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.stake(pool_id, yield_source, asset_amount, staking_period_hrs)
    assert "contract has been paused" in repr(e.value)

    tevmc.cleos.logger.info(
        "evmnotify: Should fail for not active contract"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(e_user.address, b'')
    assert "contract has been paused" in repr(e.value)


    tevmc.cleos.logger.info(
        "Activate contract"
    )
    zero_bridge.set_config(
        bbf.bridge_e_contract.address,
        bbf.token_registry_contract.address,
        bbf.stake_local_account,
        refund_delay_period_mins,
        batch_size,
        "v1.1", # avoid duplicate transaction
        admin,
        True)
    
    tevmc.cleos.logger.info(
        "BRIDGEZTOEVM TESTS"
    )
    
    tevmc.cleos.logger.info(
        "bridgeztoevm: Should fail for non authorized "
    )
    with pytest.raises(Exception) as e:
        zero_bridge.bridge_z_to_e(z_user, e_user.address, asset_amount, bbf.z_accounts[1])
    assert "missing authority of" in repr(e.value)

    tevmc.cleos.logger.info(
        "bridgeztoevm: Should fail for non registered token"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.bridge_z_to_e(z_user, e_user.address, "10.00 NE")
    assert "Token not registered" in repr(e.value)

    tevmc.cleos.logger.info(
        "bridgeztoevm: Should fail for non active token"
    )
    
    bbf.evm_transaction_signer.transact(
           bbf.token_registry_contract,
           "setTokenActiveStatus",
           bbf.cleos.evm_default_account.address,
           bbf.tokens[2].contract.address,
           False 
        )
    with pytest.raises(Exception) as e:
        zero_bridge.bridge_z_to_e(z_user, e_user.address, bbf.tokens[2].to_asset(10))
    assert "Token is not active" in repr(e.value)

    tevmc.cleos.logger.info(
        "bridgeztoevm: Should fail for invalid token precision"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.bridge_z_to_e(z_user, e_user.address, "10.00 MTA")
    assert "Symbol precision does not match registered decimals" in repr(e.value)

    tevmc.cleos.logger.info(
        "bridgeztoevm: Should fail for amount must be > 0"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.bridge_z_to_e(z_user, e_user.address, token.to_asset(0))
    assert "amount must be positive" in repr(e.value)

    tevmc.cleos.logger.info(
        "bridgeztoevm: Should fail for amount must be > min amount"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.bridge_z_to_e(z_user, e_user.address, token.to_asset(49))
    assert "amount must be greater or equal to min_amount" in repr(e.value)

    tevmc.cleos.logger.info(
        "bridgeztoevm: Should fail for non created token"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.bridge_z_to_e(z_user, e_user.address, token.to_asset(50))
    assert "token does not exist" in repr(e.value)

    z_user_balance = 1000000
    test_util.assert_bridge_evm_to_zero(
        e_user, z_user, token, z_user_balance
    )
    tevmc.cleos.logger.info(
        "bridgeztoevm: Should fail for no balance"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.bridge_z_to_e(bbf.z_accounts[1], e_user.address, token.to_asset(50))
    assert "no balance object found" in repr(e.value)

    tevmc.cleos.logger.info(
        "bridgeztoevm: Should fail for overdrawn balance"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.bridge_z_to_e(z_user, e_user.address, token.to_asset(z_user_balance + 1))
    assert "overdrawn balance" in repr(e.value)

    tevmc.cleos.logger.info(
        "STAKE TESTS"
    )

    tevmc.cleos.logger.info(
        "stake: Should fail for called from non stake local account"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.stake(pool_id, yield_source, asset_amount, staking_period_hrs, z_user)
    assert "missing authority of" in repr(e.value)

    tevmc.cleos.logger.info(
        "stake: Should fail for non registered token"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.stake(pool_id, yield_source, "10.00 NE", staking_period_hrs)
    assert "Token not registered" in repr(e.value)

    tevmc.cleos.logger.info(
        "stake: Should fail for non active token"
    )
    
    with pytest.raises(Exception) as e:
        zero_bridge.stake(pool_id, yield_source, bbf.tokens[2].to_asset(10), staking_period_hrs)
    assert "Token is not active" in repr(e.value)

    tevmc.cleos.logger.info(
        "stake: Should fail for invalid token precision"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.stake(pool_id, yield_source, "10.00 MTA", staking_period_hrs)
    assert "Symbol precision does not match registered decimals" in repr(e.value)

    tevmc.cleos.logger.info(
        "stake: Should fail for amount must be > 0"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.stake(pool_id, yield_source, token.to_asset(0), staking_period_hrs)
    assert "amount must be positive" in repr(e.value)

    tevmc.cleos.logger.info(
        "stake: Should fail for amount must be > min amount"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.stake(pool_id, yield_source, token.to_asset(49), staking_period_hrs)
    assert "amount must be greater or equal to min_amount" in repr(e.value)

    tevmc.cleos.logger.info(
        "stake: Should fail for non created token"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.stake(pool_id, yield_source, bbf.tokens[1].to_asset(50), staking_period_hrs)
    assert "token does not exist" in repr(e.value)

    z_user_balance = 1000000
    test_util.assert_bridge_evm_to_zero(
        e_user, z_user, token, z_user_balance
    )
    tevmc.cleos.logger.info(
        "stake: Should fail for no balance"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.stake(pool_id, yield_source, token.to_asset(50), staking_period_hrs)
    assert "no balance object found" in repr(e.value)

    stake_local_account_balance = 1000000
    test_util.assert_bridge_evm_to_zero(
        e_user, bbf.stake_local_account, token, stake_local_account_balance
    )
    tevmc.cleos.logger.info(
        "stake: Should fail for overdrawn balance"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.stake(pool_id, yield_source, token.to_asset(stake_local_account_balance + 1), staking_period_hrs)
    assert "overdrawn balance" in repr(e.value)

    tevmc.cleos.logger.info(
        "EVMNOTIFY TESTS"
    )

    tevmc.cleos.logger.info(
        "evmnotify: Should fail for called from non message account"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(e_user.address, '', z_user)
    assert "missing authority of" in repr(e.value)

    tevmc.cleos.logger.info(
        "evmnotify: Should fail for sender not the evm bridge address"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(e_user.address, '')
    assert "Sender must be the evm bridge contract" in repr(e.value)

    tevmc.cleos.logger.info(
        "evmnotify: Should fail for msg without handler function signature"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, '123')
    assert "msg must have the handler function signature" in repr(e.value)

    tevmc.cleos.logger.info(
        "evmnotify: Should fail for unknown handler function signature"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, '1234')
    assert "unknown handler function signature" in repr(e.value)

    tevmc.cleos.logger.info(
        "BRIDGE_ZERO_TO_EVM_SUCCEEDED TESTS"
    )

    encoder = FunctionEncoder("bridgeZeroToEVMSucceeded", ["uint64"])
    tevmc.cleos.logger.info(
        "bridge_zero_to_evm_succeeded: Should fail for invalid message length for the expected number of parameters"
    )
    tevmc.cleos.logger.info(
        f"function selector: {encoder.get_function_selector()}"
    )
    with pytest.raises(ChainAPIError) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.get_function_selector())
    assert  "data must be 32 bytes long to hold 1 params its size is 0" in repr(e.value)

    tevmc.cleos.logger.info(
        "bridge_zero_to_evm_succeeded: Should fail for bridge request not found"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(0))
    assert "bridge request not found" in repr(e.value)

    test_util.assert_bridge_zero_to_evm(
        z_user, e_user, token, 100
    )

    tevmc.cleos.logger.info(
        "bridge_zero_to_evm_succeeded: Should fail for bridge request not in pending state"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(0))
    assert "bridge request must be pending" in repr(e.value)

    tevmc.cleos.logger.info(
        "STAKE_SUCCEEDED TESTS"
    )

    encoder = FunctionEncoder("stakeSucceeded", ["uint64"])
    tevmc.cleos.logger.info(
        "stake_succeeded: Should fail for invalid message length for the expected number of parameters"
    )
    tevmc.cleos.logger.info(
        f"function selector: {encoder.get_function_selector()}"
    )
    with pytest.raises(ChainAPIError) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.get_function_selector())
    assert  "data must be 32 bytes long to hold 1 params its size is 0" in repr(e.value)

    tevmc.cleos.logger.info(
        "stake_succeeded: Should fail for stake request not found"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(0))
    assert "stake request not found" in repr(e.value)

    test_util.assert_stake(
        pool_id, yield_source, token, 100, 50
    )

    tevmc.cleos.logger.info(
        "stake_succeeded: Should fail for stake request not in pending state"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(0))
    assert "stake request must be pending" in repr(e.value)


    tevmc.cleos.logger.info(
        "BRIDGE_EVM_TO_ZERO TESTS"
    )

    encoder = FunctionEncoder("bridgeEVMToZero", ["bytes32", "bytes32", "uint64"])
    tevmc.cleos.logger.info(
        "bridge_evm_to_zero: Should fail for invalid message length for the expected number of parameters"
    )
    tevmc.cleos.logger.info(
        f"function selector: {encoder.get_function_selector()}"
    )
    with pytest.raises(ChainAPIError) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.get_function_selector())
    assert  "data must be 96 bytes long to hold 3 params its size is 0" in repr(e.value)

    symbol = "MTA"
    tevmc.cleos.logger.info(
        "bridge_evm_to_zero: Should fail for amount greater than max asset amount"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(z_user, symbol, 4611686018427387904))
    assert "input does not fit in asset amount" in repr(e.value)

    tevmc.cleos.logger.info(
        "bridge_evm_to_zero: Should fail for invalid symbol"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(z_user, "invalid", amount))
    assert "only uppercase letters allowed in symbol_code string" in repr(e.value)

    tevmc.cleos.logger.info(
        "bridge_evm_to_zero: Should fail for non existing account"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call("nonexistent", symbol, amount))
    assert "to account does not exist" in repr(e.value)


    tevmc.cleos.logger.info(
        "bridge_evm_to_zero: Should fail for non registered token"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(z_user, "NA", amount))
    assert "Token not registered" in repr(e.value)

    tevmc.cleos.logger.info(
        "bridge_evm_to_zero: Should fail for non active token"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(z_user, bbf.tokens[2].z_symbol, amount))
    assert "Token is not active" in repr(e.value)

    tevmc.cleos.logger.info(
        "bridge_evm_to_zero: Should fail for amount must be positive"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(z_user, symbol, 0))
    assert "amount must be positive" in repr(e.value)

    tevmc.cleos.logger.info(
        "bridge_evm_to_zero: Should fail for amount less than min amount"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(z_user, symbol, 49))
    assert "amount must be greater or equal to min_amount" in repr(e.value)


    tevmc.cleos.logger.info(
        "UNSTAKE TESTS"
    )

    encoder = FunctionEncoder("unstake", ["uint64", "bytes32", "bytes32", "uint64"])
    tevmc.cleos.logger.info(
        f"function selector: {encoder.get_function_selector()}"
    )
    tevmc.cleos.logger.info(
        "unstake: Should fail for invalid message length for the expected number of parameters"
    )
    with pytest.raises(ChainAPIError) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(pool_id, yield_source, symbol, amount)[:-1])
    assert  "data must be 128 bytes long to hold 4 params its size is 127" in repr(e.value)

    alt_encoder = FunctionEncoder("unstake", ["uint256", "bytes32", "bytes32", "uint64"])
    tevmc.cleos.logger.info(
        "unstake: Should fail for pool id that does not fit in uint64"
    )
    with pytest.raises(Exception) as e:
        fn_selector = encoder.get_function_selector()
        encoded_args = alt_encoder.encode_arguments(18446744073709551616, yield_source, symbol, amount)
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, (fn_selector + encoded_args))
    assert "input does not fit in uint64" in repr(e.value)

    tevmc.cleos.logger.info(
        "unstake: Should fail for invalid yield source name"
    )
    with pytest.raises(ChainAPIError) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(pool_id, "invalid8", symbol, amount))
    assert  "character is not in allowed character set for names" in repr(e.value)


    tevmc.cleos.logger.info(
        "unstake: Should fail for amount greater than max asset amount"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(pool_id, yield_source, symbol, 4611686018427387904))
    assert "input does not fit in asset amount" in repr(e.value)

    tevmc.cleos.logger.info(
        "unstake: Should fail for invalid symbol"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(pool_id, yield_source, "invalid", amount))
    assert "only uppercase letters allowed in symbol_code string" in repr(e.value)

    tevmc.cleos.logger.info(
        "unstake: Should fail for non registered token"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(pool_id, yield_source, "NA", amount))
    assert "Token not registered" in repr(e.value)

    tevmc.cleos.logger.info(
        "unstake: Should fail for non active token"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(pool_id, yield_source, bbf.tokens[2].z_symbol, amount))
    assert "Token is not active" in repr(e.value)

    tevmc.cleos.logger.info(
        "unstake: Should fail for amount must be positive"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(pool_id, yield_source, symbol, 0))
    assert "amount must be positive" in repr(e.value)

    tevmc.cleos.logger.info(
        "unstake: Should fail for amount less than min amount"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.evmnotify(bbf.bridge_e_contract.address, encoder.encode_function_call(pool_id, yield_source, symbol, 49))
    assert "amount must be greater or equal to min_amount" in repr(e.value)

    # tevmc.cleos.logger.info(
    #     "REFUND TESTS"
    # )

    # tevmc.cleos.logger.info(
    #     "refund: Should fail for non existent bridge request"
    # )
    # with pytest.raises(Exception) as e:
    #     zero_bridge.refund(50)
    # assert "bridge request not found" in repr(e.value)
    
    # tevmc.cleos.logger.info(
    #     "Getting last completed bridge request and lapsing it to verify that it is not refunded"
    # )
    # last_completed_bridge_request = zero_bridge.get_last_bridge_request()
    # assert last_completed_bridge_request['state'] == "completed"
    # zero_bridge.lapse_bridge_request(last_completed_bridge_request['bridge_request_id'])

    # tevmc.cleos.logger.info(
    #     "refund: Should fail for bridge request that has been completed"
    # )
    # with pytest.raises(Exception) as e:
    #     zero_bridge.refund(last_completed_bridge_request['bridge_request_id'])
    # assert "bridge request must be pending" in repr(e.value)
    
    # tevmc.cleos.logger.info(
    #     "Set an invalid evm bridge contract address in order to be able to create requests that require refunds"
    # )

    # zero_bridge.set_config(
    #     bbf.token_registry_contract.address,
    #     bbf.token_registry_contract.address,
    #     bbf.stake_local_account,
    #     refund_delay_period_mins,
    #     batch_size,
    #     version,
    #     admin)
    
    # tevmc.cleos.logger.info(
    #     "Create refund request"
    # )
    # result = bbf.zero_bridge.bridge_z_to_e(z_user, e_user.address, token.to_asset(50))
    # tevmc.cleos.logger.info(json.dumps(result, indent=4))

    # refund_bridge_request = zero_bridge.get_last_bridge_request()
    # assert refund_bridge_request['state'] == "completed"

    # tevmc.cleos.logger.info(
    #     "refund: Should fail for bridge request for which refund delay has not expired"
    # )
    # with pytest.raises(Exception) as e:
    #     zero_bridge.refund(refund_bridge_request['bridge_request_id'])
    # assert "refund delay period has not expired" in repr(e.value)

    # zero_bridge.lapse_bridge_request(refund_bridge_request['bridge_request_id'])

    # tevmc.cleos.logger.info(
    #     "refund: Should work for bridge request for which refund delay has expired and in pending state"
    # )
    # balance = token.z_balance(z_user)
    # zero_bridge.refund(refund_bridge_request['bridge_request_id'])
    # balance.amount += 50
    # assert token.z_balance(z_user) == balance

    
    # tevmc.cleos.logger.info(
    #     "RESET TESTS"
    # )
    # tevmc.cleos.logger.info(
    #     "Populate tables"
    # )

    # test_util.assert_bridge_zero_to_evm(
    #     z_user, e_user, token, 50
    # )
    # test_util.assert_bridge_zero_to_evm(
    #     z_user, e_user, token, 51
    # )
    # test_util.assert_bridge_zero_to_evm(
    #     z_user, e_user, token, 52
    # )

    # test_util.assert_stake(
    #     30, yield_source, token, 100, 50
    # )
    # test_util.assert_stake(
    #     31, yield_source, token, 100, 50
    # )

    # bridge_request_count = zero_bridge.get_bridge_request_count()
    # assert bridge_request_count  > 2
    # stake_request_count = zero_bridge.get_stake_request_count()
    # assert stake_request_count  > 2

    # tevmc.cleos.logger.info(
    #     "reset: Should fail when called from non contract account"
    # )
    # with pytest.raises(ChainAPIError) as e:
    #     zero_bridge.reset(10, ["bridgeconfig"], 1, bbf.bridge_z_admin)
    # assert  "missing authority of" in repr(e.value)

    # zero_bridge.reset(10, ["bridgeconfig"], 2)
    # assert zero_bridge.get_bridge_request_count() == bridge_request_count
    # assert zero_bridge.get_stake_request_count() == stake_request_count

    # zero_bridge.reset(1, ["bridgereqs"], 3)
    # assert zero_bridge.get_config() is None

    # bridge_request_count -= 1
    # assert zero_bridge.get_bridge_request_count() == bridge_request_count
    # assert zero_bridge.get_stake_request_count() == stake_request_count

    # zero_bridge.reset(1, ["stakereqs"], 4)
    # assert zero_bridge.get_config() is None

    # stake_request_count -= 1
    # assert zero_bridge.get_bridge_request_count() == bridge_request_count
    # assert zero_bridge.get_stake_request_count() == stake_request_count

    # request_count = bridge_request_count + stake_request_count
    # call_counter = 5
    # while request_count > 0:
    #     zero_bridge.reset(2, ["bridgereqs", "stakereqs"], call_counter)
    #     call_counter += 1
    #     request_count = max(0, request_count - 2)
    #     assert zero_bridge.get_bridge_request_count() + zero_bridge.get_stake_request_count() == request_count


def test_refund(benybridge):
    bbf = benybridge
    local_w3 = bbf.local_w3
    tevmc = bbf.tevmc
    tevmc.logger.setLevel(logging.DEBUG)
    test_util = BridgeTestUtil(bbf)
    token = bbf.tokens[0]
    zero_bridge = bbf.zero_bridge
    bbf.configure_zero_contract()

    z_user = bbf.z_accounts[0]
    e_user = bbf.e_accounts[0]

    test_util.assert_bridge_evm_to_zero(
        e_user, z_user, token, 1000000
    )

    test_util.assert_bridge_zero_to_evm(
        z_user, e_user, token, 100
    )

    tevmc.cleos.logger.info(
        "REFUND TESTS"
    )

    tevmc.cleos.logger.info(
        "refund: Should fail for non existent bridge request"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.refund(50)
    assert "bridge request not found" in repr(e.value)
    
    tevmc.cleos.logger.info(
        "Getting last completed bridge request and lapsing it to verify that it is not refunded"
    )
    last_completed_bridge_request = zero_bridge.get_last_bridge_request()
    assert last_completed_bridge_request['state'] == "completed"
    zero_bridge.lapse_bridge_request(last_completed_bridge_request['bridge_request_id'])

    tevmc.cleos.logger.info(
        "refund: Should fail for bridge request that has been completed"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.refund(last_completed_bridge_request['bridge_request_id'])
    assert "bridge request must be pending" in repr(e.value)
    
    tevmc.cleos.logger.info(
        "Set an invalid evm bridge contract address in order to be able to create requests that require refunds"
    )
    refund_delay_period_mins = 5
    batch_size = 40
    admin = bbf.bridge_z_admin
    version = "v1.0"
    zero_bridge.set_config(
        bbf.token_registry_contract.address,
        bbf.token_registry_contract.address,
        bbf.stake_local_account,
        refund_delay_period_mins,
        batch_size,
        version,
        admin)
    
    tevmc.cleos.logger.info(
        "Create refund request"
    )
    result = bbf.zero_bridge.bridge_z_to_e(z_user, e_user.address, token.to_asset(50))
    tevmc.cleos.logger.info(json.dumps(result, indent=4))

    refund_bridge_request = zero_bridge.get_last_bridge_request()
    assert refund_bridge_request['state'] == "pending"

    tevmc.cleos.logger.info(
        "refund: Should fail for bridge request for which refund delay has not expired"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.refund(refund_bridge_request['bridge_request_id'])
    assert "refund delay period has not expired" in repr(e.value)

    zero_bridge.lapse_bridge_request(refund_bridge_request['bridge_request_id'])

    tevmc.cleos.logger.info(
        "refund: Should work for bridge request for which refund delay has expired and in pending state"
    )
    balance = token.z_balance(z_user)
    zero_bridge.refund(refund_bridge_request['bridge_request_id'])
    balance.amount += 50
    assert token.z_balance(z_user) == balance
    assert refund_bridge_request['state'] == "refunded"


def test_exec_refunds(benybridge):
    bbf = benybridge
    local_w3 = bbf.local_w3
    tevmc = bbf.tevmc
    tevmc.logger.setLevel(logging.DEBUG)
    test_util = BridgeTestUtil(bbf)
    token = bbf.tokens[0]
    zero_bridge = bbf.zero_bridge
    bbf.configure_zero_contract()

    z_user1 = bbf.z_accounts[0]
    z_user2 = bbf.z_accounts[1]
    e_user = bbf.e_accounts[0]

    test_util.assert_bridge_evm_to_zero(
        e_user, z_user1, token, 1000000
    )

    test_util.assert_bridge_evm_to_zero(
        e_user, z_user2, token, 1000000
    )

    test_util.assert_bridge_zero_to_evm(
        z_user1, e_user, token, 100
    )

    tevmc.cleos.logger.info(
        "EXECREFUNDS TESTS"
    )

    tevmc.cleos.logger.info(
        "execrefunds: Should fail for non existent bridge request"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.refund(50)
    assert "bridge request not found" in repr(e.value)
    
    tevmc.cleos.logger.info(
        "Getting last completed bridge request and lapsing it to verify that it is not refunded"
    )
    last_completed_bridge_request = zero_bridge.get_last_bridge_request()
    assert last_completed_bridge_request['state'] == "completed"
    zero_bridge.lapse_bridge_request(last_completed_bridge_request['bridge_request_id'])

    
    tevmc.cleos.logger.info(
        "Set an invalid evm bridge contract address in order to be able to create requests that require refunds"
    )
    refund_delay_period_mins = 5
    batch_size = 40
    admin = bbf.bridge_z_admin
    version = "v1.0"
    zero_bridge.set_config(
        bbf.token_registry_contract.address,
        bbf.token_registry_contract.address,
        bbf.stake_local_account,
        refund_delay_period_mins,
        batch_size,
        version,
        admin)
    
    tevmc.cleos.logger.info(
        "Create refund requests"
    )
    result = bbf.zero_bridge.bridge_z_to_e(z_user1, e_user.address, token.to_asset(50))
    tevmc.cleos.logger.info(json.dumps(result, indent=4))

    refund_bridge_request1 = zero_bridge.get_last_bridge_request()
    assert refund_bridge_request1['state'] == "pending"
    
    result = bbf.zero_bridge.bridge_z_to_e(z_user2, e_user.address, token.to_asset(251))
    tevmc.cleos.logger.info(json.dumps(result, indent=4))

    refund_bridge_request2 = zero_bridge.get_last_bridge_request()
    assert refund_bridge_request2['state'] == "pending"

    result = bbf.zero_bridge.bridge_z_to_e(z_user1, e_user.address, token.to_asset(507))
    tevmc.cleos.logger.info(json.dumps(result, indent=4))

    refund_bridge_request3 = zero_bridge.get_last_bridge_request()
    assert refund_bridge_request3['state'] == "pending"
    
    user1_balance = token.z_balance(z_user1)
    user2_balance = token.z_balance(z_user2)

    tevmc.cleos.logger.info(
        "execrefunds: Should not refund any requests as refund delay period has not expired should throw nothing-to-process error"
    )
    with pytest.raises(Exception) as e:
        zero_bridge.exec_refunds(1)
    assert "Refunds.[nothing-to-process]" in repr(e.value)

    assert last_completed_bridge_request['state'] == "completed"
    assert refund_bridge_request1['state'] == "pending"
    assert refund_bridge_request2['state'] == "pending"
    assert refund_bridge_request3['state'] == "pending"

    assert token.z_balance(z_user1) == user1_balance
    assert token.z_balance(z_user2) == user2_balance

    tevmc.cleos.logger.info(
        "execrefunds: Should work refund bridge request 1"
    )
    zero_bridge.lapse_bridge_request(refund_bridge_request1['bridge_request_id'])
    zero_bridge.exec_refunds(2)
    user1_balance.amount += Asset.from_str(refund_bridge_request1['quantity']).amount
    
    assert refund_bridge_request1['state'] == "refunded"
    assert refund_bridge_request2['state'] == "pending"
    assert refund_bridge_request3['state'] == "pending"

    assert token.z_balance(z_user1) == user1_balance
    assert token.z_balance(z_user2) == user2_balance

    tevmc.cleos.logger.info(
        "execrefunds: Should work refund bridge request 2 and 3"
    )
    zero_bridge.lapse_bridge_request(refund_bridge_request2['bridge_request_id'])
    zero_bridge.lapse_bridge_request(refund_bridge_request3['bridge_request_id'])
    zero_bridge.exec_refunds(3)
    user1_balance.amount += Asset.from_str(refund_bridge_request3['quantity']).amount
    user2_balance.amount += Asset.from_str(refund_bridge_request2['quantity']).amount
    
    assert refund_bridge_request1['state'] == "refunded"
    assert refund_bridge_request2['state'] == "refunded"
    assert refund_bridge_request3['state'] == "refunded"

    assert token.z_balance(z_user1) == user1_balance
    assert token.z_balance(z_user2) == user2_balance