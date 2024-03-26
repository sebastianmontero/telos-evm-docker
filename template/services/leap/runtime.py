#!/usr/bin/env python3

import time

from pathlib import Path
from typing import Literal, NoReturn
from urllib.parse import urlparse

import requests

from pydantic import BaseModel, Field
from dockerstack.errors import DockerServiceError
from dockerstack.typing import ServiceConfig
from dockerstack.service import DockerService

from leap.cleos import CLEOS

from tevmc.cleos_evm import CLEOSEVM


class IniDict(BaseModel):
    plugins: list[str]
    peers: list[str]
    subst: str | dict[str, str] | None = None

    agent_name: str = 'Telos EVM Controller node'
    wasm_runtime: str = 'eos-vm-jit'
    vm_oc_compile_threads: int = 4
    vm_oc_enable: bool = True

    chain_state_size: int = 65536
    account_queries: bool = True
    abi_serializer_max_time: int = 2_000_000

    allow_origin: str = '*'
    http_verbose_error: bool = True
    contracts_console: bool = True
    http_validate_host: bool = False
    p2p_max_nodes: int = 1

    trace_history: bool = True
    chain_history: bool = True
    history_debug_mode: bool = True
    history_dir: str = 'state-history'

    sync_fetch_span: int = 1600

    max_clients: int = 250
    cleanup_period: int = 30
    allowed_connection: str = 'any'
    http_max_response_time: int = 100000
    http_max_body_size: int = 100000000

    enable_stale_production: bool = True

    sig_provider: str | None = None

    disable_subjective_billing: bool = True
    max_transaction_time: int = 500


class LeapDict(ServiceConfig):
    chain_id: str
    chain_type: Literal['local'] | Literal['testnet'] | Literal['mainnet']
    nodeos_bin: str = 'nodeos'
    snapshot: int | str | None = None
    genesis: str | None = None
    produce: bool | None = None
    space_monitor: bool = True
    initialize: bool = True
    eosio_evm: str = Field('eosio.evm/receiptless', alias='eosio.evm')
    nodeos_params: list[str] = []
    ini: IniDict


