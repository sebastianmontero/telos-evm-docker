#!/usr/bin/env python3

import logging


from pathlib import Path




import pytest

from typing import Type

from eth_account import Account
from eth_typing import (
    ChecksumAddress,
)
from eth_account.signers.local import (
    LocalAccount,
)
from leap.sugar import random_string
from leap.protocol import Asset
from tevmc.config import local
from tevmc.testing import bootstrap_test_stack
from tevmc.testing import open_web3
from tevmc import TEVMController
from tevmc.cleos_evm import CLEOSEVM
from web3 import Web3
from web3.contract import (
    Contract
)

from util.util_zero import UtilZero
from util.evm_transaction_signer import EVMTransactionSigner
from util.token import Token

DEFAULT_GAS_PRICE = 524799638144
DEFAULT_GAS = 991000

@pytest.fixture()
def benybridge(request, tmp_path_factory):
    request.applymarker(pytest.mark.config(**local.default_config))
    with bootstrap_test_stack(request, tmp_path_factory) as tevmc:
        tevmc.logger.setLevel(logging.DEBUG)
        bbf = BenyBridgeFixture(tevmc)
        yield bbf


class BenyBridgeFixture:

    def __init__(self, tevmc: TEVMController):
        self.tevmc: TEVMController = tevmc
        self.cleos: CLEOSEVM = tevmc.cleos
        self.local_w3: Web3 = open_web3(tevmc)
        self.local_w3.from_wei
        self.evm_transaction_signer = EVMTransactionSigner(self.local_w3, default_gas_price=DEFAULT_GAS_PRICE, default_gas=DEFAULT_GAS)
        self.evm_transaction_signer.add_account(tevmc.cleos.evm_default_account)
        self.util_z = UtilZero(self.cleos)
        self.tokens = [
            Token(self.cleos, "mta", "MTA", "MTA", 8, 6, 50, 100),
            Token(self.cleos, "mtb", "MTB", "WMTB", 7, 4, 4, 100),
            Token(self.cleos, "mtc", "MTC", "MTC", 4, 3, 1, 100)
        ]
        tevmc.cleos.push_action('eosio.evm', 'setrevision', [2], 'eosio.evm')
        self.util_z.create_delegated_account('eosio', 'message.evm', 'eosio.evm')
        assert self.local_w3.is_connected()
        self.__deploy_contracts()
        self.z_accounts = self.__create_zero_accounts(5)
        self.e_accounts = self.__create_evm_accounts(5)
        self.__fund_evm_accounts_with_tlos(self.e_accounts)
        self.__fund_evm_accounts_with_tokens(self.tokens, self.e_accounts)
        self.__register_tokens(self.tokens)
        self.__register_yield_sources(self.tokens)

    def __deploy_contracts(self):
        tevmc = self.tevmc
        local_w3 = self.local_w3
        tevmc.cleos.logger.info("Deploying mock stake local contract...")
        self.stake_local_account = "stakelocal"
        tevmc.cleos.deploy_contract_from_path(
            self.stake_local_account,
            Path("../bennyfi-evm-bridge/zero/artifacts/mock.stake.origin/build/stakeorigin"),
            contract_name="stakeorigin",
        )
        tevmc.cleos.logger.info("Deploying bridge zero contract...")
        self.bridge_z_account = "benybridge"
        tevmc.cleos.deploy_contract_from_path(
            self.bridge_z_account,
            Path("../bennyfi-evm-bridge/zero/build/benybridge"),
            contract_name=self.bridge_z_account,
        )
        tevmc.cleos.create_evm_account(self.bridge_z_account, random_string())
        tevmc.cleos.logger.info("Getting bridge_z_eth_addr...")
        self.bridge_z_eth_addr = local_w3.to_checksum_address(
            tevmc.cleos.eth_account_from_name(self.bridge_z_account)
        )
        assert self.bridge_z_eth_addr

        tevmc.cleos.logger.info("Funding bridge zero contract...")
        quantity_native = Asset.from_str("1000.0000 TLOS")
        quantity_evm = Asset.from_str("100.0000 TLOS")
        tevmc.cleos.transfer_token("eosio", self.bridge_z_account, quantity_native, "")
        tevmc.cleos.transfer_token(self.bridge_z_account, "eosio.evm", quantity_evm, "")
        assert local_w3.eth.get_transaction_count(self.bridge_z_eth_addr) == 1

        self.__deploy_token_contracts(self.tokens)


        tevmc.cleos.logger.info("Deploying TokenRegistry...")
        self.token_registry_contract = tevmc.cleos.eth_deploy_contract_from_json(
            Path(
                "../bennyfi-evm-bridge/evm/artifacts/contracts/TokenRegistry.sol/TokenRegistry.json"
            ),
            "TokenRegistry",
        )

        tevmc.cleos.logger.info("Deploying YieldSourceRegistry...")
        self.yield_source_registry_contract = tevmc.cleos.eth_deploy_contract_from_json(
            Path(
                "../bennyfi-evm-bridge/evm/artifacts/contracts/YieldSourceRegistry.sol/YieldSourceRegistry.json"
            ),
            "YieldSourceRegistry",
        )

        tevmc.cleos.logger.info("Deploying MockYieldSourceAdaptor...")
        self.mock_yield_source_adaptor = tevmc.cleos.eth_deploy_contract_from_json(
            Path(
                "../bennyfi-evm-bridge/evm/artifacts/contracts/mocks/MockYieldSourceAdaptor.sol/MockYieldSourceAdaptor.json"
            ),
            "MockYieldSourceAdaptor",
        )

        tevmc.cleos.logger.info("Deploying Bridge E...")
        self.bridge_e_contract = tevmc.cleos.eth_deploy_contract_from_json(
            Path(
                "../bennyfi-evm-bridge/evm/artifacts/contracts/BennyfiBridge.sol/BennyfiBridge.json"
            ),
            "BennyfiBridge",
            constructor_arguments=[
                self.bridge_z_eth_addr,
                self.bridge_z_account,
                self.token_registry_contract.address,
                self.yield_source_registry_contract.address,
                0,
                10,
            ],
        )

        tevmc.cleos.logger.info("Calling init action...")
        tevmc.cleos.push_action(
            self.bridge_z_account,
            "init",
            [
                self.bridge_e_contract.address[2:],
                self.token_registry_contract.address[2:],
                self.stake_local_account,
                "v1.0",
                self.bridge_z_account,
            ],
            self.bridge_z_account,
        )

    def __create_zero_accounts(self, num_accounts: int) -> list[str]:
        accounts = []
        for i in range(num_accounts):
            account = f"user{chr(ord('a') + i)}"
            self.cleos.create_account_staked("eosio", account)
            accounts.append(account)
        return accounts

    def __create_evm_accounts(self, num_accounts) -> list[LocalAccount]:
        accounts = []
        for i in range(num_accounts):
            account = Account.create()
            accounts.append(account)
            self.evm_transaction_signer.add_account(account)
        return accounts

    def __fund_evm_accounts_with_tlos(
        self,
        accounts: list[LocalAccount],
        amount: int = 10000,
        name: str = 'evmuser2',
        data: str = 'foobar',
    ):
        self.cleos.new_account(
            name,
            key=self.cleos.keys['eosio'])

        gas_allowance = 20

        total_needed = len(accounts)*amount + gas_allowance

        self.cleos.create_evm_account(name, data)
        quantity = Asset.from_ints(total_needed * (10 ** 4), 4, 'TLOS')

        self.cleos.transfer_token('eosio', name, quantity, ' ')
        self.cleos.transfer_token(name, 'eosio.evm', quantity, 'Deposit')

        self.cleos.wait_blocks(3)

        eth_addr = self.cleos.eth_account_from_name(name)
        assert eth_addr

        self.cleos.logger.info(f'{name}: {eth_addr}')
        for account in accounts:
            self.cleos.eth_transfer(
                eth_addr,
                account.address,
                Asset.from_ints(amount * (10 ** 4), 4, 'TLOS'),
                account='evmuser2'
            )
    
    def __fund_evm_accounts_with_tokens(
        self,
        tokens: list[Token],
        accounts: list[LocalAccount]
    ):
    
        for token in tokens:
            self.cleos.logger.info(f'Minting {token.initial_amount} {token.e_symbol} to accounts')
            self.__fund_evm_accounts_with_token(token.contract, accounts, token.initial_amount_e)

    def __fund_evm_accounts_with_token(
        self,
        token_contract: Contract,
        accounts: list[LocalAccount],
        amount: int = 100000000000
    ):
    
        for account in accounts:
            self.cleos.logger.info(f'Minting {amount} to {account.address}')
            receipt = self.evm_transaction_signer.transact(
            token_contract,
            'mint',
            self.cleos.evm_default_account.address,
            account.address,
            amount)
            assert receipt

    def __deploy_token_contracts(self, tkns: list[Token]):
        for tkn in tkns:
            contract = self.__deploy_token_contract(tkn.name, tkn.e_symbol, tkn.e_decimals)
            tkn.add_contract(contract)
    
    def __deploy_token_contract(self, name: str, symbol: str, decimals: int) -> Contract:
        self.cleos.logger.info(f"Deploying Token contract: {name} {symbol} {decimals}")
        token_contract = self.cleos.eth_deploy_contract_from_json(
            Path(
                "../bennyfi-evm-bridge/evm/artifacts/contracts/mocks/MockToken.sol/MockToken.json"
            ),
            name,
            constructor_arguments=[name, symbol, decimals],
        )
        assert token_contract.functions.symbol().call() == symbol
        assert token_contract.functions.decimals().call() == decimals
        return token_contract

    def __register_tokens(self, tokens: list[Token]):
        for token in tokens:
            self.__register_token(token.contract.address, token.z_symbol, token.z_decimals, token.min_amount)

    def __register_token(self, token_contract_address: ChecksumAddress, z_symbol: str, z_decimals: int, min_amount: int):
        self.cleos.logger.info(f"Registering Token: {token_contract_address} {z_symbol} {z_decimals} {min_amount}")
        receipt = self.evm_transaction_signer.transact(
            self.token_registry_contract,
            "registerToken",
            self.cleos.evm_default_account.address,
            token_contract_address, 
            z_symbol,
            z_decimals,
            min_amount,
            True
        )
        assert receipt

    def __register_yield_sources(self, tokens: list[Token]):
        for token in tokens:
            self.__register_yield_source(token.yield_source_name(), self.mock_yield_source_adaptor.address)

    def __register_yield_source(self, name: str, adaptor_contract_address: ChecksumAddress):
        self.cleos.logger.info(f"Registering yield source: {name} {adaptor_contract_address}")
        receipt = self.evm_transaction_signer.transact(
            self.yield_source_registry_contract,
            "setYieldSource",
            self.cleos.evm_default_account.address,
            name,
            adaptor_contract_address,
            True
        )
        assert receipt