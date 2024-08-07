#!/usr/bin/env python3

from contextlib import contextmanager
from copy import deepcopy
import os
import shutil
import sys
import json
import logging

from pathlib import Path

import click
import requests

from tevmc.cmdline.build import patch_config
from tevmc.utils import deep_dict_equal

from ..config import *

from .cli import cli


class ConfigUpgradeRequiredError(Exception):
    def __init__(self, diffs):
        self.diffs = diffs
        super().__init__(self._generate_message())

    def _generate_message(self):
        msg = f'Config upgrade posible and --conf-upgrade not passed!'
        for diff in self.diffs:
            msg += '\n' + diff
        return msg 


@contextmanager
def open_node_from_dir(
    target_dir: str | Path,
    config_filename: str = 'tevmc.json',
    pid_filename: str = 'tevmc.pid',
    config_upgrade: bool = False,
    loglevel: str = 'info',
    services: list[str] = [
        'redis',
        'elastic',
        'kibana',
        'nodeos',
        'indexer',
        'rpc',
    ],
    wait: bool = False,
    sync: bool = True
):
    from ..tevmc import TEVMController

    config = load_config(str(target_dir), config_filename)
    target_dir = Path(target_dir)

    # optionally upgrade conf
    up_config = None
    cmp_config = deepcopy(config)
    if 'metadata' in cmp_config:
        del cmp_config['metadata']
    diffs = []
    if 'local' in config['telos-evm-rpc']['elastic_prefix']:
        up_config, diffs = patch_config(local.default_config, cmp_config)

    elif 'testnet' in config['telos-evm-rpc']['elastic_prefix']:
        up_config, diffs = patch_config(testnet.default_config, cmp_config)

    elif 'mainnet' in config['telos-evm-rpc']['elastic_prefix']:
        up_config, diffs = patch_config(mainnet.default_config, cmp_config)

    # if config upgrade is posible and flag not passed
    # print new conf and exit.
    if (up_config and
        not deep_dict_equal(up_config, cmp_config)):
        if config_upgrade:
            # backup old conf
            config_path = Path(target_dir) / config_filename
            backup_path = config_path.with_name(f'{config_path.name}.backup')

            if backup_path.is_file():
                raise FileExistsError('Backup file alredy exist, please move it before re-doing config upgrade...')

            shutil.copy(config_path, backup_path)

            # write upgraded config
            with open(config_path, 'w+') as conf:
                conf.write(json.dumps(up_config, indent=4))

            config = up_config

        else:
            raise ConfigUpgradeRequiredError(diffs)

    if Path(target_dir / pid_filename).resolve().exists():
        raise RuntimeError(
            'Daemon pid file exists! \n'
            'This means tevmc for this node is running or crashed, '
            'you might need to remove tevmc.pid'
        )

    fmt = logging.Formatter(
        fmt='%(asctime)s:%(levelname)s:%(message)s',
        datefmt='%H:%M:%S'
    )
    loglevel = loglevel.upper()
    logger = logging.getLogger('tevmc')
    logger.setLevel(loglevel)
    logger.propagate = False

    # config logging to stdout
    oh = logging.StreamHandler(sys.stdout)
    oh.setLevel(loglevel)
    oh.setFormatter(fmt)
    logger.addHandler(oh)

    if isinstance(services, str):
        services = json.loads(services)

    with open(target_dir / pid_filename, 'w+') as pidfile:
        pidfile.write(str(os.getpid()))

    try:
        with TEVMController(
            config,
            root_pwd=target_dir,
            logger=logger,
            wait=wait,
            services=services,
            from_latest=not sync
        ) as _tevmc:
            logger.info('control point reached')
            try:
                yield _tevmc

            except KeyboardInterrupt:
                logger.warning('interrupt catched.')

    except requests.exceptions.ReadTimeout:
        logger.critical(
            'docker timeout! usually means system hung, '
            'please await tear down or run \'tevmc clean\''
            'to cleanup envoirment.')



@cli.command()
@click.option(
    '--pid', default='tevmc.pid',
    help='Path to lock file for daemon')
@click.option(
    '--services',
    default=json.dumps([
        'redis',
        'elastic',
        'kibana',
        'nodeos',
        'indexer',
        'rpc',
    ]),
    help='Services to launch')
@click.option(
    '--wait/--no-wait', default=False,
    help='Wait until caught up to sync before launching RPC api.')
@click.option(
    '--sync/--head', default=True,
    help='Sync from chain start or from head.')
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
@click.option(
    '--loglevel', default='info',
    help='Provide logging level. Example --loglevel debug, default=warning')
@click.option(
    '--target-dir', default='.',
    help='target')
@click.option(
    '--conf-upgrade/--no-conf-upgrade', default=None,
    help='Perform or ignore posible config upgrade.')
def up(
    pid,
    services,
    wait,
    sync,
    config,
    loglevel,
    target_dir,
    conf_upgrade
):
    """Bring tevmc daemon up.
    """

    try:
        with open_node_from_dir(
            target_dir,
            config,
            pid,
            conf_upgrade,
            loglevel,
            services,
            wait,
            sync
        ) as tevmc:
            tevmc.serve_api()


    except FileNotFoundError:
        print('Config not found.')
        sys.exit(1)

    except FileExistsError:
        print('Backup file alredy exist, please move it before re-doing config upgrade...')
        sys.exit(3)

    except ConfigUpgradeRequiredError as e:
        print(e)
        sys.exit(2)

    except RuntimeError:
        print(
            'Daemon pid file exists! \n'
            'This means tevmc for this node is running or crashed, '
            'you might need to remove tevmc.pid'
        )
        sys.exit(1)

    except json.JSONDecodeError:
        print('--services value must be a json list encoded in a string')
        sys.exit(1)
