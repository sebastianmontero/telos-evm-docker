#!/usr/bin/env python3

import os
import json
import time
import logging
import tempfile
import subprocess

from copy import deepcopy
from pathlib import Path
from datetime import timedelta
from contextlib import contextmanager
import http.server
import socketserver
import threading

import pdbp
import pytest
import requests

from tevmc.config import local, testnet, mainnet
from tevmc.testing import bootstrap_test_stack
from tevmc.testing.database import get_suffix

from elasticsearch import Elasticsearch


@pytest.fixture()
def tevmc_local2(request, tmp_path_factory):
    request.applymarker(pytest.mark.config(**local.default_config))
    with bootstrap_test_stack(request, tmp_path_factory) as tevmc:
        yield tevmc
