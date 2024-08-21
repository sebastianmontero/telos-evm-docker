import json
import logging
import pytest
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import (
    ChecksumAddress,
)

# from w3multicall.multicall import W3Multicall

from pathlib import Path
from leap.sugar import random_string
from leap.protocol import Asset
from tevmc.testing import open_web3
from tevmc.cleos_evm import CLEOSEVM

from tevmc.utils import to_wei
from web3.middleware.signing import construct_sign_and_send_raw_middleware
from web3 import Web3
from util.evm_transaction_signer import EVMTransactionSigner
from util.token import Token


class BridgeTestUtil:

  def __init__(self, bbf) -> None:
    self.bbf = bbf
    self.cleos: CLEOSEVM = bbf.cleos

  def assert_bridge_evm_to_zero(
    self,
    e_user: LocalAccount,
    z_user: str,
    token: Token,
    z_amount: int,
  ):
      tevmc = self.bbf.tevmc
      local_w3: Web3 = self.bbf.local_w3
      evm_transaction_signer = self.bbf.evm_transaction_signer

      e_user_balance = token.e_balance(e_user.address)
      z_user_balance = token.z_balance(z_user)
      e_bridge_balance = self.bbf.bridge_e_contract.functions.tokenBalances(
          token.contract.address
      ).call()
      z_bridge_eth_balance = local_w3.eth.get_balance(self.bbf.bridge_z_eth_addr)
      z_supply = token.z_supply()
      e_amount = token.z_to_e_amount(z_amount)
      self.cleos.logger.info(
          f"z user balance: {z_user_balance} z user balance type: {type(z_user_balance)} e user balance: {e_user_balance} bridge balance: {e_bridge_balance} z supply: {z_supply} z supply type: {type(z_supply)} z amount: {z_amount} e amount: {e_amount}"
      )
      self.cleos.logger.info("Set allowance to bridge e...")
      receipt = evm_transaction_signer.transact(
          token.contract,
          "approve",
          e_user.address,
          self.bbf.bridge_e_contract.address,
          e_amount,
      )
      assert receipt
      fee = self.bbf.bridge_e_contract.functions.fee().call()
      self.cleos.logger.info("Bridge evm to zero...")
      receipt = evm_transaction_signer.transact(
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
      assert receipt

      e_user_balance -= e_amount
      e_bridge_balance += e_amount
      z_user_balance.amount += z_amount
      z_supply.amount += z_amount
      z_bridge_eth_balance += fee
      assert token.e_balance(e_user.address) == e_user_balance
      assert token.e_balance(self.bbf.bridge_e_contract.address) == e_bridge_balance
      assert (
          self.bbf.bridge_e_contract.functions.tokenBalances(token.contract.address).call()
          == e_bridge_balance
      )
      assert token.z_balance(z_user) == z_user_balance
      assert token.z_supply() == z_supply
      assert local_w3.eth.get_balance(self.bbf.bridge_z_eth_addr) == z_bridge_eth_balance
      self.assert_stats(token, z_supply)


  def assert_bridge_zero_to_evm(
      self,
      z_user: str,
      e_user: LocalAccount,
      token: Token,
      z_amount: int,
  ):
      tevmc = self.bbf.tevmc
      e_user_balance = token.e_balance(e_user.address)
      z_user_balance = token.z_balance(z_user)
      e_bridge_balance = self.bbf.bridge_e_contract.functions.tokenBalances(
          token.contract.address
      ).call()
      z_supply = token.z_supply()
      e_amount = token.z_to_e_amount(z_amount)
      asset_amount = token.to_asset(z_amount)
      self.cleos.logger.info(
          f"z user balance: {z_user_balance} z user balance type: {type(z_user_balance)} e user balance: {e_user_balance} bridge balance: {e_bridge_balance} z supply: {z_supply} z supply type: {type(z_supply)} z amount: {z_amount} e amount: {e_amount}"
      )

      result = self.bbf.zero_bridge.bridge_z_to_e(z_user, e_user.address, str(asset_amount))
      self.cleos.logger.info(json.dumps(result, indent=4))

      e_user_balance += e_amount
      e_bridge_balance -= e_amount
      z_user_balance.amount -= z_amount
      z_supply.amount -= z_amount
      assert token.e_balance(e_user.address) == e_user_balance
      assert token.e_balance(self.bbf.bridge_e_contract.address) == e_bridge_balance
      assert (
          self.bbf.bridge_e_contract.functions.tokenBalances(token.contract.address).call()
          == e_bridge_balance
      )
      assert token.z_balance(z_user) == z_user_balance
      assert token.z_supply() == z_supply
      self.assert_stats(token, z_supply)
      self.assert_bridge_request(z_user, e_user, str(asset_amount), "completed")

  def assert_stake(
      self,
      pool_id: int,
      yield_source: str,
      token: Token,
      z_amount: int,
      staking_period_hrs: int
  ):
      tevmc = self.bbf.tevmc
      mock_yield_source_adaptor_balance = token.e_balance(self.bbf.mock_yield_source_adaptor.address)
      stake_local_balance = token.z_balance(self.bbf.stake_local_account)
      e_bridge_balance = self.bbf.bridge_e_contract.functions.tokenBalances(
          token.contract.address
      ).call()
      z_supply = token.z_supply()
      e_amount = token.z_to_e_amount(z_amount)
      asset_amount = token.to_asset(z_amount)
      
      result = self.bbf.zero_bridge.stake(pool_id, yield_source, asset_amount, staking_period_hrs)
      self.cleos.logger.info(json.dumps(result, indent=4))

      mock_yield_source_adaptor_balance += e_amount
      e_bridge_balance -= e_amount
      stake_local_balance.amount -= z_amount
      z_supply.amount -= z_amount
      assert token.e_balance(self.bbf.mock_yield_source_adaptor.address) == mock_yield_source_adaptor_balance
      assert token.e_balance(self.bbf.bridge_e_contract.address) == e_bridge_balance
      assert (
          self.bbf.bridge_e_contract.functions.tokenBalances(token.contract.address).call()
          == e_bridge_balance
      )
      assert token.z_balance(self.bbf.stake_local_account) == stake_local_balance
      assert token.z_supply() == z_supply
      self.assert_stats(token, z_supply)
      self.assert_stake_request(pool_id, yield_source, str(asset_amount), staking_period_hrs, "completed")
      self.assert_stake_info(pool_id, yield_source, token, e_amount, staking_period_hrs)


  def assert_unstake(
      self,
      pool_id: int,
      yield_source: str,
      token: Token,
      z_amount: int,
  ):
      tevmc = self.bbf.tevmc
      evm_transaction_signer = self.bbf.evm_transaction_signer

      mock_yield_source_adaptor_balance = token.e_balance(self.bbf.mock_yield_source_adaptor.address)
      stake_local_balance = token.z_balance(self.bbf.stake_local_account)
      e_bridge_balance = self.bbf.bridge_e_contract.functions.tokenBalances(
          token.contract.address
      ).call()
      z_supply = token.z_supply()
      e_amount = token.z_to_e_amount(z_amount)
      # self.cleos.logger.info("Set allowance to bridge e...")
      # receipt = evm_transaction_signer.transact(
      #     token.contract,
      #     "approve",
      #     self.bbf.mock_yield_source_adaptor.address,
      #     self.bbf.bridge_e_contract.address,
      #     e_amount,
      # )
      # assert receipt

      self.cleos.logger.info("Trigger Unstake...")
      receipt = evm_transaction_signer.transact(
          self.bbf.mock_yield_source_adaptor,
          "triggerUnstake",
          self.bbf.e_accounts[0].address,
          yield_source,
          pool_id,
          token.contract.address,
          e_amount,
          self.bbf.bridge_e_contract.address,
      )
      assert receipt

      mock_yield_source_adaptor_balance -= e_amount
      e_bridge_balance += e_amount
      stake_local_balance.amount += z_amount
      z_supply.amount += z_amount
      assert token.e_balance(self.bbf.mock_yield_source_adaptor.address) == mock_yield_source_adaptor_balance
      assert token.e_balance(self.bbf.bridge_e_contract.address) == e_bridge_balance
      assert (
          self.bbf.bridge_e_contract.functions.tokenBalances(token.contract.address).call()
          == e_bridge_balance
      )
      assert token.z_balance(self.bbf.stake_local_account) == stake_local_balance
      assert token.z_supply() == z_supply
      self.assert_stats(token, z_supply)
      self.assert_unstake_info(pool_id, token.to_asset(z_amount))


  def assert_stats(self, token: Token, expected_supply: Asset):
      stats = token.z_stats()
      assert stats["supply"] == str(expected_supply)
      assert stats["max_supply"] == str(token.to_asset(4611686018427387903))
      assert stats["issuer"] == self.bbf.bridge_z_account


  def assert_bridge_request(
      self,
      fromAccount: str,
      to: LocalAccount,
      quantity: Asset,
      state: str,
  ):
      actual = self.bbf.zero_bridge.get_last_bridge_request()
      
      assert actual is not None
      assert actual["from"] == str(fromAccount)
      assert actual["to"] == to.address[2:].lower()
      assert actual["quantity"] == str(quantity)
      assert actual["state"] == state

  def assert_stake_request(
      self,
      pool_id: int,
      yield_source: str,
      quantity: Asset,
      staking_period_hrs: int,
      state: str,
  ):
      actual = self.bbf.zero_bridge.get_last_stake_request()
      
      assert actual is not None
      assert actual["pool_id"] == pool_id
      assert actual["yield_source"] == yield_source
      assert actual["quantity"] == str(quantity)
      assert actual["staking_period_hrs"] == staking_period_hrs
      assert actual["state"] == state


  def assert_stake_info(
      self,
      pool_id: int,
      yield_source: str,
      token: Token,
      amount: int,
      staking_period_hrs: int
  ):
      actual = self.bbf.mock_yield_source_adaptor.functions.lastStakeInfo().call()
      self.cleos.logger.info(f'In assert_stake_info, results: {json.dumps(actual, indent=4)}')
      assert actual[0] == pool_id
      assert actual[1] == yield_source
      assert actual[2] == token.contract.address
      assert actual[3] == amount
      assert actual[4] == staking_period_hrs

  def assert_unstake_info(
      self,
      pool_id: int,
      amount: Asset
  ):
      results = self.cleos.get_table(
          self.bbf.stake_local_account, self.bbf.stake_local_account, "unstakeinfo"
      )
      self.cleos.logger.info(f'In assert_unstake_info, results: {json.dumps(results, indent=4)}')
      assert len(results) == 1
      actual = results[0]
      assert actual["from"] == self.bbf.bridge_z_account
      assert actual["amount"] == str(amount)
      assert actual["memo"] == f"pool id: {pool_id}"


  def assert_zero_bridge_config(
      self,
      bridge_e_address: str,
      token_registry_address: str,
      stake_local_account: str,
      refund_delay_period_mins: int,
      batch_size: int,
      version: str,
      admin: str,
      active: bool
  ):
      actual = self.bbf.zero_bridge.get_config()
      self.cleos.logger.info(f'In zero bridge config: {json.dumps(actual, indent=4)}')
      self.cleos.logger.info(f'bridge_e_address: {bridge_e_address}, token_registry_address: {token_registry_address}, stake_local_account: {stake_local_account}, version: {version}, admin: {admin}')
      assert actual is not None
      assert actual["evm_bridge_address"] == bridge_e_address[2:].lower()
      assert actual["evm_token_registry_address"] == token_registry_address[2:].lower()
      assert actual["stake_local_contract"] == stake_local_account
      assert actual["version"] == version
      assert actual["admin"] == admin
      


  def set_fee(self, fee: int):
      receipt = self.bbf.evm_transaction_signer.transact(
              self.bbf.bridge_e_contract,
              "setFee",
              self.cleos.evm_default_account.address,
              fee
              )
      assert receipt