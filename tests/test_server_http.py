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
__copyright__ = "Copyright © 2013-2014-2015 Sébastien GALLET aka bibi21000"

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

#~ JNTTBase.skipCITest()
JNTTServer.skipDockerTest()

class TestHttpSerser(JNTTServer, JNTTServerCommon):
    """Test the server
    """
    loglevel = logging.DEBUG
    path = '/tmp/janitoo_test'
    broker_user = 'toto'
    broker_password = 'toto'
    server_class = JNTServer
    server_conf = "tests/data/test_server_http.conf"
    hadds = [HADD%(1118,0), HADD%(1118,1)]

    def test_101_server_start_no_error_in_log(self):
        self.start()
        try:
            self.assertHeartbeatNodes(hadds=self.hadds)
            time.sleep(120)
            self.assertInLogfile('Found heartbeats in timeout')
            self.assertNotInLogfile('^ERROR ')
        finally:
            self.stop()
