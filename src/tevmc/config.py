#!/usr/bin/env python3

import json
import shutil
import logging

from copy import deepcopy
from pathlib import Path
from collections import OrderedDict
from urllib.parse import urlparse

from deepmerge import always_merger

from tevmc.utils import find_closest_snapshot_url


DEFAULT_BASE_CONFIG = {
    'services': ['rpc'],
    'stack': [
        {
            'name': 'elasticsearch',
            'base': 'https://raw.githubusercontent.com/guilledk/dockerstack/master/library/elastic.json'
        },
        {
            'name': 'kibana',
            'base': 'https://raw.githubusercontent.com/guilledk/dockerstack/master/library/kibana.json',

            'host': '127.0.0.1'
        },
        {
            'name': 'redis',
            'base': 'https://raw.githubusercontent.com/guilledk/dockerstack/master/library/redis.json',

            'host': '127.0.0.1'
        },
        {
            'name': 'leap',
            'aliases': ['nodeos'],
            'tag': 'tevmc:leap',
            'docker_file': 'Dockerfile',
            'service_path': 'leap',
            'mounts': [
                {
                    'name': '~',
                    'source': 'services/leap',
                    'target': '/root/.local/share/eosio/nodeos/config',
                    'mtype': 'bind'
                },
                {
                    'name': 'data',
                    'source': 'leap_data',
                    'target': '/root/.local/share/eosio/nodeos/data',
                    'mtype': 'bind'
                }
            ],
            'ports': {
                'api': 8888,
                'p2p': 9876,
                'history': 29999
            },
            'show_build': True,
            'startup_logs_kwargs': {'lines': 0, 'from_latest': True, 'timeout': 60},
        },
        {
            'name': 'translator',
            'tag': 'tevmc:translator',
            'docker_file': 'Dockerfile',
            'ports': {
                'broadcast': 7300
            },
            'requires': ['elasticsearch', 'leap'],
            'startup_logs_kwargs': {'lines': 0, 'from_latest': True, 'timeout': 600},
            'startup_phrase': 'drained',
            'stop_sequence': ['SIGTERM', 'SIGKILL'],
        },
        {
            'name': 'rpc',
            'tag': 'tevmc:rpc',
            'docker_file': 'Dockerfile',
            'ports': {
                'api': 7000,
                'ws': 7400
            },
            'requires': ['translator', 'redis'],
            'startup_phrase': 'Starting teloscan-evm-rpc'
        }
    ]
}

DEFAULT_LOCAL_CONFIG = {
    'name': 'telos-evm-local-node',
    'services': ['rpc'],
    'stack': [
        {
            'name': 'leap',

            'chain_id': 'c4c5fcc7b6e5e7484eb6b609e755050ebba977c4c291a63aab42d94c0fb8c2cf',
            'chain_type': 'local',
            'genesis': 'local',
            'produce': True,

            'ini': {
                'plugins': [
                    'eosio::http_plugin',
                    'eosio::chain_plugin',
                    'eosio::chain_api_plugin',
                    'eosio::net_plugin',
                    'eosio::producer_plugin',
                    'eosio::producer_api_plugin',
                    'eosio::state_history_plugin'
                ],
                'peers': [],
                'subst': {
                    'eosio.evm': 'contracts/eosio.evm/regular/regular.wasm'
                }
            }
        },
        {
            'name': 'translator',
            'chain_name': 'telos-local',
            'chain_id': 41,
            'start_block': 2,
            'block_delta': 0
        },
        {
            'name': 'rpc',
        }
    ]
}


