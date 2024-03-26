#!/usr/bin/env python3

from dockerstack.typing import ServiceConfig
from dockerstack.service import DockerService
from dockerstack.utils import flatten
from pydantic import BaseModel

from tevmc.utils import jsonize


class PerfDict(BaseModel):
    stall_counter: int = 5
    reader_workers: int = 4
    evm_workers: int = 4
    elastic_dump_size: int = 1


class TranslatorDict(ServiceConfig):
    chain_name: str
    chain_id: int
    start_block: int
    block_delta: int

    prev_hash: str = ''
    validate_hash: str = ''
    end_block: int = -1
    irreversible_only: bool = False
    perf: PerfDict = PerfDict()
    log_level: str = 'debug'
    reader_log_level: str = 'warning'
    ws_host: str = '127.0.0.1'


class TranslatorService(DockerService):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config: TranslatorDict

        self.template_whitelist = [
            'config.json'
        ]

    def configure(self):
        perf_subst = flatten('perf', self.config.perf.model_dump())
        self.config_subst.update(flatten('translator', perf_subst))

        es_service = self.stack.get_service('elastic')
        nodeos_service = self.stack.get_service('leap')

        remote = nodeos_service.cleos_url
        if nodeos_service.remote_endpoint:
            remote = nodeos_service.remote_endpoint

        self.config_subst.update({
            'nodeos_http_endpoint': nodeos_service.cleos_url,
            'nodeos_remote_endpoint': remote,
            'nodeos_ws_endpoint': nodeos_service.history_endpoint,

            'elastic_endpoint': es_service.node_url
        })

        self.config_subst = jsonize(self.config_subst)

        super().configure()

    @property
    def status(self) -> str:
        try:
            for msg in self.stream_logs(from_latest=True, timeout=5):
                if 'drained' in msg:
                    return 'healthy'

            return 'unhealthy'

        except ValueError:
            return 'unhealthy'
