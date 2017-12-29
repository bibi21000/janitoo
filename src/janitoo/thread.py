# -*- coding: utf-8 -*-
"""The thread

A thread that handle a bus, ... ie i2e, onewire,

It also handle the controller for the janitoo protocol

How do what :

The tread :
 - hold the mqttc
 - ask the nodeman to boot :
   - get an HADD for the controller
   - get configuration for the controller and start the i2c bus, the onewire bus, .....
   - get an HADD for each nodes
   - get configuration of the node and start it : ie the lcd03 of i2c, the cpu of the rapsy, ...

Reloading configration:
 - inside the run loop of the thread so need to kill it and re-create a new one : only possible in the server.
   The server (=the rapsy server) can do it but it should be accessible on mqtt.
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

# Set default logging handler to avoid "No handler found" warnings.
import logging
logger = logging.getLogger(__name__)

import threading
import uuid as muuid
from datetime import datetime
from pkg_resources import resource_filename, Requirement

from janitoo.utils import JanitooNotImplemented, HADD, HADD_SEP, CADD
from janitoo.node import JNTNodeMan, JNTBusNodeMan
from janitoo.options import JNTOptions

class BaseThread(threading.Thread):
    def __init__(self, options=None):
        """Initialise the worker

        :param options: The options used to start the worker.
        :type clientid: str
        """
        threading.Thread.__init__(self)
        self._stopevent = threading.Event()
        self._reloadevent = threading.Event()
        self.config_timeout_timer = None
        self.config_timeout_delay = 3
        self.loop_sleep = 0.1
        self.slow_start = 0.2
        if not hasattr(self, 'options'):
            self.options = JNTOptions(options)
        self.uuid = None
        if not hasattr(self, 'section'):
            self.section = None
        if self.section is None:
            self.init_section()

    def __del__(self):
        """
        """
        try:
            self.stop()
        except Exception:
            pass

    def init_section(self):
        """Init the section. Must be overloaded
        """
        self.section = None

    def config_timeout_callback(self):
        """Called when configuration is finished.
        """
        logger.debug("[%s] - Configuration timeout occurs after %s seconds ... reload thread", self.__class__.__name__, self.config_timeout_delay)
        self.config_timeout_timer = None
        self._reloadevent.set( )

    def stop_trigger_reload(self, timeout=None):
        """Stop reload trigger.
        """
        if self.config_timeout_timer is not None:
            self.config_timeout_timer.cancel()
            self.config_timeout_timer = None

    def trigger_reload(self, timeout=None):
        """Trigger the config_timeout_callback to reload config.
        """
        if timeout is not None:
            try:
                self.config_timeout_delay = float(timeout)
            except ValueError:
                logger.warning("[%s] - C'ant set timeout_delay to %s seconds in trigger_reload", self.__class__.__name__, timeout)
        self.stop_trigger_reload()
        if self._stopevent.isSet():
            return
        self.config_timeout_timer = threading.Timer(self.config_timeout_delay, self.config_timeout_callback)
        self.config_timeout_timer.start()

    def stop(self):
        """Stop the thread
        """
        logger.debug("[%s] - Stop the thread", self.__class__.__name__)
        self._stopevent.set()
        self.stop_trigger_reload()

    def reload(self):
        """Stop the thread
        """
        logger.debug("[%s] - reload the thread", self.__class__.__name__)
        self._reloadevent.set()

    def pre_loop(self):
        """Launch before entering the run loop. The node manager is available.
        """
        try:
            self.loop_sleep = float(self.options.get_option(self.section, 'loop_sleep'))
        except Exception:
            logger.info("[%s] - Can't set loop_sleep from configuration file. Using default value %s", self.__class__.__name__, self.loop_sleep)
        try:
            self.slow_start = float(self.options.get_option('system','slow_start'))
        except Exception:
            logger.info("[%s] - Can't set slow_start from configuration file. Using default value %s", self.__class__.__name__, self.slow_start)

    def post_loop(self):
        """Launch after finishing the run loop. The node manager is still available.
        """
        pass

    def post_run(self):
        """Launch before exititng the run methode. You should dereference here.
        """
        pass

    def resource_filename(self, path='public', package_name=None):
        """Needed to publish static files
        """
        if package_name is None:
                package_name =self.get_package_name().split('.')[0]
        return resource_filename(Requirement.parse(package_name), path)

    def get_package_name(self):
        """Return the name of the package. Needed to publish static files

        **MUST** be copy paste in every extension that publish statics files
        """
        return __package__

class JNTThread(BaseThread):
    def __init__(self, options=None):
        """Initialise the worker

        :param options: The options used to start the worker.
        :type clientid: str
        """
        BaseThread.__init__(self, options=options)
        self.uuid = self.options.get_option(self.section, 'uuid')
        if self.uuid is None or len(self.uuid) == 0:
            self.uuid = muuid.uuid1()
            self.options.set_option(self.section, 'uuid', self.uuid)
        logger.info("[%s] - Start thread uuid %s", self.__class__.__name__, self.uuid)
        self.nodeman = self.create_nodeman()
        self.mqtt_nodes = None
        self.mqtt_broadcast = None
        self.hadds = {}
        self.heartbeat_next = None
        self.heartbeat_delay = None

    @property
    def state(self):
        """Return the nodeman state
        """
        return self.nodeman.state

    def create_nodeman(self):
        """Create the node manager
        """
        return JNTNodeMan(self.options, self.section, self.uuid)

    def run(self):
        """Run the loop
        """
        self._stopevent.clear()
        #~ self.boot()
        self.trigger_reload()
        logger.debug("[%s] - Wait for the thread reload event for initial startup", self.__class__.__name__)
        while not self._reloadevent.isSet() and not self._stopevent.isSet():
            self._reloadevent.wait(0.10)
        logger.debug("[%s] - Entering the thread loop", self.__class__.__name__)
        while not self._stopevent.isSet():
            self._reloadevent.clear()
            try:
                self.pre_loop()
            except Exception:
                logger.exception('[%s] - Exception in pre_loop', self.__class__.__name__)
                self._stopevent.set()
            self.nodeman.start(self.trigger_reload, loop_sleep=self.loop_sleep, slow_start=self.slow_start)
            while not self._reloadevent.isSet() and not self._stopevent.isSet():
                self.nodeman.loop(self._reloadevent)
            try:
                self.post_loop()
            except Exception:
                logger.exception('[%s] - Exception in post_loop', self.__class__.__name__)
            self.nodeman.stop()
            i = 0
            while not self.nodeman.is_stopped and i<100:
                i += 1
                self._reloadevent.wait(0.1)
        logger.debug("[%s] - Exiting the thread loop", self.__class__.__name__)
        self.post_run()
        self.nodeman = None

class JNTBusThread(JNTThread):
    def __init__(self, options=None):
        """Initialise the worker

        :param options: The options used to start the worker.
        :type clientid: str
        """
        self.bus = None
        self.section = None
        self.options = JNTOptions(options)
        self.init_bus()
        JNTThread.__init__(self, options=options)
        self._lock = threading.Lock()

    def create_nodeman(self):
        """
        """
        return JNTBusNodeMan(self.options, bus = self.bus, section=self.section, thread_uuid=self.uuid)

    def init_bus(self):
        """Init the bus. Must be overloaded
        """
        self.section = None
        self.bus = None

    def post_loop(self):
        """After the loop is finished
        """
        pass

    def post_run(self):
        """Launch before exititng the run methode. You should dereference here.
        Derefernce the bus
        """
        self.bus = None