class LeapService(DockerService):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.chain_type = self.config.chain_type

        self.is_relaunch: bool = False
        self.plugins: list[str] = []
        self.producer_key: str

        self.data_dir: Path = Path(self.mounts['data']['Source'])
        self.nodeos_wd = Path(self.mounts['~']['Target'])

        self.is_relaunch = (self.data_dir / 'blocks/blocks.log').is_file()

        self.remote_endpoint: str | None = None
        if self.chain_type == 'testnet':
            self.remote_endpoint = 'https://testnet.telos.net'

        elif self.chain_type == 'mainnet':
            self.remote_endpoint = 'https://mainnet.telos.net'

        self.history_endpoint: str = f'ws://{self.ip}:{self.ports["history"]}'

        # require rpc and translator configs to be present to point
        # cleos evm to right endpoint + get evm chain_id
        rpc_conf = self.stack._get_raw_service_config('rpc')
        self.translator_conf = self.stack._get_raw_service_config('translator')

        self.cleos_url = f'http://{self.ip}:{self.ports["api"]}'
        self.cleos_evm_url = f'http://{self.ip}:{rpc_conf["ports"]["api"]}/evm'

        # setup cleos wrapper
        cleos = CLEOSEVM(
            self.cleos_url,
            logger=self.logger,
            evm_url=self.cleos_evm_url,
            chain_id=self.translator_conf['chain_id'])

        self.cleos = cleos

        self.config: LeapDict

        self.template_whitelist = [
            'config.ini', 'local.config.ini'
        ]

        # dynamic snapshot conf
        self.snapshot: str | None = None
        if self.config.snapshot is not None:
            if not isinstance(self.config.snapshot, str):
                raise AttributeError('Expected leap.snapshot to be a str')

            snap_url = urlparse(self.config.snapshot)

            # if str does not contain a url schema assume snapshot
            # is a path relative to home dir
            _snap = self.config.snapshot

            if snap_url.scheme in ('http', 'https'):
                # if snap conf is url means it was downloaded to
                # home dir / snap_id by dockerstack www_files
                # so find snap_id in field
                snap_matches = [
                    k for k in self.www_files.keys()
                    if 'snap' in k and k.endswith('.bin')
                ]

                if len(snap_matches) > 1:
                    raise AttributeError(
                        'Leap runtime cant figure out snapshot id due to'
                        f'conflicting www_files names: {snap_matches}')

                if len(snap_matches) == 0:
                    raise AttributeError(
                        f'Didn\'t find any matching snap files! {list(self.www_files.keys())}')

                _snap = snap_matches[0]

            self.snapshot = str(self.nodeos_wd / _snap)

        @self.phrase_handler(
            'Done storing initial state on startup',
            'correct startup when no data is found on disk'
        )
        def _fresh_launch() -> None:
            if self.is_relaunch:
                raise DockerServiceError('Found fresh leap launch phrase but is_relaunch == True')

        @self.phrase_handler(
            'Produced block',
            'correct startup when node is a producer'
        )
        def _producing() -> None:
            if self.chain_type != 'local':
                raise DockerServiceError(f'Node is producing blocks but chain_type == {self.chain_type}')

        @self.phrase_handler(
            'Received block',
            'correct startup when node is syncing'
        )
        def _receiving() -> None:
            if self.chain_type == 'local':
                raise DockerServiceError('Node is receiving blocks but chain_type == local')

        @self.phrase_handler(
            'database dirty flag',
            'nodeos state database is dirty, can\'t start without repair'
        )
        def _dirty_db() -> None:
            raise DockerServiceError('Leap database dirty!')

        @self.phrase_handler(
            'Address already in use',
            'one of the ports selected is already in use on this host'
        )
        def _addr_in_use() -> None:
            raise DockerServiceError('Leap port in use!')

    def configure(self):
        cleos = self.cleos

        if not self.config.ini.sig_provider and self.config.produce:
            self.config.ini.sig_provider = 'EOS5GnobZ231eekYUJHGTcmy2qve1K23r5jSFQbMfwWTtPB7mFZ1L=KEY:5Jr65kdYmn33C3UabzhmWDm2PuqbRfPuDStts3ZFNSBLM7TqaiL'
            self.producer_key = self.config.ini.sig_provider.split('=KEY:')[-1]
            cleos.import_key('eosio', self.producer_key)

        contracts_dir = self.service_wd / 'contracts'

        cleos.load_abi_file('eosio', contracts_dir / 'eosio.system/eosio.system.abi')
        cleos.load_abi_file('eosio.evm', contracts_dir / 'eosio.evm/regular/regular.abi')
        cleos.load_abi_file('eosio.token', contracts_dir / 'eosio.token/eosio.token.abi')

        self.config_subst.update(self.config.ini.model_dump())

        self.config_subst.update({
            'http_addr': f'0.0.0.0:{self.ports["api"]}',
            'p2p_addr': f'0.0.0.0:{self.ports["p2p"]}',
            'history_endpoint': f'0.0.0.0:{self.ports["history"]}'
        })

        # normalize bools
        norm_subst = {}
        for key, val in self.config_subst.items():
            if isinstance(val, bool):
                norm_subst[key] = str(val).lower()
            else:
                norm_subst[key] = val

        ini_conf = self.templates[
            'config.ini'].substitute(**norm_subst) + '\n'

        if self.chain_type == 'local':
            ini_conf += self.templates[
                'local.config.ini'].substitute(**norm_subst) + '\n'

        for plugin in norm_subst['plugins']:
            ini_conf += f'plugin = {plugin}' + '\n'
            self.plugins.append(plugin)

        if 'subst' in norm_subst:
            ini_conf += f'plugin = eosio::subst_plugin\n'
            ini_conf += '\n'
            sinfo = norm_subst['subst']
            if isinstance(sinfo, str):
                ini_conf += f'subst-manifest = {sinfo}'

            elif isinstance(sinfo, dict):
                for skey, val in sinfo.items():
                    subst_path = Path(val)
                    if not subst_path.is_absolute():
                        subst_path = self.nodeos_wd / val
                    ini_conf += f'subst-by-name = {skey}:{subst_path}'

        ini_conf += '\n'

        for peer in norm_subst['peers']:
            ini_conf += f'p2p-peer-address = {peer}\n'

        with open(self.service_wd / 'config.ini', 'w+') as target_file:
            target_file.write(ini_conf)

        # remove templates that are related to nodeos.ini generation
        del self.templates['config.ini']
        del self.templates['local.config.ini']

        super().configure()

    def prepare(self):
        # generate nodeos command
        nodeos_cmd = [self.config.nodeos_bin]

        if 'eosio::state_history_plugin' in self.plugins:
            nodeos_cmd += ['--disable-replay-opts']

        if (not self.is_relaunch or
            '--replay-blockchain' in self.config.nodeos_params):
            if self.config.snapshot:
                nodeos_cmd += [f'--snapshot={self.snapshot}']

            elif self.config.genesis:
                nodeos_cmd += [
                    f'--genesis-json={self.nodeos_wd}/genesis/{self.config.genesis}.json'
                ]

        if not self.config.space_monitor:
            nodeos_cmd += ['--resource-monitor-not-shutdown-on-threshold-exceeded']

        if self.config.produce:
            nodeos_cmd += ['-p', 'eosio']

        self.logger.stack_info(f'launching nodeos with cmd: \"{" ".join(nodeos_cmd)}\"')

        self.command = nodeos_cmd

    def start(self):
        cleos = self.cleos

        if self.chain_type == 'local' and self.config.initialize:
            output = ''
            for msg in self.stream_logs(lines=200, timeout=60*10, from_latest=True):
                output += msg
                if 'Produced' in msg:
                    break

            # await for nodeos to produce a block
            cleos.wait_blocks(4)

            self.is_fresh = (
                'No existing chain state or fork database. '
                'Initializing fresh blockchain state and resetting fork database.' in output
            )

            if self.is_fresh:
                contracts_dir = self.service_wd / 'contracts'
                cleos.boot_sequence(
                    contracts=contracts_dir,
                    remote_node=CLEOS('https://testnet.telos.net'),
                    extras=['telos'])

                cleos.deploy_evm(contracts_dir / self.config.eosio_evm)


        else:
            if '--replay-blockchain' not in self.config.nodeos_params:
                for msg in self.stream_logs(timeout=60*10, from_latest=True):
                    if 'Received' in msg:
                        break

        if self.config.initialize:
            # wait until nodeos apis are up
            for _ in range(60):
                try:
                    self.nodeos_init_info = cleos.get_info()
                    current_chain_id = self.nodeos_init_info['chain_id']
                    config_chain_id = self.config.chain_id

                    if config_chain_id != current_chain_id:
                        raise ValueError(
                            f'chain id returned ({current_chain_id}) '
                            f'from nodeos differs from one on config ({config_chain_id})')

                    break

                except requests.exceptions.ConnectionError:
                    self.logger.warning('connection error trying to get chain info...')
                    time.sleep(1)

            genesis_block = int(self.translator_conf['start_block']) - 1
            cleos.wait_block(genesis_block)

    @property
    def status(self) -> str:
        if self.cleos and isinstance(self.cleos, CLEOSEVM):
            try:
                info = self.cleos.get_info()
                assert 'chain_id' in info
                assert info['chain_id'] == self.config.chain_id
                return 'healthy'

            except:
                ...


        return 'unhealthy'

    def remote_block_num(self):
        if self.chain_type == 'local':
            raise DockerServiceError(f'Can\'t get remote head block on local chain!')

        resp = requests.get(f'{self.remote_endpoint}/v1/chain/get_info').json()
        return int(resp['head_block_num'])

    def block_num(self) -> int:
        return int(self.cleos.get_info()['head_block_num'])

    def measure_speed(self, time_interval: int) -> float:
        time_interval = int(time_interval)

        start_block = self.block_num()
        self.logger.info(
            f'measuring speed, time interval: {time_interval}, latest block: {start_block}')

        for i in range(time_interval):
            self.logger.info(i+1)
            time.sleep(1)

        end_block = self.block_num()

        blocks_synced = end_block - start_block
        speed = blocks_synced / time_interval

        self.logger.info(
            f'end speed measure, end block: {end_block}, speed: {speed:.02f}')

        return speed

    def stop(self):
        ec, _ = self.run_process(['pkill', '-f', 'nodeos'])
        assert ec == 0

        for msg in self.stream_logs(from_latest=True, lines=15):
            if 'nodeos successfully exiting' in msg:
                break

        super().stop()
