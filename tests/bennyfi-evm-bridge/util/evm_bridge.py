import time
from eth_account.signers.local import LocalAccount
from util.token import Token


class EVMBridge:
    def __init__(self, bbf):
        self.bbf = bbf

    def fee(self) -> int:
        return self.bbf.bridge_e_contract.functions.fee().call()

    def set_fee(self, fee: int):
        return self.bbf.evm_transaction_signer.transact(
            self.bbf.bridge_e_contract,
            "setFee",
            self.bbf.cleos.evm_default_account.address,
            fee,
        )

    def e_to_z_next_req_id(self) -> int:
        return (
            self.bbf.bridge_e_contract.functions.nextBridgeEVMToZeroRequestId().call()
        )

    def e_to_z_req_by_id(self, req_id: int) -> dict:
        return self.bbf.bridge_e_contract.functions.getBridgeEVMToZeroRequestById(
            req_id
        ).call()

    def token_balance(self, token: Token) -> int:
        return self.bbf.bridge_e_contract.functions.tokenBalances(
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
        receipt = self.bbf.evm_transaction_signer.transact(
            self.bbf.bridge_e_contract,
            "bridgeEVMToZero",
            {
                "from": e_user.address,
                "value": fee,
            },
            z_user,
            token.contract.address,
            e_amount,
        )
        events = self.bbf.bridge_e_contract.events.BridgeEVMToZeroRequestQueued().process_receipt(
            receipt
        )
        return {"receipt": receipt, "event": events[0]}
    

    def get_events(self, event_name: str, count: int) -> list:
        time.sleep(1)
        events = self.bbf.bridge_e_contract.events[event_name]().get_logs(
            fromBlock=0,
            toBlock='latest',
        )
        assert len(events) >= count, f"Expected at least {count} events, got {len(events)}"
        return events[-count:]
