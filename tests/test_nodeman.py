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

from janitoo.runner import Runner, jnt_parse_args
from janitoo.server import JNTServer
from janitoo.node import JNTNodeMan, JNTBusNodeMan
from janitoo.options import JNTOptions
from janitoo.utils import HADD, HADD_SEP, CADD, json_dumps, json_loads
from janitoo.tests import FakeBus
import mock
import uuid as muuid

class NodeManagerCommon():
    """Test the NodeManager state machine
    """
    def test_010_nodeman_sfm_states(self):
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_nodeman.conf']):
            options = vars(jnt_parse_args())
            options = JNTOptions(options)
        section = 'fake'
        thread_uuid = options.get_option(section, 'uuid')
        if thread_uuid == None:
            thread_uuid = muuid.uuid1()
            options.set_option(section, 'uuid', "%s"%thread_uuid)
        node_state = JNTNodeMan(options, section, thread_uuid, test=True)
        node_state.start()
        #~ net_state.fsm_network_start()
        while node_state.state != 'ONLINE':
            node_state.fsm_state_next()
        node_state.stop()

    def test_020_busnodeman_sfm_states(self):
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_nodeman.conf']):
            options = vars(jnt_parse_args())
            options = JNTOptions(options)
        bus = FakeBus(options=options)
        section = 'fake'
        thread_uuid = options.get_option(section, 'uuid')
        if thread_uuid == None:
            thread_uuid = muuid.uuid1()
            options.set_option(section, 'uuid', "%s"%thread_uuid)
        node_state = JNTBusNodeMan(options, bus, section, thread_uuid, test=True)
        node_state.start()
        #~ net_state.fsm_network_start()
        while node_state.state != 'ONLINE':
            node_state.fsm_state_next()
        node_state.stop()

    def test_100_node_state(self):
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_nodeman.conf']):
            options = vars(jnt_parse_args())
            options = JNTOptions(options)
        section = 'fake'
        thread_uuid = options.get_option(section, 'uuid')
        if thread_uuid == None:
            thread_uuid = muuid.uuid1()
            options.set_option(section, 'uuid', "%s"%thread_uuid)
        node_state = JNTNodeMan(options, section, thread_uuid)
        print(node_state.state)
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        node_state.start()
        i = 0
        while node_state.state != 'ONLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'ONLINE')
        node_state.stop()
        i = 0
        while node_state.state != 'OFFLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'OFFLINE')
        node_state = None

    def test_110_node_start_stop_start(self):
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_nodeman.conf']):
            options = vars(jnt_parse_args())
            options = JNTOptions(options)
        section = 'fake'
        thread_uuid = options.get_option(section, 'uuid')
        if thread_uuid == None:
            thread_uuid = muuid.uuid1()
            options.set_option(section, 'uuid', "%s"%thread_uuid)
        node_state = JNTNodeMan(options, section, thread_uuid)
        print(node_state.state)
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        node_state.start()
        i = 0
        while node_state.state != 'ONLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'ONLINE')
        node_state.stop()
        i = 0
        while node_state.state != 'OFFLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'OFFLINE')
        node_state.start()
        i = 0
        while node_state.state != 'ONLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'ONLINE')
        node_state.stop()
        i = 0
        while node_state.state != 'OFFLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'OFFLINE')

    def test_120_busnode_state(self):
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_nodeman.conf']):
            options = vars(jnt_parse_args())
            options = JNTOptions(options)
        bus = FakeBus(options=options)
        section = 'fake'
        thread_uuid = options.get_option(section, 'uuid')
        if thread_uuid == None:
            thread_uuid = muuid.uuid1()
            options.set_option(section, 'uuid', "%s"%thread_uuid)
        node_state = JNTBusNodeMan(options, bus, section, thread_uuid)
        print(node_state.state)
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        node_state.start()
        i = 0
        while node_state.state != 'ONLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'ONLINE')
        node_state.stop()
        i = 0
        while node_state.state != 'OFFLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'OFFLINE')

    def test_130_busnode_start_stop_start(self):
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_nodeman.conf']):
            options = vars(jnt_parse_args())
            options = JNTOptions(options)
        bus = FakeBus(options=options)
        print(bus)
        section = 'fake'
        thread_uuid = options.get_option(section, 'uuid')
        if thread_uuid == None:
            thread_uuid = muuid.uuid1()
            options.set_option(section, 'uuid', "%s"%thread_uuid)
        node_state = JNTBusNodeMan(options, bus, section, thread_uuid)
        print(node_state.state)
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        node_state.start()
        i = 0
        while node_state.state != 'ONLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'ONLINE')
        node_state.stop()
        i = 0
        while node_state.state != 'OFFLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'OFFLINE')
        node_state.start()
        i = 0
        while node_state.state != 'ONLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'ONLINE')
        node_state.stop()
        i = 0
        while node_state.state != 'OFFLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'OFFLINE')

    def test_131_busnode_start_wait_stop(self):
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_nodeman.conf']):
            options = vars(jnt_parse_args())
            options = JNTOptions(options)
        bus = FakeBus(options=options)
        section = 'fake'
        thread_uuid = options.get_option(section, 'uuid')
        if thread_uuid == None:
            thread_uuid = muuid.uuid1()
            options.set_option(section, 'uuid', "%s"%thread_uuid)
        node_state = JNTBusNodeMan(options, bus, section, thread_uuid)
        print(node_state.state)
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        node_state.start()
        time.sleep(2)
        node_state.stop()
        i = 0
        while node_state.state != 'OFFLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'OFFLINE')
        node_state.start()
        time.sleep(7)
        node_state.stop()
        i = 0
        while node_state.state != 'OFFLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'OFFLINE')
        node_state.start()
        time.sleep(37)
        node_state.stop()
        i = 0
        while node_state.state != 'OFFLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'OFFLINE')

    def disable_210_node_manager_value_to_json(self):
        self.startClient({})
        self.nodeman = JNTNodeMan()
        key = 'test110'
        node = JNTNode(uuid=key,name='Test (%s)'%key, cmd_classes=[0x0000], hadd=HADD%(1000,1000))
        self.nodeman.add_node(node.uuid, node)
        value = JNTValue( uuid='test110_1',
                    help='The test 110_1',
                    units='°C',
                    index=0,
                    cmd_class=0x0000,
                    genre=0x02,
                    type=0x03,
                    get_data_cb=lambda x: 40.14+x,
                    is_writeonly=False,
                    is_polled=True,
                    )
        self.nodeman.add_value_to_node(value.uuid, node, value)
        self.mqtthearbeat = MQTTClient(options={})

        self.nodeman.start(self.mqttc,self.mqtthearbeat, 0.1)
        res = json_loads(value.to_json())
        print(res)
        self.assertEqual(res['uuid'], 'test110_1')
        self.assertEqual(res['help'], 'The test 110_1')
        self.assertEqual(res['cmd_class'], 0x0000)
        self.assertEqual(res['data'], 40.14)
        self.stopClient()
        self.mqtthearbeat = None

    def test_301_busnode_find_helpers(self):
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_bus.conf']):
            options = vars(jnt_parse_args())
            options = JNTOptions(options)
        bus = FakeBus(options=options)
        section = 'fake'
        thread_uuid = options.get_option(section, 'uuid')
        if thread_uuid == None:
            thread_uuid = muuid.uuid1()
            options.set_option(section, 'uuid', "%s"%thread_uuid)
        node_state = JNTBusNodeMan(options, bus, section, thread_uuid)
        print(node_state.state)
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        node_state.start()
        i = 0
        while node_state.state != 'ONLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        self.assertEqual(node_state.state, 'ONLINE')
        try:

            node = node_state.find_node('component1')
            self.assertTrue('rrd1' in node.name)
            node = node_state.find_node('componentbad')
            self.assertEqual(node, None)
            value = node_state.find_value('component1', 'heartbeat')
            self.assertTrue('component1' in value.node_uuid)
            self.assertEqual('heartbeat',value.uuid)
            value = node_state.find_value('componentbad', 'heartbeat')
            self.assertEqual(value, None)
            value = node_state.find_value('component1', 'badbeat')
            self.assertEqual(value, None)

        finally:
            node_state.stop()
            i = 0
            while node_state.state != 'OFFLINE' and i<120:
                i += 1
                print(node_state.state)
                time.sleep(1)
            self.assertEqual(node_state.state, 'OFFLINE')

