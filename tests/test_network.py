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
import threading
import logging
from janitoo_nosetests import JNTTBase
from common import TestJanitoo, SLEEP
from janitoo.runner import Runner, jnt_parse_args
from janitoo.server import JNTServer
from janitoo.dhcp import JNTNetwork
from janitoo.options import JNTOptions
from janitoo.utils import HADD, HADD_SEP, CADD, json_dumps, json_loads
import mock

import logging
#~ logging.basicConfig(filename='/tmp/janitoo_test/log/network.log',level=logging.DEBUG)

class NetworkStateCommon():
    """Test the network state machine
    """
    def test_010_network_sfm_primary(self):
        logging.config.fileConfig("tests/data/test_runner_conf_complete.conf")
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_complete.conf']):
            options = vars(jnt_parse_args())
        stopevent = threading.Event()
        net_state = JNTNetwork(stopevent, JNTOptions(options), is_primary=True, is_secondary=False, do_heartbeat_dispatch=True, test=True)
        net_state.start()
        while net_state.state != 'STARTED':
            net_state.fsm_network_next()
        net_state.stop()

    def test_050_network_sfm_secondary(self):
        logging.config.fileConfig("tests/data/test_runner_conf_complete.conf")
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_complete.conf']):
            options = vars(jnt_parse_args())
        stopevent = threading.Event()
        net_state = JNTNetwork(stopevent, JNTOptions(options), is_primary=False, is_secondary=True, do_heartbeat_dispatch=False, test=True)
        net_state.start()
        while net_state.state != 'STARTED':
            net_state.fsm_network_next()
        net_state.stop()

    def test_060_network_sfm_secondary_fail(self):
        logging.config.fileConfig("tests/data/test_runner_conf_complete.conf")
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_complete.conf']):
            options = vars(jnt_parse_args())
        stopevent = threading.Event()
        net_state = JNTNetwork(stopevent, JNTOptions(options), is_primary=False, is_secondary=True, do_heartbeat_dispatch=False, test=True)
        net_state.start()
        while net_state.state != 'STARTED':
            net_state.fsm_network_next()
        net_state.fsm_network_fail()
        while net_state.state != 'STARTED':
            net_state.fsm_network_next()
        net_state.fsm_network_recover()
        while net_state.state != 'STARTED':
            net_state.fsm_network_next()
        net_state.stop()

    def test_100_network_state_primary(self):
        logging.config.fileConfig("tests/data/test_runner_conf_complete.conf")
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_complete.conf']):
            options = vars(jnt_parse_args())
        stopevent = threading.Event()
        net_state = JNTNetwork(stopevent, JNTOptions(options), is_primary=True, is_secondary=False, do_heartbeat_dispatch=True)
        print(net_state.state)
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        net_state.boot(hadds)
        i = 0
        while net_state.state != 'STARTED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STARTED')
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')

    def test_110_network_state_secondary(self):
        logging.config.fileConfig("tests/data/test_runner_conf_complete.conf")
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_complete.conf']):
            options = vars(jnt_parse_args())
        stopevent = threading.Event()
        net_state = JNTNetwork(stopevent, JNTOptions(options), is_primary=False, is_secondary=True, do_heartbeat_dispatch=False, resolv_timeout=10)
        print(net_state.state)
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        net_state.boot(hadds)
        i = 0
        while net_state.state != 'STARTED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STARTED')
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')

    def test_120_network_state_secondary_fail(self):
        logging.config.fileConfig("tests/data/test_runner_conf_complete.conf")
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_complete.conf']):
            options = vars(jnt_parse_args())
        stopevent = threading.Event()
        net_state = JNTNetwork(stopevent, JNTOptions(options), is_primary=False, is_secondary=True, do_heartbeat_dispatch=False, resolv_timeout=10)
        print(net_state.state)
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        net_state.boot(hadds)
        i = 0
        while net_state.state != 'STARTED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STARTED')
        net_state.fsm_network_fail()
        print(net_state.state)
        i = 0
        while net_state.state != 'STARTED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        net_state.fsm_network_recover()
        print(net_state.state)
        i = 0
        while net_state.state != 'STARTED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')

