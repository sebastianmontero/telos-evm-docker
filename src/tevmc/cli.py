#!/usr/bin/env python3

from pathlib import Path

import click

from dockerstack.stack import DockerStack, DockerStackException

from tevmc.config import initialize_node_dir
from tevmc.logging import get_tevmc_logger


@click.group()
def cli():
    pass

@cli.command()
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
@click.argument('chain-name')
def init(config, chain_name):
    initialize_node_dir(chain_name, config_name=config)


@cli.command()
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
@click.option(
    '--node-root', default='.',
    help='tevmc node working dir')
@click.option(
    '--exist-ok', default=True,
    help='dont throw error when node is already up')
@click.option(
    '--repair', default=True,
    help='attempt fix unhealthy services')
@click.option(
    '--log-level', default='info',
    help='logging verbosity level')
def up(config, node_root, exist_ok, repair, log_level):
    _stack = DockerStack(
        root_pwd=Path(node_root).resolve(strict=True),
        logger=get_tevmc_logger(log_level),
        config_name=config
    )

    with _stack.open(
        exist_ok=exist_ok,
        teardown=False
    ) as _stack:
        ...


@cli.group()
def service():
    ...


@service.command()
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
@click.option(
    '--node-root', default='.',
    help='tevmc node working dir')
@click.option(
    '--log-level', default='info',
    help='logging verbosity level')
@click.argument('service-alias')
def status(config, node_root, log_level, service_alias):
    _stack = DockerStack(
        root_pwd=Path(node_root).resolve(strict=True),
        logger=get_tevmc_logger(log_level),
        config_name=config
    )

    _stack.initialize()
    service = _stack.get_service(service_alias)
    status = service.status
    _stack.logger.stack_info(f'service \"{service}\" status: {status}')


@service.command()
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
@click.option(
    '--node-root', default='.',
    help='tevmc node working dir')
@click.option(
    '--log-level', default='info',
    help='logging verbosity level')
@click.argument('service-alias')
@click.argument('method')
@click.argument('fn_args', nargs=-1, type=str)
def run(config, node_root, log_level, service_alias, method, fn_args):
    _stack = DockerStack(
        root_pwd=Path(node_root).resolve(strict=True),
        logger=get_tevmc_logger(log_level),
        config_name=config
    )

    _stack.initialize()
    service = _stack.get_service(service_alias)

    serv_fn = getattr(service, method, None)
    if not serv_fn:
        _stack.logger.error(f'service {service} has no method named {method}!')
        exit(1)

    ret = serv_fn(*fn_args)
    if ret:
        print(ret)


@cli.command()
@click.option(
    '--config', default='tevmc.json',
    help='Unified config file name.')
@click.option(
    '--node-root', default='.',
    help='tevmc node working dir')
@click.option(
    '--force', default=False,
    help='teardown even if a service is unhealthy')
@click.option(
    '--log-level', default='info',
    help='logging verbosity level')
def down(config, node_root, force, log_level):
    _stack = DockerStack(
        root_pwd=Path(node_root).resolve(strict=True),
        logger=get_tevmc_logger(log_level),
        config_name=config
    )

    _stack.initialize()

    if _stack.status != 'healthy' and not force:
        raise DockerStackException(f'TEVMC stack is unhealthy and --force=True not passed')

    _stack.stop()
