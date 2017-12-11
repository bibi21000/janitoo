# -*- coding: utf-8 -*-
"""The fake thread and components for tests

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

import logging
logger = logging.getLogger(__name__)
import os, sys
import threading
from distutils.dir_util import copy_tree
import shutil
from pkg_resources import get_distribution, DistributionNotFound, resource_filename, Requirement


from janitoo.compat import HTTPServer, BaseHTTPRequestHandler
from janitoo.compat import SimpleHTTPRequestHandler
from janitoo.compat import ThreadingMixIn
from janitoo.thread import JNTBusThread, BaseThread
from janitoo.options import get_option_autostart
from janitoo.utils import HADD
from janitoo.node import JNTNode
from janitoo.value import JNTValue
from janitoo.component import JNTComponent
from janitoo.bus import JNTBus

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_WEB_CONTROLLER = 0x1030
COMMAND_WEB_RESOURCE = 0x1031
COMMAND_DOC_RESOURCE = 0x1032

assert(COMMAND_DESC[COMMAND_WEB_CONTROLLER] == 'COMMAND_WEB_CONTROLLER')
assert(COMMAND_DESC[COMMAND_WEB_RESOURCE] == 'COMMAND_WEB_RESOURCE')
assert(COMMAND_DESC[COMMAND_DOC_RESOURCE] == 'COMMAND_DOC_RESOURCE')
##############################################################

DEPLOY_DIRS = ['css', 'images', 'js']

def make_thread(options, force=False):
    if get_option_autostart(options, 'fake') == True or force:
        return FakeThread(options)
    else:
        return None

def make_fake_component(**kwargs):
    return FakeComponent(**kwargs)

class FakeBus(JNTBus):
    """A fake bus
    """
    def __init__(self, **kwargs):
        """
        :param int bus_id: the SMBus id (see Raspberry Pi documentation)
        :param kwargs: parameters transmitted to :py:class:`smbus.SMBus` initializer
        """
        oid = kwargs.pop('oid', 'fake')
        JNTBus.__init__(self, oid=oid, **kwargs)

    def check_heartbeat(self):
        """Check that the component is 'available'

        """
        return True

class FakeComponent(JNTComponent):
    """ A fake component """

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', 'fake.component')
        name = kwargs.pop('name', "Fake component")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name,
                **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)
        uuid="test_basic"
        self.values[uuid] = JNTValue( uuid=uuid,
                    index=0,
                    genre=0x01,
                )
        uuid="test_user"
        self.values[uuid] = JNTValue( uuid=uuid,
                    index=0,
                    genre=0x02,
                )
        uuid="test_command"
        self.values[uuid] = JNTValue( uuid=uuid,
                    index=0,
                    genre=0x05,
                )
        uuid="test_config"
        self.values[uuid] = JNTValue( uuid=uuid,
                    index=0,
                    genre=0x03,
                )

    def check_heartbeat_file(self, filename):
        """Check that the component is 'available'

        """
        return True

class FakeThread(JNTBusThread):
    """The Http thread

    """
    def init_bus(self):
        """Build the bus
        """
        self.section = 'fake'
        self.bus = FakeBus(options=self.options, product_name="Fake server")
