from tevmc.cleos_evm import CLEOSEVM
from leap.protocol import Asset

class ZeroBridge:
  def __init__(self, bbf):
    self.bbf = bbf
    self.cleos: CLEOSEVM = bbf.cleos


  def init(self, bridge_e_address: str, token_registry_address: str, stake_local_account: str, version: str, admin: str) -> dict:
    return self.__action(
        "init",
        self.bbf.bridge_z_account,
        [
            bridge_e_address[2:],
            token_registry_address[2:],
            stake_local_account,
            version,
            admin
        ]
    )

  def bridge_z_to_e(self, z_user: str, e_user: str, asset_amount: str | Asset, actor: str = None) -> dict:
    actor = z_user if actor is None else actor
    return self.__action(
        "bridgeztoevm",
        actor,
        [
          z_user,
          str(asset_amount),
          e_user[2:],
        ]
    )
  
  def stake(self, pool_id: int, yield_source: str, asset_amount: str | Asset, staking_period_hrs: int, actor: str = None) -> dict:
    actor = self.bbf.stake_local_account if actor is None else actor
    return self.__action(
        "stake",
        actor,
        [
          pool_id,
          yield_source,
          str(asset_amount),
          staking_period_hrs
        ]
    )
  
  def __action(self, action: str, actor: str, data: list) -> dict:
    return self.cleos.push_action(
        self.bbf.bridge_z_account,
        action,
        data,
        actor,
        self.cleos.private_keys[actor]
    )