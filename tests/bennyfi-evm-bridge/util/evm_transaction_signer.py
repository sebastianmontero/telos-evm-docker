from web3 import Web3
from eth_account.signers.local import LocalAccount
from web3.types import TxParams, Wei
from typing import Union, Dict

class EVMTransactionSigner:
    def __init__(self, w3: Web3, default_gas: int = 2000000, default_gas_price: Union[int, str] = 'auto'):
        self.w3 = w3
        self.accounts = {}
        self.default_gas = default_gas
        self.default_gas_price = default_gas_price

    def add_account(self, account_or_key: Union[LocalAccount, str]):
        if isinstance(account_or_key, LocalAccount):
            account = account_or_key
        else:
            account = LocalAccount.from_key(account_or_key)
        
        self.accounts[account.address] = account
        return account

    def transact(self, contract, function_name: str, tx_parameters: Union[str, Dict] = None, *args, **kwargs):
        # Prepare the transaction parameters
        tx_params = self._prepare_tx_params(tx_parameters)

        # Get the contract function
        contract_function = getattr(contract.functions, function_name)

        # Build the transaction
        transaction = contract_function(*args, **kwargs).build_transaction(tx_params)

        # Get the account to sign with
        account = self._get_account_for_transaction(tx_params['from'])

        # Sign the transaction
        signed_txn = account.sign_transaction(transaction)

        # Send the transaction
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        # Wait for transaction receipt
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return tx_receipt

    def _prepare_tx_params(self, tx_parameters: Union[str, Dict]) -> TxParams:
        if isinstance(tx_parameters, str):
            tx_params = {'from': tx_parameters}
        elif isinstance(tx_parameters, dict):
            tx_params = tx_parameters.copy()
        else:
            tx_params = {}

        if 'from' not in tx_params:
            raise ValueError("'from' address must be specified in tx_parameters")

        if 'gas' not in tx_params:
            tx_params['gas'] = self.default_gas

        if 'gasPrice' not in tx_params:
            tx_params['gasPrice'] = self.w3.eth.gas_price if self.default_gas_price == 'auto' else self.default_gas_price

        if 'nonce' not in tx_params:
            tx_params['nonce'] = self.w3.eth.get_transaction_count(tx_params['from'])

        return tx_params

    def _get_account_for_transaction(self, address: str) -> LocalAccount:
        for account in self.accounts.values():
            if account.address.lower() == address.lower():
                return account
        raise ValueError(f"No account found for address {address}")

# Usage example:
# signer = TransactionSigner(local_w3, default_gas=2000000, default_gas_price='auto')
# signer.add_account(tevmc.cleos.evm_default_account.key, 'default')
# tx_receipt = signer.transact(mock_token_contract, 'mint', user1.address, 10000, tx_parameters='0xYourAddress')
# print(f"Transaction hash: {tx_receipt['transactionHash'].hex()}")