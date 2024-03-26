#!/usr/bin/env python3

import shutil

from pathlib import Path
from typing import Generator

import pdbp
import pytest
import requests

from dockerstack.stack import DockerStack
from dockerstack.utils import docker_rm
from dockerstack.testing import StackFixtureParams, maybe_get_marker

from tevmc.config import initialize_node_dir
from tevmc.logging import get_tevmc_logger


@pytest.fixture()
def compile_evm():
    # maybe compile uniswap v2 core
    uswap_v2_dir = Path('tests/evm-contracts/uniswap-v2-core')
    if not (uswap_v2_dir / 'build').exists():

        # run yarn & compile separate cause their script dies
        # installing optional deps and this is ok
        process = subprocess.run(
            'yarn',
            shell=True, cwd=uswap_v2_dir,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        if process.returncode != 0:
            last_line = process.stdout.splitlines()[-1]
            if 'you can safely ignore this error' not in last_line:
                logging.error(process.stdout)
                raise ChildProcessError(f'Failed to install uniswap v2 core deps')

        process = subprocess.run(
            'yarn compile',
            shell=True, cwd=uswap_v2_dir,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        if process.returncode != 0:
            logging.error(process.stdout)
            raise ChildProcessError(f'Failed to compile uniswap v2 core')



@pytest.fixture
def tevmc(tmp_path_factory, request) -> Generator[DockerStack, None, None]:

    tevmc_logger = get_tevmc_logger('info')
    tmp_path: Path = tmp_path_factory.getbasetemp() / request.node.name

    _stack_config = maybe_get_marker(
        request, 'stack_config', 'kwargs',
        {})

    if 'from_template' not in _stack_config:
        _stack_config['from_template'] = 'template'

    if 'config_name' not in _stack_config:
        _stack_config['config_name'] = 'tevmc.json'

    if 'chain_name' not in _stack_config:
        _stack_config['chain_name'] = f'telos-local-{request.node.name}'

    config = StackFixtureParams(**_stack_config)

    target_dir = config.target_dir

    if target_dir is None:
        target_dir = str(tmp_path) if not config.from_dir else config.from_dir

    target_dir = Path(target_dir)
    assert isinstance(target_dir, Path)

    chain_name: str = _stack_config['chain_name']

    if config.from_template:
        src_dir = Path(str(config.from_template))

        if not src_dir.exists() or not src_dir.is_dir():
            pytest.fail(f'Specified example directory does not exist: {src_dir}')

        # delete node dir if exists
        if target_dir.exists():
            if not config.exist_ok:
                tevmc_logger.info(f'node dir already exists, removing...')
                docker_rm(target_dir)

            # update templates and runtime only
            for path in src_dir.rglob('*'):
                # check if the current path is a file and matches the desired extensions
                if path.is_file() and (
                    path.suffix == '.py' or
                    path.suffix == '.template' or
                    'Dockerfile' in path.name
                ):
                    relative_path = path.relative_to(src_dir)
                    target_path = target_dir / relative_path

                    # ensure the target directory exists
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # copy the file
                    shutil.copy(path, target_path)
                    tevmc_logger.info(f'update file {path} -> {target_path}')

                elif path.is_dir():
                    # create the directory structure in the target directory
                    relative_dir_path = path.relative_to(src_dir)
                    target_dir_path = target_dir / relative_dir_path
                    target_dir_path.mkdir(parents=True, exist_ok=True)

        else:
            initialize_node_dir(chain_name, target_dir=target_dir)

    _stack = DockerStack(
        root_pwd=target_dir.resolve(strict=True),
        config_name=config.config_name,
        logger=tevmc_logger,
        cache_dir='tests/.cache'
    )

    with _stack.open(
        exist_ok=config.exist_ok,
        teardown=config.teardown
    ) as _stack:
        yield _stack
