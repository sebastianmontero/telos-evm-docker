from web3.contract import (
    Contract
)

class Token:
    def __init__(self, name: str, e_symbol: str, z_symbol: str, e_decimals: int, z_decimals: int, initial_amount: int):
        self.name = name
        self.e_symbol = e_symbol
        self.z_symbol = z_symbol
        self.e_decimals = e_decimals
        self.z_decimals = z_decimals
        self.initial_amount = initial_amount
        self.initial_amount_e = self.to_decimals(initial_amount, e_decimals)
        self.initial_amount_z = self.to_decimals(initial_amount, z_decimals)
        
    def add_contract(self, contract: Contract):
        self.contract = contract

    @staticmethod
    def to_decimals(amount: int, decimals: int) -> int:
        return amount * 10 ** decimals