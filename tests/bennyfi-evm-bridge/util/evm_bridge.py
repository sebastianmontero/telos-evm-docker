import time
from eth_account.signers.local import LocalAccount
from util.token import Token
from util.evm_contract import EVMContract


class EVMBridge(EVMContract):

    def fee(self) -> int:
        return self.functions.fee().call()

    def set_fee(self, fee: int):
        return self.transact(
            "setFee",
            self.bbf.cleos.evm_default_account.address,
            fee,
        )

    def e_to_z_next_req_id(self) -> int:
        return (
            self.functions.nextBridgeEVMToZeroRequestId().call()
        )

    def e_to_z_req_by_id(self, req_id: int) -> dict | None:
        try:
            return self.functions.getBridgeEVMToZeroRequestById(
                req_id
            ).call()
        except Exception as e:
            self.logger.info(
                f"Bridge evm to zero request not found error:{e}\n"
            )
            return None
        

    def token_balance(self, token: Token) -> int:
        return self.functions.tokenBalances(
            token.contract.address
        ).call()

    def bridge_e_to_z(
        self,
        e_user: LocalAccount,
        z_user: str,
        token: Token,
        e_amount: int,
        fee: int = None,
    ) -> dict:
        fee = fee if fee else self.fee()
        receipt = self.transact(
            "bridgeEVMToZero",
            {
                "from": e_user.address,
                "value": fee,
            },
            z_user,
            token.contract.address,
            e_amount,
        )
        events = self.events.BridgeEVMToZeroRequestQueued().process_receipt(
            receipt
        )
        return {"receipt": receipt, "event": events[0]}