class TestNetworkState(JNTTBase, NetworkStateCommon):
    """Test the network state machine
    """

    prog = 'start.py'

    add_ctrl = 111


    def test_130_network_state_secondary_random(self):
        #~ self.skipTest("Pass but freeze on Docker/CI. Surely a non stopped thread in the state machine")
        self.onlyCITest()
        logging.config.fileConfig("tests/data/test_runner_conf_complete.conf")
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_complete.conf']):
            options = vars(jnt_parse_args())
        stopevent = threading.Event()
        net_state = JNTNetwork(stopevent, JNTOptions(options), is_primary=False, is_secondary=True, do_heartbeat_dispatch=False, resolv_timeout=10)
        print(net_state.state)
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        net_state.boot(hadds)
        time.sleep(8)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')
        net_state.boot(hadds)
        time.sleep(15)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')
        net_state.boot(hadds)
        time.sleep(21)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')
        net_state.boot(hadds)
        time.sleep(42)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')

    def test_131_network_state_secondary_random_more(self):
        #~ self.skipTest("Pass but freeze on Docker/CI. Surely a non stopped thread in the state machine")
        self.onlyCITest()
        logging.config.fileConfig("tests/data/test_runner_conf_complete.conf")
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_complete.conf']):
            options = vars(jnt_parse_args())
        stopevent = threading.Event()
        net_state = JNTNetwork(stopevent, JNTOptions(options), is_primary=False, is_secondary=True, do_heartbeat_dispatch=False, resolv_timeout=5)
        print(net_state.state)
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        net_state.boot(hadds)
        time.sleep(5)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')
        net_state.boot(hadds)
        time.sleep(25)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')
        net_state.boot(hadds)
        time.sleep(31)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')
        net_state.boot(hadds)
        time.sleep(52)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')

    def test_140_network_state_primary_random(self):
        #~ self.skipTest("Pass but freeze on Docker/CI. Surely a non stopped thread in the state machine")
        self.onlyCITest()
        logging.config.fileConfig("tests/data/test_runner_conf_complete.conf")
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_complete.conf']):
            options = vars(jnt_parse_args())
        stopevent = threading.Event()
        net_state = JNTNetwork(stopevent, JNTOptions(options), is_primary=True, is_secondary=False, do_heartbeat_dispatch=True, resolv_timeout=10)
        print(net_state.state)
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        net_state.boot(hadds)
        time.sleep(8)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')
        net_state.boot(hadds)
        time.sleep(15)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')
        net_state.boot(hadds)
        time.sleep(21)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')
        net_state.boot(hadds)
        time.sleep(42)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')

    def test_141_network_state_primary_random_more(self):
        #~ self.skipTest("Pass but freeze on Docker/CI. Surely a non stopped thread in the state machine")
        self.onlyCITest()
        logging.config.fileConfig("tests/data/test_runner_conf_complete.conf")
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_complete.conf']):
            options = vars(jnt_parse_args())
        stopevent = threading.Event()
        net_state = JNTNetwork(stopevent, JNTOptions(options), is_primary=True, is_secondary=False, do_heartbeat_dispatch=True, resolv_timeout=5)
        print(net_state.state)
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        net_state.boot(hadds)
        time.sleep(5)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')
        net_state.boot(hadds)
        time.sleep(25)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')
        net_state.boot(hadds)
        time.sleep(31)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')
        net_state.boot(hadds)
        time.sleep(52)
        net_state.stop()
        i = 0
        while net_state.state != 'STOPPED' and i<150:
            i += 1
            print(net_state.state)
            time.sleep(1)
        self.assertEqual(net_state.state, 'STOPPED')
