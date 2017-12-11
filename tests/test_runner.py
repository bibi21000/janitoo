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
from common import TestJanitoo, SLEEP
from janitoo.runner import Runner, jnt_parse_args
import mock

class FakeServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._stopevent = threading.Event( )
    def run(self):
        i = 0
        while not self._stopevent.isSet():
            i += 1
            self._stopevent.wait(2.0)
    def stop(self):
        self._stopevent.set( )

class MyFakeRunner(Runner):
    def app_run(self):
        self.fake = FakeServer()
        self.fake.run()
    def app_shutdown(self):
        self.fake.stop()

class TestArgParser(TestJanitoo):
    """Test the argument parser
    """
    prog='start.py'

    def test_010_args_start_stop(self):
        with mock.patch('sys.argv', [self.prog, 'start']):
            args = jnt_parse_args()
            print(args)
            self.assertEqual(args.command, 'start')
        with mock.patch('sys.argv', [self.prog, 'stop']):
            args = jnt_parse_args()
            print(args)
            self.assertEqual(args.command, 'stop')

    def test_020_args_service(self):
        with mock.patch('sys.argv', [self.prog, 'start', '--service=jnt_test']):
            args = jnt_parse_args()
            print(args)
            self.assertEqual(args.command, 'start')
            self.assertEqual(args.service, 'jnt_test')

    def test_030_args_service_from_conf(self):
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf1.conf']):
            args = jnt_parse_args()
            print(args)
            self.assertEqual(args.command, 'start')
            self.assertEqual(args.service, 'jnt_test')

    def test_050_args_to_dict(self):
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_complete.conf']):
            args = vars(jnt_parse_args())
            print(args)
            self.assertEqual(args['service'], 'jnt_test')
            self.assertEqual(args['user'], 'janitoo')
            self.assertEqual(args['log_dir'], '/tmp/janitoo_test/log')
            self.assertEqual(args['home_dir'], '/tmp/janitoo_test/home')
            self.assertEqual(args['pid_dir'], '/tmp/janitoo_test/run')
            self.assertEqual(args['conf_dir'], '/tmp/janitoo_test/etc')
            self.assertEqual(args['broker_ip'], '127.0.0.1')
            self.assertEqual(args['broker_port'], '1883')
            self.assertEqual(args['broker_user'], 'myuser')
            self.assertEqual(args['broker_password'], 'mypassword')
            self.assertEqual(args['conf_file'], 'tests/data/test_runner_conf_complete.conf')

class TestRunnerLow(TestJanitoo):
    """Test the runner
    """
    prog='janitoo.py'

    def setUp(self):
        self.mkDir('/tmp/janitoo_test/log')
        self.mkDir('/tmp/janitoo_test/home')
        self.mkDir('/tmp/janitoo_test/run')
        self.mkDir('/tmp/janitoo_test/etc')

    #def tearDown(self):
    #    self.rmDir('/tmp/janitoo_test')

    def test_010_runner_start_stop(self):
        self.wipTest()
        with mock.patch('sys.argv', [self.prog, 'start', '--conf_file=tests/data/test_runner_conf_testing.conf']):
            daemon = MyFakeRunner()
            daemon.do_action()
        time.sleep(5)
        with mock.patch('sys.argv', [self.prog, 'stop', '--conf_file=tests/data/test_runner_conf_testing.conf']):
            daemon = MyFakeRunner()
            daemon.do_action()
        time.sleep(5)