DEFAULT_TESTNET_CONFIG = {
    'name': 'telos-evm-testnet-node',
    'services': ['rpc'],
    'stack': [
        {
            'name': 'leap',

            'snapshot': 'http://storage.telos.net/test-resources/telos-testnet-snapshot-evm-deploy.bin',

            'chain_id': '1eaa0824707c8c16bd25145493bf062aecddfeb56c736f6ba6397f3195f33c9f',
            'chain_type': 'testnet',

            'ini': {
                'plugins': [
                    'eosio::http_plugin',
                    'eosio::chain_api_plugin',
                    'eosio::state_history_plugin'
                ],
                'peers': [
                    'testnet2.telos.eosusa.news:59877',
                    'node1.testnet.telosglobal.io:9876',
                    'basho.eos.barcelona:9899',
                    'sslapi.teloscentral.com:9875',
                    '145.239.133.188:5566',
                    'testnet.telos.eclipse24.io:6789',
                    'p2p.telos.testnet.detroitledger.tech:30001',
                    'basho-p2p.telosuk.io:19876',
                    'telos-testnet.atticlab.net:7876',
                    'testnet.eossweden.eu:8022',
                    'testnet.telos.cryptosuvi.io:2223',
                    'p2p-test.tlos.goodblock.io:9876',
                    'telosapi.eosmetal.io:59877',
                    '207.148.6.75:9877',
                    'telosgermany-testnet.genereos.io:9876',
                    '176.9.86.214:9877',
                    'peer1-telos-testnet.eosphere.io:9876',
                    'testnet.telos.africa:9875',
                    'p2p.testnet.telosgreen.com:9876',
                    'testnet2p2p.telosarabia.net:9876',
                    '157.230.29.117:9876',
                    'test.telos.kitchen:9876',
                    'prod.testnet.bp.teleology.world:9876',
                    'telos-testnet.eoscafeblock.com:9879',
                    'p2p.basho.telos.dutcheos.io:7654',
                    'testnet-b.telos-21zephyr.com:9876',
                    'p2p.testnet.telosunlimited.io:9876',
                    'peer.tlostest.alohaeos.com:9876',
                    '52.175.222.202:9877',
                    'testnet2.telos.eosindex.io:9876',
                    'basho.sofos.network:9876',
                    '85.152.18.129:39876',
                    'telostestnet.ikuwara.com:9876',
                    'p2p.testnet.nytelos.com:8012',
                    'telos.basho.eosdublin.io:9876',
                    'telos-testnet.cryptolions.io:9871',
                    'api.basho.eostribe.io:9880',
                    'p2p-telos-testnet.hkeos.com:59876',
                    't-seed.teloskorea.com:19876',
                    'telos.testnet.boid.animus.is:3535',
                    'telos.testnet.boid.animus.is:5050',
                    'kandaweather-testnet.ddns.net:8765',
                    'telos-testnet.eosio.cr:9879',
                    'testnet.dailytelos.net:9877',
                    'testnet.telos.goodblock.io:9876'
                ],
                'subst': 'http://evmwasms.s3.amazonaws.com/subst.json'
            }
        },
        {
            'name': 'translator',
            'chain_name': 'telos-testnet',
            'chain_id': 41,
            'start_block': 136393814,
            'block_delta': 57,

            'prev_hash': '8e149fd918bad5a4adfe6f17478e46643f7db7292a2b7b9247f48dc85bdeec94'
        },
        {
            'name': 'rpc',
        }
    ]
}


