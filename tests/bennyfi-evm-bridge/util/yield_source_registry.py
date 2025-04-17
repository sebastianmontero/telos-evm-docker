import time
from eth_account.signers.local import LocalAccount
from util.token import Token
from util.evm_contract import EVMContract
from eth_typing import (
    ChecksumAddress,
)


class YieldSourceRegistry(EVMContract):

    def register_yield_source(
        self, name: str, adaptor_contract_address: ChecksumAddress
    ):
        self.logger.info(
            f"Registering yield source: {name} {adaptor_contract_address}"
        )
        receipt = self.transact(
            "setYieldSource",
            self.default_account.address,
            name,
            adaptor_contract_address,
            True,
        )
        assert receipt