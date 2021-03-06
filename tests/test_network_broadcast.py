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

from .common import TestJanitoo, SLEEP

from janitoo_nosetests import JNTTBase
from janitoo.runner import Runner, jnt_parse_args
from janitoo.server import JNTServer
from janitoo.dhcp import JNTNetwork
from janitoo.tests import FakeBus
from janitoo.node import JNTNodeMan, JNTBusNodeMan
from janitoo.options import JNTOptions
from janitoo.utils import HADD, HADD_SEP, CADD, json_dumps, json_loads
import mock

class CommonNetworkState(JNTTBase):
    """Test the network state machine
    """

    prog = 'start.py'

    net_add_ctrl = 111
    node_add_ctrl = 1118

    network = None
    nodeman = None

    def tearDown(self):
        if self.network is not None:
            self.network.stop()
            while not self.network.is_stopped and i<10:
                i += 1
                time.sleep(1)
        if self.nodeman is not None:
            self.nodeman.stop()
            while not self.nodeman.is_stopped and i<10:
                i += 1
                time.sleep(1)
        time.sleep(5)
        self.nodeman = None
        self.network = None

class TestNetworkState1(CommonNetworkState):
    """Test the network state machine
    """
    def test_001_broadcast_secondary(self):
        #~ self.wipTest("Freeze")
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_nodeman.conf']):
            options = vars(jnt_parse_args())
            options = JNTOptions(options)
        section = 'fake'
        thread_uuid = options.get_option(section, 'uuid')
        if thread_uuid == None:
            thread_uuid = muuid.uuid1()
            options.set_option(section, 'uuid', "%s"%thread_uuid)
        self.nodeman = JNTBusNodeMan(options, FakeBus(options=options, product_name="Http server"), section, thread_uuid)
        print(self.nodeman.state)
        #~ hadds = { 0 : HADD%(self.node_add_ctrl,0),
                     #~ }
        self.nodeman.start()
        i = 0
        while not self.nodeman.is_started and i<120:
            i += 1
            print(self.nodeman.state)
            time.sleep(1)
        self.assertEqual(self.nodeman.state, 'ONLINE')


        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_network.conf']):
            options = vars(jnt_parse_args())
        stopevent = threading.Event()
        self.network = JNTNetwork(stopevent, JNTOptions(options), is_primary=False, is_secondary=True, do_heartbeat_dispatch=True)
        print(self.network.state)
        hadds = { 0 : HADD%(self.net_add_ctrl,0),
                     }
        self.network.boot(hadds)
        i = 0
        while not self.network.is_started and i<150:
            i += 1
            print(self.network.state)
            time.sleep(1)
        print(self.network.state)
        self.assertEqual(self.network.state, 'STARTED')

        time.sleep(30)

        print("network.nodes", self.network.nodes)
        print("network.users", self.network.users)
        print("network.configs", self.network.configs)
        print("network.basics", self.network.basics)
        print("network.systems", self.network.systems)
        print("network.commands", self.network.commands)

        print("HADD", HADD%(self.node_add_ctrl,0))

        self.assertTrue(HADD%(self.node_add_ctrl,0) in self.network.nodes)
        self.assertTrue(HADD%(self.node_add_ctrl,0) in self.network.systems)
        self.assertTrue(HADD%(self.node_add_ctrl,0) in self.network.configs)
        self.assertTrue(HADD%(self.node_add_ctrl,1) in self.network.nodes)
        self.assertTrue(HADD%(self.node_add_ctrl,1) in self.network.systems)
        self.assertTrue(HADD%(self.node_add_ctrl,1) in self.network.configs)
        self.assertTrue(HADD%(self.node_add_ctrl,1) in self.network.basics)
        self.assertTrue(HADD%(self.node_add_ctrl,1) in self.network.users)
        self.assertTrue(HADD%(self.node_add_ctrl,1) in self.network.commands)

class TestNetworkState2(CommonNetworkState):
    """Test the network state machine
    """
    def test_011_broadcast_primary(self):
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_nodeman.conf']):
            options = vars(jnt_parse_args())
            options = JNTOptions(options)
        section = 'fake'
        thread_uuid = options.get_option(section, 'uuid')
        if thread_uuid == None:
            thread_uuid = muuid.uuid1()
            options.set_option(section, 'uuid', "%s"%thread_uuid)
        self.nodeman = JNTBusNodeMan(options, FakeBus(options=options, product_name="Http server"), section, thread_uuid)
        print(self.nodeman.state)
        #~ hadds = { 0 : HADD%(self.node_add_ctrl,0),
                     #~ }
        self.nodeman.start()
        i = 0
        while not self.nodeman.is_started and i<120:
            i += 1
            print(self.nodeman.state)
            time.sleep(1)
        self.assertEqual(self.nodeman.state, 'ONLINE')


        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_network.conf']):
            options = vars(jnt_parse_args())
        stopevent = threading.Event()
        self.network = JNTNetwork(stopevent, JNTOptions(options), is_primary=True, is_secondary=False, do_heartbeat_dispatch=True)
        print(self.network.state)
        hadds = { 0 : HADD%(self.net_add_ctrl,0),
                     }
        self.network.boot(hadds)
        i = 0
        while not self.network.is_started and i<150:
            i += 1
            print(self.network.state)
            time.sleep(1)
        print(self.network.state)
        self.assertEqual(self.network.state, 'STARTED')

        time.sleep(30)

        print("network.nodes", self.network.nodes)
        print("network.users", self.network.users)
        print("network.configs", self.network.configs)
        print("network.basics", self.network.basics)
        print("network.systems", self.network.systems)
        print("network.commands", self.network.commands)

        print("HADD", HADD%(self.node_add_ctrl,0))

        self.assertTrue(HADD%(self.node_add_ctrl,0) in self.network.nodes)
        self.assertTrue(HADD%(self.node_add_ctrl,0) in self.network.systems)
        self.assertTrue(HADD%(self.node_add_ctrl,0) in self.network.configs)
        self.assertTrue(HADD%(self.node_add_ctrl,1) in self.network.nodes)
        self.assertTrue(HADD%(self.node_add_ctrl,1) in self.network.systems)
        self.assertTrue(HADD%(self.node_add_ctrl,1) in self.network.configs)
        self.assertTrue(HADD%(self.node_add_ctrl,1) in self.network.basics)
        self.assertTrue(HADD%(self.node_add_ctrl,1) in self.network.users)
        self.assertTrue(HADD%(self.node_add_ctrl,1) in self.network.commands)