DEFAULT_MAINNET_CONFIG = {
    'name': 'telos-evm-mainnet-node',
    'services': ['rpc'],
    'stack': [
        {
            'name': 'leap',

            'chain_id': '4667b205c6838ef70ff7988f6e8257e8be0e1284a2f59699054a018f743b1d11',
            'chain_type': 'mainnet',

            'snapshot': 'http://storage.telos.net/test-resources/telos-mainnet-snapshot-evm-deploy.bin',

            'ini': {
                'plugins': [
                    'eosio::http_plugin',
                    'eosio::chain_api_plugin',
                    'eosio::state_history_plugin'
                ],
                'peers': [
                    'telosp2p.actifit.io:9876',
                    'telos.eu.eosamsterdam.net:9120',
                    'p2p.telos.eosargentina.io:9879',
                    'telos.p2p.boid.animus.is:5151',
                    'telos.p2p.boid.animus.is:5252',
                    'p2p.telos.y-knot.io:9877',
                    'telos.caleos.io:9880',
                    'p2p.creativblock.org:9876',
                    'p2p.telos.cryptobloks.io:9876',
                    'telos.cryptolions.io:9871',
                    'p2p.dailytelos.net:9876',
                    'p2p.telos.detroitledger.tech:1337',
                    'node-telos.eosauthority.com:10311',
                    'telosp2p.eos.barcelona:2095',
                    'peer1-telos.eosphere.io:9876',
                    'peer2-telos.eosphere.io:9876',
                    'telos.eosrio.io:8092',
                    'api.telos.cryptotribe.io:7876',
                    'telos.p2p.eosusa.io:9876',
                    'telos.eosvenezuela.io:9871',
                    'p2p.fortisbp.io:9876',
                    'mainnet.telos.goodblock.io:9879',
                    'seed-telos.infinitybloc.io:9877',
                    'p2p.kainosbp.com:9876',
                    'kandaweather-mainnet.ddns.net:9876',
                    'tlos-p2p.katalyo.com:11877',
                    'telos.seed.eosnation.io:9876',
                    'p2p.telos.nodenode.org:9876',
                    'p2p.telos.pandabloks.com:9876',
                    'mainnet.persiantelos.com:8880',
                    'telosp2p.sentnl.io:4242',
                    'p2p.telos.africa:9877',
                    'telos.eossweden.eu:8012',
                    'telos.greymass.com:19871',
                    'peers.teleology.one:9876',
                    'telos.teleology.one:9876',
                    'p2p.telosarabia.net:9876',
                    'sslapi.teloscentral.com:9876',
                    'testnet.telosculture.com:9874',
                    'p2p.telosgermany.genereos.io:9876',
                    'node1.us-east.telosglobal.io:9876',
                    'node1.us-west.telosglobal.io:9876',
                    'p2p2.telos.telosgreen.com:9877',
                    'p2p.telos.blocksindia.com:9876',
                    'api.telos.kitchen:9876',
                    'seed.teloskorea.com:9876',
                    'seed.telosmadrid.io:9877',
                    'p2p.telosuk.io:9876',
                    'p2p.telosunlimited.io:9876',
                    'telosyouth.io:9876',
                    'p2p.theteloscope.io:9876',
                    'mainnet.teloscrew.com:18876',
                    '136.243.90.53:9876',
                    'p2p.telos.dutcheos.io:9876',
                    'p2p.telos.zenblocks.io:9876'
                ],
                'subst': 'http://evmwasms.s3.amazonaws.com/subst.json'
            }
        },
        {
            'name': 'translator',
            'chain_name': 'telos-mainnet',
            'chain_id': 40,
            'start_block': 180698860,
            'block_delta': 36,

            'prev_hash': 'cfa67996f5d4f1e9e2b8b13a8984e1d8997091060748c3345f160b39050809b6'
        },
        {
            'name': 'rpc',
        }
    ]
}


_config_templates: dict[str, dict] = {
    'local': DEFAULT_LOCAL_CONFIG,
    'testnet': DEFAULT_TESTNET_CONFIG,
    'mainnet': DEFAULT_MAINNET_CONFIG
}

_stack_conf_order: list[str] = ['name', 'services', 'network', 'logs', 'stack']

_service_conf_order: list[str] = [
    'name',
    'base',
    'aliases',
    'tag',
    'docker_file',
    'docker_image',
    'entrypoint',
    'service_path',
    'user',
    'group',
    'mounts',
    'ports',
    'env',
    'sym_links',
    'requires',
    'startup_logs_kwargs',
    'startup_phrase',
    'stop_sequence'
]


