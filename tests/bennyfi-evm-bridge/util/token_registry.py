import time
from eth_account.signers.local import LocalAccount
from util.token import Token
from util.evm_contract import EVMContract
from eth_typing import (
    ChecksumAddress,
)


class TokenRegistry(EVMContract):

    def register_tokens(self, tokens: list[Token]):
        for token in tokens:
            self.register_token(
                token.contract.address,
                token.z_symbol,
                token.z_decimals,
                token.min_amount,
            )

    def register_token(
        self,
        token_contract_address: ChecksumAddress,
        z_symbol: str,
        z_decimals: int,
        min_amount: int,
    ):
        self.logger.info(
            f"Registering Token: {token_contract_address} {z_symbol} {z_decimals} {min_amount}"
        )
        receipt = self.transact(
            "registerToken",
            self.default_account.address,
            token_contract_address,
            z_symbol,
            z_decimals,
            min_amount,
            True,
        )
        assert receipt

    
    def set_active_status(self, token_contract_address: ChecksumAddress, active: bool):
        self.logger.info(
            f"Setting token active status for: {token_contract_address} active: {active}"
        )
        return self.transact(
            "setTokenActiveStatus",
            self.default_account.address,
            token_contract_address,
            active,
        )
    
    def unregister_tokens(self, tokens: list[Token]):
        for token in tokens:
            self.unregister_token(
                token.contract.address
            )


    def unregister_token(self, token_contract_address: ChecksumAddress):
        self.logger.info(
            f"Unregistering token: {token_contract_address}"
        )
        return self.transact(
            "unregisterToken",
            self.default_account.address,
            token_contract_address
        )