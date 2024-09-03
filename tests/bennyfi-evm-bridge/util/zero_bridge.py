from tevmc.cleos_evm import CLEOSEVM
from leap.protocol import Asset

class ZeroBridge:
  def __init__(self, bbf):
    self.bbf = bbf
    self.cleos: CLEOSEVM = bbf.cleos


  def set_config(self, bridge_e_address: str, token_registry_address: str, stake_local_account: str, refund_delay_period_mins: int, batch_size: int, version: str, admin: str, active: bool = True, actor: str = None) -> dict:
    actor = self.bbf.bridge_z_account if actor is None else actor
    return self.__action(
        "setconfig",
        actor,
        [
            bridge_e_address[2:],
            token_registry_address[2:],
            stake_local_account,
            refund_delay_period_mins,
            batch_size,
            version,
            admin,
            active
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
  
  def evmnotify(self, sender: str, msg: str,  actor: bytes = None) -> dict:
    actor = self.bbf.message_evm_account if actor is None else actor
    return self.__action(
        "evmnotify",
        actor,
        [
          sender[2:],
          msg
        ]
    )
  
  def refund(self, bridge_request_id: int) -> dict:
    return self.__action(
        "refund",
        self.bbf.bridge_z_account,
        [
          bridge_request_id
        ]
    )

  def exec_refunds(self, call_counter: int) -> dict:
    return self.__action(
        "execrefunds",
        self.bbf.bridge_z_account,
        [
          call_counter
        ]
    )
  
  def lapse_bridge_request(self, bridge_request_id: int) -> dict:
    return self.__action(
        "lpsebrdgereq",
        self.bbf.bridge_z_account,
        [
          bridge_request_id
        ]
    )
  
  def reset(self, limit: int, to_delete: list[str], call_counter: int, actor: str = None) -> dict:
    actor = self.bbf.bridge_z_account if actor is None else actor
    return self.__action(
        "reset",
        actor,
        [
          limit,
          to_delete,
          call_counter
        ]
    )
  
  def get_last_bridge_request(self) -> dict | None:
    results = self.__table(
      "bridgereqs",
      # limit=1,
      reverse=True
    )
    return results[0] if len(results) > 0 else None
  
  def get_bridge_request(self, bridge_request_id: int) -> dict | None:
    results = self.__table(
      "bridgereqs",
      key_type="i64",
      index="1",
      lower_bound=bridge_request_id,
      upper_bound=bridge_request_id
    )
    return results[0] if len(results) > 0 else None
  
  def get_last_stake_request(self) -> dict | None:
    results = self.__table(
      "stakereqs",
      # limit=1,
      reverse=True)
    return results[0] if len(results) > 0 else None
  
  def get_stake_request(self, stake_request_id: int) -> dict | None:
    results = self.__table(
      "stakereqs",
      key_type="i64",
      index="1",
      lower_bound=stake_request_id,
      upper_bound=stake_request_id
      )
    return results[0] if len(results) > 0 else None
  
  def get_bridge_request_count(self) -> dict | None:
    results = self.__table("bridgereqs")
    return len(results)
  
  
  def get_stake_request_count(self) -> dict | None:
    results = self.__table("stakereqs")
    return len(results)
  
  def get_config(self) -> dict | None:
    results = self.__table("bridgeconfig")
    return results[0] if len(results) > 0 else None
  
  def __action(self, action: str, actor: str, data: list) -> dict:
    return self.cleos.push_action(
        self.bbf.bridge_z_account,
        action,
        data,
        actor,
        self.cleos.private_keys[actor]
    )
  
  def __table(self, table: str, **kwargs) -> list[dict]:
    return self.cleos.get_table(
          self.bbf.bridge_z_account, self.bbf.bridge_z_account, table, **kwargs
      )