def generate_stack_config(template_name: str):
    if template_name not in _config_templates:
        raise ValueError(f'Unknown template name: {template_name}')

    stack_config = deepcopy(DEFAULT_BASE_CONFIG)
    template_config = _config_templates[template_name]

    # merge the top-level fields except 'stack' from template into base
    for key, value in template_config.items():
        if key != 'stack':
            stack_config[key] = value

    # now handle the 'stack' field specially, ensuring services are merged based on their 'name'
    template_stack = {service['name']: service for service in template_config['stack']}
    for i, base_service in enumerate(stack_config['stack']):
        service_name = base_service['name']
        if service_name in template_stack:
            # merge the template service configuration into the base service configuration
            service_conf = always_merger.merge(base_service, template_stack[service_name])

            # apply specific service conf key order

            # keys we dont have order info about
            extra_keys: list[str] = [key for key in service_conf if key not in _service_conf_order]

            combined_keys = _service_conf_order + extra_keys

            stack_config['stack'][i] = OrderedDict(
                (key, service_conf[key])
                for key in combined_keys
                if key in service_conf
            )

    # apply specific stack conf key order
    stack_config = OrderedDict(
        (key, stack_config[key])
        for key in _stack_conf_order
        if key in stack_config
    )

    return stack_config


def config_pre_processor(stack_config: OrderedDict) -> None:
    '''resolve custom tevmc config semantics that dockerstack
    does not know about
    '''

    _configs = {c['name']: c for c in stack_config['stack']}
    leap_conf = _configs['leap']

    if 'snapshot' in leap_conf and leap_conf['snapshot'] is not None:
        # make snapshot config semantics work:

        # if snapshot is str, assume is url pointing to
        # a bin or a compressed file with the snapshot inside
        snapshot = leap_conf['snapshot']

        # if snapshot is an int means user wants us to find
        # the closest snap to that block num
        if isinstance(snapshot, int):
            network = leap_conf['chain_type']
            logging.info(f'finding closest {network} snapshot to {snapshot}')
            snapshot, block_num = find_closest_snapshot_url(network, snapshot)
            snap_id = f'snapshot-telos-{network}-{block_num}.bin'

        elif isinstance(snapshot, str):
            # check if its url, in that case 
            parsed_url = urlparse(snapshot)

            if parsed_url.scheme in ('http', 'https'):
                # use dockerstack www_files to download the snapshot,
                # assume url ending contains file name and use that
                # with .bin suffix as snap_id
                file_name = Path(parsed_url.path.split('/')[-1])

                fname_suffixless = str(file_name.name.split('.')[0])

                snap_id = 'snapshot-' + fname_suffixless + '.bin'

                if 'www_files' not in leap_conf:
                    leap_conf['www_files'] = []


                leap_conf['www_files'].append({
                    'url': snapshot, 'rename': snap_id
                })

            elif parsed_url.scheme == '':
                # snapshot is just a file path relative to
                # leap root, leave as is and leap runtime will
                # figure it out
                ...

            else:
                raise NotImplementedError(
                    f'Unsupported snapshot resource type {snapshot}')


def initialize_node_dir(
    chain_name: str,
    config_name: str = 'tevmc.json',
    target_dir: Path | None = None
):
    '''generate fresh tevmc node directory based on template
    '''

    chain_type = 'local'
    if 'local' in chain_name:
        chain_type = 'local'
    elif 'testnet' in chain_name:
        chain_type = 'testnet'

    elif 'mainnet' in chain_name:
        chain_type = 'mainnet'

    else:
        raise NotImplementedError(
            f'No template for chain {chain_name}')

    if not isinstance(target_dir, Path):
        target_dir = Path(chain_name).resolve()

    # copy services template
    shutil.copytree(
        Path(__file__).parent.parent.parent / 'template',
        target_dir
    )

    # generate & write stack config
    stack_config = generate_stack_config(chain_type)

    config_pre_processor(stack_config)

    with open(target_dir / config_name, 'w+') as config_file:
        config_file.write(
            json.dumps(stack_config, indent=4))
