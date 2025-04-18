from tevmc.cleos_evm import CLEOSEVM
from leap.protocol import Asset


class ZeroBridge:
    def __init__(self, bbf):
        self.bbf = bbf
        self.cleos: CLEOSEVM = bbf.cleos
        self.logger = bbf.cleos.logger
        self.call_counter = 0

    def set_config(
        self,
        bridge_e_address: str,
        token_registry_address: str,
        stake_local_account: str,
        refund_delay_period_mins: int,
        batch_size: int,
        version: str,
        admin: str,
        active: bool = True,
        actor: str = None,
    ) -> dict:
        actor = self.bbf.bridge_z_account if actor is None else actor
        self.logger.info(
            f"Set config: bridge_e_address: {bridge_e_address}, token_registry_address: {token_registry_address}, stake_local_account: {stake_local_account}, refund_delay_period_mins: {refund_delay_period_mins}, batch_size: {batch_size}, version: {version}, admin: {admin}, active: {active}, actor: {actor}"
        )
        if bridge_e_address.startswith('0x'):
            bridge_e_address = bridge_e_address[2:]
        if token_registry_address.startswith('0x'):
            token_registry_address = token_registry_address[2:]
        return self.__action(
            "setconfig",
            actor,
            [
                bridge_e_address,
                token_registry_address,
                stake_local_account,
                refund_delay_period_mins,
                batch_size,
                version,
                admin,
                active,
            ],
        )
    
    def update_config(
        self,
        bridge_e_address: str | None = None,
        token_registry_address: str | None = None,
        stake_local_account: str | None = None,
        refund_delay_period_mins: int | None = None,
        batch_size: int | None = None,
        version: str | None = None,
        admin: str | None = None,
        active: bool | None = None,
        actor: str | None = None,
    ) -> dict:
        config = self.get_config()
        if not config:
            raise Exception("Config must already exist to update it")
        
        self.logger.info(f"Updating config: {config}")
        return self.set_config(
                bridge_e_address or config["evm_bridge_address"],
                token_registry_address or config["evm_token_registry_address"],
                stake_local_account or config["stake_local_contract"],
                refund_delay_period_mins or int(config["refund_delay_period"]["_count"] / 60_000_000),
                batch_size or config["batch_size"],
                version or config["version"],
                admin or config["admin"],
                active if active is not None else config["active"],
                actor
        )

    def bridge_z_to_e(
        self, z_user: str, e_user: str, asset_amount: str | Asset, actor: str = None
    ) -> dict:
        actor = z_user if actor is None else actor
        return self.__action(
            "bridgeztoevm",
            actor,
            [
                z_user,
                str(asset_amount),
                e_user[2:],
            ],
        )

    def process_e_to_z_reqs(self) -> dict:
        # TODO: ADD equivalent to open permissions account
        return self.__action("prevmtozreqs", "eosio", [self.call_counter])

    def notify_processed_e_to_z_reqs(self) -> dict:
        # TODO: ADD equivalent to open permissions account
        return self.__action("ntpretozreqs", "eosio", [self.call_counter])

    def remove_processed_e_to_z_reqs(self) -> dict:
        # TODO: ADD equivalent to open permissions account
        return self.__action("rmpretozreqs", "eosio", [self.call_counter])

    def stake(
        self,
        pool_id: int,
        yield_source: str,
        asset_amount: str | Asset,
        staking_period_hrs: int,
        actor: str = None,
    ) -> dict:
        actor = self.bbf.stake_local_account if actor is None else actor
        return self.__action(
            "stake",
            actor,
            [pool_id, yield_source, str(asset_amount), staking_period_hrs],
        )

    def evmnotify(self, sender: str, msg: str, actor: bytes = None) -> dict:
        actor = self.bbf.message_evm_account if actor is None else actor
        return self.__action("evmnotify", actor, [sender[2:], msg])

    def refund(self, bridge_request_id: int) -> dict:
        return self.__action("refund", self.bbf.bridge_z_account, [bridge_request_id])

    def exec_refunds(self, call_counter: int) -> dict:
        return self.__action("execrefunds", self.bbf.bridge_z_account, [call_counter])

    def lapse_bridge_request(self, bridge_request_id: int) -> dict:
        return self.__action(
            "lpsebrdgereq", self.bbf.bridge_z_account, [bridge_request_id]
        )

    def reset(
        self, limit: int, to_delete: list[str], call_counter: int, actor: str = None
    ) -> dict:
        actor = self.bbf.bridge_z_account if actor is None else actor
        return self.__action("reset", actor, [limit, to_delete, call_counter])

    def get_last_processed_bridge_e_to_z_request(self) -> dict | None:
        results = self.__table(
            "procetozreqs",
            # limit=1,
            reverse=True,
        )
        return results[0] if len(results) > 0 else None

    def get_processed_bridge_e_to_z_request(self, call_id: int) -> dict | None:
        results = self.__table(
            "procetozreqs", key_type="i64", index="1", lower_bound=call_id, upper_bound=call_id
        )
        return results[0] if len(results) > 0 else None
    
    def get_processed_bridge_e_to_z_requests(self) -> list[dict]:
        results = self.__table(
            "procetozreqs",
            limit=1000
        )
        return results
    
    def get_processed_bridge_e_to_z_request_count(self) -> int:
        results = self.get_processed_bridge_e_to_z_requests()
        return len(results)

    def get_processed_bridge_e_to_z_requests_map(self) -> dict:
        results = self.get_processed_bridge_e_to_z_requests()
        return {r["call_id"]: r for r in results}

    def get_last_bridge_z_to_e_request(self) -> dict | None:
        results = self.__table(
            "bridgereqs",
            # limit=1,
            reverse=True,
        )
        return results[0] if len(results) > 0 else None

    def get_bridge_z_to_e_request(self, bridge_request_id: int) -> dict | None:
        results = self.__table(
            "bridgereqs",
            key_type="i64",
            index="1",
            lower_bound=bridge_request_id,
            upper_bound=bridge_request_id,
        )
        return results[0] if len(results) > 0 else None

    def get_last_stake_request(self) -> dict | None:
        results = self.__table(
            "stakereqs",
            # limit=1,
            reverse=True,
        )
        return results[0] if len(results) > 0 else None

    def get_stake_request(self, stake_request_id: int) -> dict | None:
        results = self.__table(
            "stakereqs",
            key_type="i64",
            index="1",
            lower_bound=stake_request_id,
            upper_bound=stake_request_id,
        )
        return results[0] if len(results) > 0 else None

    def get_bridge_z_to_e_request_count(self) -> dict | None:
        results = self.__table("bridgereqs")
        return len(results)

    def get_stake_request_count(self) -> dict | None:
        results = self.__table("stakereqs")
        return len(results)

    def get_config(self) -> dict | None:
        results = self.__table("bridgeconfig")
        return results[0] if len(results) > 0 else None

    def __action(self, action: str, actor: str, data: list) -> dict:
        self.call_counter += 1
        return self.cleos.push_action(
            self.bbf.bridge_z_account,
            action,
            data,
            actor,
            self.cleos.private_keys[actor],
        )

    def __table(self, table: str, **kwargs) -> list[dict]:
        return self.cleos.get_table(
            self.bbf.bridge_z_account, self.bbf.bridge_z_account, table, **kwargs
        )
