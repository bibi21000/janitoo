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

from janitoo_nosetests import JNTTBase
from janitoo_nosetests.server import JNTTDockerServerCommon, JNTTDockerServer

from janitoo.runner import Runner, jnt_parse_args
from janitoo.server import JNTServer
from janitoo.utils import HADD_SEP, HADD

class TestFakeSerser(JNTTDockerServer, JNTTDockerServerCommon):
    """Test the server
    """
    loglevel = logging.DEBUG
    path = '/tmp/janitoo_test'
    broker_user = 'toto'
    broker_password = 'toto'
    server_class = JNTServer
    server_conf = "tests/data/test_threads_hourly.conf"
    hadds = [HADD%(1118,0), HADD%(1118,1)]


class TestNetworkState(JNTTBase):
    """Test the network state machine
    """

    prog = 'start.py'

    add_ctrl = 111

    def test_100_network_state_primary(self):
        logging.config.fileConfig("tests/data/test_runner_conf_complete.conf")
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_complete.conf']):
            options = vars(jnt_parse_args())
        stopevent = threading.Event()
        net_state = JNTNetwork(stopevent, JNTOptions(options), is_primary=True, is_secondary=False, do_heartbeat_dispatch=True)
        print net_state.state
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        net_state.boot(hadds)
        i = 0
        while net_state.state != 'STARTED' and i<150:
            i += 1
            print net_state.state
            time.sleep(1)
        self.assertEqual(net_state.state, 'STARTED')
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print net_state.state
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')

    def test_110_network_state_secondary(self):
        logging.config.fileConfig("tests/data/test_runner_conf_complete.conf")
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_complete.conf']):
            options = vars(jnt_parse_args())
        stopevent = threading.Event()
        net_state = JNTNetwork(stopevent, JNTOptions(options), is_primary=False, is_secondary=True, do_heartbeat_dispatch=False, resolv_timeout=10)
        print net_state.state
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        net_state.boot(hadds)
        i = 0
        while net_state.state != 'STARTED' and i<150:
            i += 1
            print net_state.state
            time.sleep(1)
        self.assertEqual(net_state.state, 'STARTED')
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print net_state.state
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')

    def test_120_network_state_secondary_fail(self):
        logging.config.fileConfig("tests/data/test_runner_conf_complete.conf")
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_complete.conf']):
            options = vars(jnt_parse_args())
        stopevent = threading.Event()
        net_state = JNTNetwork(stopevent, JNTOptions(options), is_primary=False, is_secondary=True, do_heartbeat_dispatch=False, resolv_timeout=10)
        print net_state.state
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        net_state.boot(hadds)
        i = 0
        while net_state.state != 'STARTED' and i<150:
            i += 1
            print net_state.state
            time.sleep(1)
        self.assertEqual(net_state.state, 'STARTED')
        net_state.fsm_network_fail()
        print net_state.state
        i = 0
        while net_state.state != 'STARTED' and i<150:
            i += 1
            print net_state.state
            time.sleep(1)
        net_state.fsm_network_recover()
        print net_state.state
        i = 0
        while net_state.state != 'STARTED' and i<150:
            i += 1
            print net_state.state
            time.sleep(1)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print net_state.state
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')
