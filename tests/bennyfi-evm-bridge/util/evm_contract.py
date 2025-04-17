import time
from typing import Dict, Union
from web3.contract import Contract
from web3.types import TxReceipt


class EVMContract:
    def __init__(self, bbf, contract: Contract):
        self.bbf = bbf
        self.logger = bbf.cleos.logger
        self.contract = contract
        self.events = contract.events
        self.functions = contract.functions
        self.default_account = bbf.cleos.evm_default_account

    
    def get_events(self, event_name: str, count: int) -> list:
        time.sleep(1)
        events = self.events[event_name]().get_logs(
            fromBlock=0,
            toBlock='latest',
        )
        assert len(events) >= count, f"Expected at least {count} events, got {len(events)}"
        return events[-count:]

    def transact(self, function_name: str, tx_parameters: Union[str, Dict] = None, *args, **kwargs) -> TxReceipt:
        return self.bbf.evm_transaction_signer.transact(
            self.contract,
            function_name,
            tx_parameters,
            *args,
            **kwargs,
        )
