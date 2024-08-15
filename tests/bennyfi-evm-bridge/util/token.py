from eth_typing import (
    ChecksumAddress,
)
from web3.contract import (
    Contract
)
from tevmc.cleos_evm import CLEOSEVM

from leap.protocol import Asset, Symbol

class Token:
    @staticmethod
    def to_decimals(amount: int, decimals: int) -> int:
        return amount * 10 ** decimals
    
    def __init__(self, cleos: CLEOSEVM, name: str, e_symbol: str, z_symbol: str, e_decimals: int, z_decimals: int, min_amount: int, initial_amount: int):
        self.cleos = cleos
        self.name = name
        self.e_symbol = e_symbol
        self.z_symbol = z_symbol
        self.e_decimals = e_decimals
        self.z_decimals = z_decimals
        self.min_amount = min_amount
        self.initial_amount = initial_amount
        self.initial_amount_e = self.to_decimals(initial_amount, e_decimals)
        self.initial_amount_z = self.to_decimals(initial_amount, z_decimals)
        
    def add_contract(self, contract: Contract):
        self.contract = contract
    
    def e_balance(self, address: ChecksumAddress) -> int:
        return self.contract.functions.balanceOf(address).call()
    
    def z_balance(self, account: str) -> Asset:
        balances = self.cleos.get_table(
            "benybridge",
            account,
            'accounts',
            limit=1,
            lower_bound=self.z_symbol,
            upper_bound=self.z_symbol
            )
        if len(balances) == 0:
            return self.zero_asset()
        
        return Asset.from_str(balances[0]['balance'])
    
    def z_supply(self) -> Asset:
        stat = self.z_stats()
        if stat is None:
            return self.zero_asset()
        
        return Asset.from_str(stat['supply'])
    
    def z_stats(self) -> dict | None:
        stats = self.cleos.get_table(
            "benybridge",
            self.z_symbol,
            'stat'
            )
        if len(stats) == 0:
            return None
        
        return stats[0]
    
    def zero_asset(self) -> Asset:
        return self.to_asset(0)
    
    def z_to_e_amount(self, z_amount: int) -> int:
        return self.to_decimals(z_amount, self.e_decimals - self.z_decimals)
    
    def yield_source_name(self) -> str:
        return f'{self.name}ys'
    def to_asset(self, amount: int) -> Asset:
        symbol = Symbol.from_str(f'{self.z_decimals},{self.z_symbol}')
        return Asset(amount, symbol)