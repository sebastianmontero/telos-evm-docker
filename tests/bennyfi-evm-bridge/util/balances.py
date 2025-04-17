from util.token_test_util import TokenTestUtil
from util.token import Token
from eth_account.signers.local import (
    LocalAccount,
)

class Balances:
    def __init__(self, bbf) -> None:
        self.bbf = bbf
        self.zero = {}
        self.evm = {}
        self.supplies = {}

    def load_balances(self, objs: list[dict], zero_key: str, evm_key: str, token_key: str = "token"):
      for obj in objs:
          token = obj[token_key]
          if token.name not in self.zero:
              self.zero[token.name] = {}
              self.evm[token.name] = {}
          if obj[zero_key] not in self.zero[token.name]:
              self.zero[token.name][obj[zero_key]] = token.z_balance(obj[zero_key])
          if token.name not in self.supplies:
              self.supplies[token.name] = token.z_supply()
          if obj[evm_key] not in self.evm[token.name]:
              self.evm[token.name][obj[evm_key].address] = token.e_balance(obj[evm_key].address)

    def add_evm_balances(self, owner: LocalAccount):
          for token_name in self.evm:
              token = self.bbf.token_map[token_name]
              self.evm[token_name][owner.address] = token.e_balance(owner.address)
       
    def update_zero_balance(self, owner: str, token: Token, amount: int):
      assert token.name in self.zero, f"No zero balance for token: {token.name}"
      assert owner in self.zero[token.name], f"No zero balance for user: {owner} and token: {token.name}"
      self.zero[token.name][owner].amount += amount

    def update_evm_balance(self, owner: LocalAccount, token: Token, amount: int):
      assert token.name in self.evm, f"No evm balance for token: {token.name}"
      assert owner.address in self.evm[token.name], f"No evm balance for user: {owner.address} and token: {token.name}"
      self.evm[token.name][owner.address] += amount

    def update_supply(self, token: Token, amount: int):
      assert token.name in self.supplies, f"No supply for token: {token.name}"
      self.supplies[token.name].amount += amount

    
    def assert_balances(self):
      self.assert_zero_balances()
      self.assert_evm_balances()
      self.assert_supplies()

    def assert_zero_balances(self):
      for token_name, balances in self.zero.items():
          token = self.bbf.token_map[token_name]
          for owner, balance in balances.items():
            actual = token.z_balance(owner)
            assert actual == balance, (
                f"user: {owner} zero balance does not match {actual} != {balance}"
            )

    def assert_evm_balances(self):
      for token_name, balances in self.evm.items():
          token = self.bbf.token_map[token_name]
          for owner, balance in balances.items():
            actual = token.e_balance(owner)
            assert actual == balance, (
                f"user: {owner} evm balance for {token.e_symbol} token does not match {actual} != {balance}"
            )
    
    def assert_supplies(self):
      for token_name, supply in self.supplies.items():
          token = self.bbf.token_map[token_name]
          assert token.z_supply() == supply, (
              f"z supply does not match {token.z_supply()} != {supply}"
          )
          TokenTestUtil.assert_stats(token, supply, self.bbf.bridge_z_account)