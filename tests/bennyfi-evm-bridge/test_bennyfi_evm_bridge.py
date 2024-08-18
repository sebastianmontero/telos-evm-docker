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
from util.bridge_test_util import BridgeTestUtil
from conftest import BenyBridgeFixture

DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 991000


def test_all(benybridge):
    bbf = benybridge
    tevmc = bbf.tevmc
    tevmc.logger.setLevel(logging.DEBUG)
    test_util = BridgeTestUtil(bbf)
    token = bbf.tokens[0]
    bbf.init_zero_contract()
    # tevmc.cleos.logger.info(
    #     "TEST BRIDGE FROM EVM TO ZERO TOKEN WITH SAME NAME DIFFERENT PRECISION WITHOUT BRIDGE FEE"
    # )
    # test_util.assert_bridge_evm_to_zero(
    #     bbf.e_accounts[0], bbf.z_accounts[0], token, 847348
    # )

    # tevmc.cleos.logger.info(
    #     "TEST BRIDGE FROM ZERO TO EVM TOKEN WITH SAME NAME DIFFERENT PRECISION"
    # )
    # test_util.assert_bridge_zero_to_evm(
    #     bbf.z_accounts[0], bbf.e_accounts[0], token, 5173
    # )

    # test_util.set_fee(1000)
    # tevmc.cleos.logger.info(
    #     "TEST BRIDGE MORE TOKENS FROM EVM TO ZERO TOKEN WITH SAME NAME DIFFERENT PRECISION WITH BRIDGE FEE"
    # )
    # token = bbf.tokens[0]
    # test_util.assert_bridge_evm_to_zero(
    #     bbf.e_accounts[0], bbf.z_accounts[0], token, 1349347
    # )

    # tevmc.cleos.logger.info(
    #     "BRDIGE TOKENS TO STAKE LOCAL ACCOUNT WITH SAME NAME DIFFERENT PRECISION"
    # )
    # test_util.assert_bridge_evm_to_zero(
    #     bbf.e_accounts[0], bbf.stake_local_account, token, 9847348
    # )
    # pool_id = 2
    # yield_source = token.yield_source_name()
    # tevmc.cleos.logger.info(
    #     "TEST STAKE TOKEN WITH SAME NAME DIFFERENT PRECISION"
    # )
    # test_util.assert_stake(pool_id, yield_source, token, 4847348, 24)

    # tevmc.cleos.logger.info(
    #     "TEST UNSTAKE TOKEN WITH SAME NAME DIFFERENT PRECISION"
    # )
    # test_util.assert_unstake(pool_id, yield_source, token, 3247348)

    # tevmc.cleos.logger.info(
    #     "TEST BRIDGE FROM EVM TO ZERO TOKEN WITH DIFFERENT NAME SAME PRECISION WITH FEE"
    # )
    # token = bbf.tokens[1]
    # test_util.assert_bridge_evm_to_zero(
    #     bbf.e_accounts[0], bbf.z_accounts[0], token, 142348
    # )

    token = bbf.tokens[1]
    tevmc.cleos.logger.info(
        "TEST BRIDGE FROM EVM TO ZERO TOKEN WITH DIFFERENT NAME SAME PRECISION WITH FEE TO DIFFERENT ACCOUNTS"
    )
    test_util.assert_bridge_evm_to_zero(
        bbf.e_accounts[1], bbf.z_accounts[2], token, 517342
    )

    tevmc.cleos.logger.info(
        "TEST BRIDGE FROM ZERO TO EVM TOKEN WITH DIFFERENT NAME SAME PRECISION"
    )
    test_util.assert_bridge_zero_to_evm(
        bbf.z_accounts[2], bbf.e_accounts[0], token, 21738
    )

    tevmc.cleos.logger.info(
        "BRDIGE TOKENS TO STAKE LOCAL ACCOUNT WITH DIFFERENT NAME SAME PRECISION"
    )
    test_util.assert_bridge_evm_to_zero(
        bbf.e_accounts[0], bbf.stake_local_account, token, 28453
    )

    pool_id = 5
    yield_source = token.yield_source_name()
    tevmc.cleos.logger.info(
        "TEST STAKE TOKEN WITH DIFFERENT NAME SAME PRECISION"
    )
    test_util.assert_stake(pool_id, yield_source, token, 28453, 24)

    tevmc.cleos.logger.info(
        "TEST UNSTAKE TOKEN WITH SAME NAME DIFFERENT PRECISION"
    )
    test_util.assert_unstake(pool_id, yield_source, token, 28453)

