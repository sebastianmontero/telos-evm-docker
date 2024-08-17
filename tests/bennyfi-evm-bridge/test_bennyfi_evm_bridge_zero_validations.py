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
    tevmc.cleos.logger.info(
        "Should fail for already initialized contract"
    )
    with pytest.raises(Exception) as e:
        tevmc.cleos.push_action(
            bbf.bridge_z_account,
            "init",
            [
                bbf.bridge_e_contract.address[2:],
                bbf.token_registry_contract.address[2:],
                bbf.stake_local_account,
                "v1.0",
                bbf.bridge_z_account,
            ],
            bbf.bridge_z_account,
        )
    assert "contract already initialized" in str(e)
    # try:
    #     tevmc.cleos.push_action(
    #             bbf.bridge_z_account,
    #             "init",
    #             [
    #                 bbf.bridge_e_contract.address[2:],
    #                 bbf.token_registry_contract.address[2:],
    #                 bbf.stake_local_account,
    #                 "v1.0",
    #                 bbf.bridge_z_account,
    #             ],
    #             bbf.bridge_z_account,
    #         )
    # except Exception as e:
    #     tevmc.cleos.logger.info(f"Exception: {e}")
    

