#!/usr/bin/env python3

import requests

from web3 import HTTPProvider, Web3
from dockerstack.typing import ServiceConfig
from dockerstack.service import DockerService

from tevmc.utils import jsonize


class RpcDict(ServiceConfig):
    debug: bool = False
    host: str = '0.0.0.0'
    ws_host: str = '0.0.0.0'

    nodeos_write: str | None = None
    nodeos_read: str | None = None
    signer_account: str = 'rpc.evm'
    signer_permission: str = 'rpc'
    signer_key: str = '5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL'
    contracts: dict[str, str] = {'main': 'eosio.evm'}
    index_version: str = 'v1.5'


class RpcService(DockerService):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config: RpcDict

        self.api_endpoint = f'http://{self.ip}:{self.ports["api"]}/evm'

        self.w3 = Web3(HTTPProvider(self.api_endpoint))

        self.template_whitelist = [
            'config.json'
        ]

    def configure(self):
        es_service = self.stack.get_service('elastic')
        redis_service = self.stack.get_service('redis')
        nodeos_service = self.stack.get_service('leap')
        translator_service = self.stack.get_service('translator')

        self.config_subst.update({
            'translator_chain_id': translator_service.config.chain_id,
            'translator_block_delta': translator_service.config.block_delta,
            'translator_ws_host': translator_service.ip,
            'translator_ports_broadcast': translator_service.ports['broadcast'],
            'rpc_ws_uri': f'ws://{translator_service.ip}:7300/evm',

            'rpc_nodeos_read': self.config.nodeos_read if self.config.nodeos_read else nodeos_service.cleos_url,
            'rpc_nodeos_write': self.config.nodeos_write if self.config.nodeos_write else nodeos_service.cleos_url,

            'redis_host': redis_service.ip,
            'redis_port': redis_service.ports['bind'],

            'elastic_node': es_service.node_url,
            'elastic_prefix': translator_service.config.chain_name,

            'nodeos_chain_id': nodeos_service.config.chain_id,

        })

        self.config_subst = jsonize(self.config_subst)

        super().configure()

    @property
    def status(self) -> str:
        return 'healthy'
        # try:
        #     resp = requests.get(self.api_endpoint)
        #     breakpoint()
        #     resp.raise_for_status()

        #     assert 'a few seconds behind' in resp.text

        #     assert self.w3.is_connected()

        #     return 'healthy'

        # except requests.RequestException:
        #     return 'unhealthy'

        # except AssertionError:
        #     return 'unhealthy'
