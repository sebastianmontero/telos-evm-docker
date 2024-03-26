#!/usr/bin/env python3

import pytest


@pytest.mark.stack_config(
    from_template='template',
    exist_ok=False, teardown=False,

    chain_name='telos-mainnet-testing'
)
def test_mainnet_start(tevmc):
    ...


@pytest.mark.stack_config(
    from_template='template',
    target_dir='tests/test_mainnet',
    exist_ok=False, teardown=False,

    chain_name='telos-mainnet-testing'
)
def test_mainnet_start_no_teardown(tevmc):
    ...

@pytest.mark.stack_config(
    from_dir='tests/test_mainnet',
    exist_ok=True, teardown=False,

    chain_name='telos-mainnet-testing'
)
def test_mainnet_start_existing(tevmc):
    ...


@pytest.mark.stack_config(
    from_template='template',
    target_dir='tests/test_mainnet',
    exist_ok=True, teardown=True,

    chain_name='telos-mainnet-testing'
)
def test_mainnet_stop_existing(tevmc):
    ...

