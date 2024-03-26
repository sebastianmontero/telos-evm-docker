#!/usr/bin/env python3

import pytest

from leap.sugar import random_string
from leap.protocol import Asset

from tevmc.utils import to_wei


def test_evm_start_fresh(tevmc):
    ...


@pytest.mark.stack_config(
    target_dir='tests/nodes/test_evm',
    exist_ok=True, teardown=False
)
def test_evm_start_keep_running(tevmc):
    ...


@pytest.mark.stack_config(
    target_dir='tests/nodes/test_evm',
    exist_ok=True, teardown=False
)
def test_evm_web3(tevmc):
    """Create a random account and have it create a random evm account,
    then get its ethereum address.
    Send some TLOS and verify in the ethereum side the balance gets added.
    """

    leap_service = tevmc.get_service('leap')
    cleos = leap_service.cleos

    rpc_service = tevmc.get_service('rpc')
    local_w3 = rpc_service.w3

    account = cleos.new_account()

    cleos.create_evm_account(account, random_string())

    eth_addr = cleos.eth_account_from_name(account)
    assert eth_addr

    quantity = Asset.from_str('100.0000 TLOS')

    cleos.transfer_token('eosio', account, quantity, 'evm test')
    cleos.transfer_token(account, 'eosio.evm', quantity, 'Deposit')

    # get balance by checking telos.evm table
    balance = cleos.eth_get_balance(eth_addr)

    assert balance == to_wei(quantity.amount // (10 ** quantity.symbol.precision), 'ether')

    # get balance by hitting evm rpc api
    rpc_balance = local_w3.eth.get_balance(
        local_w3.to_checksum_address(eth_addr))

    assert balance == rpc_balance


@pytest.mark.stack_config(
    target_dir='tests/nodes/test_evm',
    exist_ok=True,
)
def test_evm_stop_running(tevmc):
    ...