class TestNodeManagerState(TestJanitoo, NodeManagerCommon):
    """Test the NodeManager state machine
    """

    prog = 'start.py'

    add_ctrl = 111

    def test_111_node_start_wait_random_stop(self):
        #~ self.skipTest("Pass but freeze on Docker/CI. Surely a non stopped thread in the state machine")
        self.onlyCITest()
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_nodeman.conf']):
            options = vars(jnt_parse_args())
            options = JNTOptions(options)
        section = 'fake'
        thread_uuid = options.get_option(section, 'uuid')
        if thread_uuid == None:
            thread_uuid = muuid.uuid1()
            options.set_option(section, 'uuid', "%s"%thread_uuid)
        node_state = JNTNodeMan(options, section, thread_uuid)
        print(node_state.state)
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        node_state.start()
        time.sleep(4)
        node_state.stop()
        i = 0
        while node_state.state != 'OFFLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        node_state.start()
        time.sleep(8)
        node_state.stop()
        i = 0
        while node_state.state != 'OFFLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        node_state.start()
        time.sleep(22)
        node_state.stop()
        i = 0
        while node_state.state != 'OFFLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)

    def test_112_node_start_wait_random_stop_more(self):
        #~ self.skipTest("Pass but freeze on Docker/CI. Surely a non stopped thread in the state machine")
        self.onlyCITest()
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_nodeman.conf']):
            options = vars(jnt_parse_args())
            options = JNTOptions(options)
        section = 'fake'
        thread_uuid = options.get_option(section, 'uuid')
        if thread_uuid == None:
            thread_uuid = muuid.uuid1()
            options.set_option(section, 'uuid', "%s"%thread_uuid)
        node_state = JNTNodeMan(options, section, thread_uuid)
        print(node_state.state)
        hadds = { 0 : HADD%(self.add_ctrl,0),
                     }
        node_state.start()
        time.sleep(6)
        node_state.stop()
        i = 0
        while node_state.state != 'OFFLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        node_state.start()
        time.sleep(15)
        node_state.stop()
        i = 0
        while node_state.state != 'OFFLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)
        node_state.start()
        time.sleep(32)
        node_state.stop()
        i = 0
        while node_state.state != 'OFFLINE' and i<120:
            i += 1
            print(node_state.state)
            time.sleep(1)

