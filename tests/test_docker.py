# -*- coding: utf-8 -*-

"""Unittests for Janitoo-common.
"""
__license__ = """
    This file is part of Janitoo.

    Janitoo is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Janitoo is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Janitoo. If not, see <http://www.gnu.org/licenses/>.

"""
__author__ = 'Sébastien GALLET aka bibi21000'
__email__ = 'bibi21000@gmail.com'
__copyright__ = "Copyright © 2013-2014-2015-2016 Sébastien GALLET aka bibi21000"

import warnings
warnings.filterwarnings("ignore")

import sys, os
import time
import unittest
import logging
import threading
import mock
import logging

from janitoo_nosetests import JNTTDockerBase, JNTTBase
from janitoo_nosetests.server import JNTTDockerServerCommon, JNTTDockerServer

from janitoo.runner import Runner, jnt_parse_args
from janitoo.server import JNTServer
from janitoo.dhcp import JNTNetwork
from janitoo.options import JNTOptions
from janitoo.utils import HADD, HADD_SEP, CADD, json_dumps, json_loads

sys.path.insert(0, os.path.abspath('.'))

JNTTBase.onlyDockerTest()

from .test_rfid import RFIDCommon
from .test_network import NetworkStateCommon
from .test_nodeman import NodeManagerCommon

class TestRFID(JNTTDockerBase, RFIDCommon):
    """Test RFID
    """
    pass

class TestFakeSerser(JNTTDockerServer, JNTTDockerServerCommon):
    """Test the server
    """
    server_class = JNTServer
    server_conf = "tests/data/test_threads_hourly.conf"
    hadds = [HADD%(1118,0), HADD%(1118,1)]

class TestNetworkState(JNTTDockerBase, NetworkStateCommon):
    """Test the network state machine
    """
    prog = 'dontcare.py'
    add_ctrl = 111

class TestNodeManager(JNTTDockerBase, NodeManagerCommon):
    """Test the network state machine
    """
    prog = 'dontcare.py'
    add_ctrl = 111


