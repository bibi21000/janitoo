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
import mock

from janitoo_nosetests import JNTTBase
from janitoo_nosetests.server import JNTTServer, JNTTServerCommon

from janitoo.runner import Runner, jnt_parse_args
from janitoo.server import JNTServer
from janitoo.utils import HADD_SEP, HADD

class TestSerser(JNTTBase):
    """Test the common server
    """
    prog='start.py'

    def test_010_server_service_to_dict(self):
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_server_conf_testing.conf']):
            options = vars(jnt_parse_args())
            server = JNTServer(options)
            self.assertEqual(server.options.get_options('database')['sqlalchemy.url'], 'sqlite:////tmp/janitoo_test/home/test_test.db')

    def test_020_server_start(self):
        #~ self.wipTest("Pass but freeze nosetests")
        server = None
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_complete.conf']):
            options = vars(jnt_parse_args())
            server = JNTServer(options)
        server.start()
        time.sleep(5)
        server.stop()

    def test_030_server_options(self):
        #~ self.skipTest("Pass but freeze nosetests")
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_server_conf_testing.conf']):
            options = vars(jnt_parse_args())
            server = JNTServer(options)
            self.assertEqual(server.options.get_options('database')['sqlalchemy.url'], 'sqlite:////tmp/janitoo_test/home/test_test.db')
            noptions = server.options.get_options('system')
            self.assertEqual(noptions['service'], options['service'])
            self.assertEqual(noptions['user'], options['user'])
            noptions = server.options.get_options('test')
            self.assertEqual(type(noptions), type({}))
            self.assertEqual(len(noptions), 0)
            noptions['timeout'] = 10
            noptions['tries'] = 3
            print(noptions)
            server.options.set_options(u'test2', noptions)
            noptions = None
            noptions = server.options.get_options('test2')
            self.assertEqual(noptions['timeout'], 10)
            self.assertEqual(noptions['tries'], 3)
            server.options.remove_options('test2')
            noptions = None
            noptions = server.options.get_options('test2')
            print(noptions)
            self.assertEqual(type(noptions), type({}))
            self.assertEqual(len(noptions), 0)

class TestFakeSerser(JNTTServer, JNTTServerCommon):
    """Test the server
    """
    loglevel = logging.DEBUG
    path = '/tmp/janitoo_test'
    broker_user = 'toto'
    broker_password = 'toto'
    server_class = JNTServer
    server_conf = "tests/data/test_threads.conf"
    server_section = "fake"
    hadds = [HADD%(1118,0), HADD%(1118,1), HADD%(1118,2)]

    def test_040_server_start_no_error_in_log(self):
        self.start()
        self.assertHeartbeatNodes(hadds=self.hadds)
        time.sleep(65)
        self.assertNotInLogfile('^ERROR ')
        self.assertInLogfile('Connected to broker')
        print("Reload server")
        self.server.reload()
        time.sleep(2)
        self.assertHeartbeatNodes(hadds=self.hadds)
        time.sleep(30)
        self.assertNotInLogfile('^ERROR ')
        print("Reload threads")
        self.server.reload_threads()
        time.sleep(2)
        self.assertHeartbeatNodes(hadds=self.hadds)
        time.sleep(30)
        self.assertNotInLogfile('^ERROR ')

