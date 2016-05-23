# -*- coding: utf-8 -*-
"""The update process of the server :

will be used to update the computer on which the server is installed.

Ideally , we need only one updater by computer (or many in the case of many virtual env).

What should we update ? :
    - the time : with the help of ntp ?
    - distribution packages
    - janitoo distribution packages
    - janitoo python modules

Most of this operations need the help of root user. We should prefer the use of sudo.

Some of them should be done using the cron system of the janitoo user : https://pypi.python.org/pypi/python-crontab. Date and time should be updatable by the user.
The use can disable them too.


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
import os, sys
import threading
import signal
import time
import uuid as muuid
from pkg_resources import iter_entry_points
from logging.config import fileConfig as logging_fileConfig

from janitoo.utils import HADD, HADD_SEP, json_dumps, json_loads
from janitoo.utils import JanitooNotImplemented, JanitooException
from janitoo.utils import TOPIC_NODES, TOPIC_NODES_REPLY, TOPIC_NODES_REQUEST
from janitoo.utils import TOPIC_BROADCAST_REPLY, TOPIC_BROADCAST_REQUEST
from janitoo.utils import TOPIC_VALUES_USER, TOPIC_VALUES_CONFIG, TOPIC_VALUES_BASIC, TOPIC_VALUES_SYSTEM, TOPIC_HEARTBEAT
from janitoo.options import JNTOptions
from janitoo.node import JNTNode
from janitoo.mqtt import MQTTClient

class JNTServer(object):
    """The Janitoo base Server

    """
    def __init__(self, options):
        """Init the server. Must be called at the begin of the children class.
        """
        self._stopevent = threading.Event()
        self.options = JNTOptions(options)
        signal.signal(signal.SIGTERM, self.sigterm_handler)
        #Need more tests
        signal.signal(signal.SIGHUP, self.sighup_handler)
        signal.signal(signal.SIGUSR1, self.sigusr1_handler)
        self._threads = []
        if 'conf_file' in self.options.data and self.options.data['conf_file'] is not None:
            logging_fileConfig(self.options.data['conf_file'])
        self.loop_sleep = 0.25
        loop_sleep = self.options.get_option('system','loop_sleep')
        if loop_sleep is not None:
            try:
                self.loop_sleep = int(loop_sleep)
            except Exception:
                logger.exception("[%s] - Exception when retrieving value of loop_sleep. Use default value instead", self.__class__.__name__)
        self.slow_start = 0.05
        slow_start = self.options.get_option('system','slow_start')
        if slow_start is not None:
            try:
                self.slow_start = int(slow_start)
            except Exception:
                logger.exception("[%s] - Exception when retrieving value of slow_start. Use default value instead", self.__class__.__name__)

    def start(self):
        """Start the server. Must be called at the end of the children class.
        """
        logger.info("[%s] - Start the server", self.__class__.__name__)
        self._stopevent.clear()
        self.start_threads()

    def start_threads(self):
        """Start the threads associated to this server.
        """
        for entry in iter_entry_points(group='janitoo.threads', name=None):
            th=None
            try:
                mkth = entry.load()
                th = mkth(self.options.data)
            except ImportError:
                logger.exception("[%s] - Exception when loading thread from entry_point", self.__class__.__name__)
            if th is not None:
                self._threads.append(th)
        for th in self._threads:
            th.start()
            self._stopevent.wait(self.slow_start)
        logger.info("[%s] - Loaded thread(s) from entry_point : %s", self.__class__.__name__, self._threads)
        if len(self._threads) == 0:
            logger.error("[%s] - Can't find a thread to launch in the config file", self.__class__.__name__)
            raise JanitooException(message="Can't find a thread to launch in the config file")
        logger.info("[%s] - Loaded thread(s) from entry_point : %s", self.__class__.__name__, self._threads)

    def pre_loop(self):
        """Before enterig the loop
        """
        pass

    def post_loop(self):
        """After the loop
        """
        pass

    def run(self):
        """Run the loop
        """
        i = 0
        self.pre_loop()
        while not self._stopevent.isSet():
            i += 1
            self._stopevent.wait(self.loop_sleep)
        self.post_loop()

    def stop(self):
        """Stop the server. Must be called at begin if overloaded in the children class
        """
        logger.info("[%s] - Stop the server", self.__class__.__name__)
        self._stopevent.set( )
        for th in self._threads:
            th.stop()
        for th in self._threads:
            if th.is_alive():
                th.join()
        self._threads = []

    def reload_threads(self):
        """Reload the threads
        """
        logger.debug("[%s] - Reload threads", self.__class__.__name__)
        for th in self._threads:
            th.trigger_reload()

    def reload(self):
        """Reload the server
        """
        logger.info("[%s] - Reload the server", self.__class__.__name__)
        self.stop()
        while len(self._threads)>0:
            self._stopevent.wait(self.loop_sleep*10)
        time.sleep(1.0)
        self.start()

    def flush(self):
        """Flush the server's data to disk
        """
        pass

    def _get_egg_path(self):
        """Return the egg path of the module. Must be redefined in server class.
        """
        raise JanitooNotImplemented('_get_egg_path not implemnted')

    def sigterm_handler(self, signal, frame):
        """Catch SIGTERM signal
        """
        print('TERM signal received : %s' % (signal))
        logger.warning('TERM signal received : %s', signal)
        self.stop()
        sys.exit(0)

    def sighup_handler(self, signal, frame):
        """Catch SIGHUP signal
        """
        print('HUP signal received : %s' % (signal))
        logger.warning('HUP signal received : %s', signal)
        self.reload()
        sys.exit(0)

    def sigusr1_handler(self, signal, frame):
        """Catch SIGUSR1 signal
        The server must flush its data to disk
        The mosquitto broker use it to persist its database to disk.
        """
        print('USR1 signal received : %s' % (signal))
        logger.warning('USR1 signal received : %s', signal)
        self.reload()
        sys.exit(0)

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_DHCPD = 0x1000
COMMAND_CONTROLLER = 0x1050
COMMAND_DISCOVERY = 0x5000

assert(COMMAND_DESC[COMMAND_DISCOVERY] == 'COMMAND_DISCOVERY')
assert(COMMAND_DESC[COMMAND_CONTROLLER] == 'COMMAND_CONTROLLER')
assert(COMMAND_DESC[COMMAND_DHCPD] == 'COMMAND_DHCPD')
##############################################################


class JNTControllerManager(object):
    """A node dedicated for a special thread/server like the the DHCP server or the listener thread in the webapp
    """
    def __init__(self):
        self.mqtt_controller = None
        self._controller = None
        self.heartbeat_controller_timer = None
        self._requests = {'request_info_nodes' : self.request_info_nodes, 'request_info_users' : self.request_info_users, 'request_info_configs' : self.request_info_configs,
                          'request_info_systems' : self.request_info_systems, 'request_info_basics' : self.request_info_basics, 'request_info_commands' : self.request_info_commands }
        self.uuid = self.options.get_option(self.section, 'uuid')
        if self.uuid == None:
            self.uuid = muuid.uuid1()
            self.options.set_option(self.section, 'uuid', '%s'%self.uuid)


    def stop_controller_timer(self):
        """Stop the controller timer
        """
        if self.heartbeat_controller_timer is not None:
            self.heartbeat_controller_timer.cancel()
            self.heartbeat_controller_timer = None

    def start_controller_timer(self):
        """Start the controller tier
        """
        self.stop_controller_timer()
        self.heartbeat_controller_timer = threading.Timer(self._controller.heartbeat+5, self.heartbeat_controller)
        self.heartbeat_controller_timer.start()

    def stop_controller(self):
        """Stop the controller
        """
        logger.info("Stop the controller")
        if self.mqtt_controller is not None:
            self.mqtt_controller.unsubscribe(topic=TOPIC_NODES_REQUEST%(self._controller.hadd))
            self.mqtt_controller.stop()
            if self.mqtt_controller.is_alive():
                try:
                    self.mqtt_controller.join()
                except Exception:
                    logger.exception("Catched exception")
            self.mqtt_controller = None

    def start_controller(self, section, options, **kwargs):
        """Start the controller
        """
        logger.info("Start the controller")
        cmd_classes = kwargs.pop('cmd_classes', [])
        if not COMMAND_CONTROLLER in cmd_classes:
            cmd_classes.append(COMMAND_CONTROLLER)
        self._controller = JNTNode( uuid=section, options=options, cmd_classes=cmd_classes, **kwargs)
        self._controller.add_internal_system_values()
        self._controller.add_internal_config_values()
        self._controller.hadd_get(section, None)
        self._controller.load_system_from_local()
        self.mqtt_controller = MQTTClient(options=options.data)
        self.mqtt_controller.connect()
        logger.debug("[%s] - Subscribe to topic %s", self.__class__.__name__, TOPIC_NODES_REQUEST%(self._controller.hadd))
        self.mqtt_controller.subscribe(topic=TOPIC_NODES_REQUEST%(self._controller.hadd), callback=self.on_controller_request)
        self.mqtt_controller.start()

    def heartbeat_controller(self):
        """Send a add_ctrl:-1 heartbeat message. It will ping all devices managed by this controller.
        """
        logger.debug("[%s] - Send heartbeat for controller", self.__class__.__name__)
        if self.heartbeat_controller_timer is not None:
            #The manager is started
            self.heartbeat_controller_timer.cancel()
            self.heartbeat_controller_timer = None
        self.heartbeat_controller_timer = threading.Timer(self._controller.heartbeat, self.heartbeat_controller)
        self.heartbeat_controller_timer.start()
        if self._controller.hadd is not None:
            #~ print self.nodes[node].hadd
            add_ctrl, add_node = self._controller.split_hadd()
            msg = {'add_ctrl':add_ctrl, 'add_node':add_node, 'state':'ONLINE'}
            self.mqtt_controller.publish_heartbeat_msg(msg)

    def get_controller_hadd(self):
        """Return the controller hadd"""
        if self._controller is None:
            return None
        return self._controller.hadd

    def get_controller(self):
        """Return the controller"""
        return self._controller

    def on_controller_request(self, client, userdata, message):
        """On request

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        logger.debug("on_request receive message %s", message.payload)
        try:
            data = json_loads(message.payload)
            #~ print data['uuid']
            #We should check what value is requested
            #{'hadd', 'cmd_class', 'type'='list', 'genre'='0x04', 'data'='node|value|config', 'uuid'='request_info'}
            if data['cmd_class'] == COMMAND_DISCOVERY:
                if data['genre'] == 0x04:
                    if data['uuid'] in self._requests:
                        resp = {}
                        resp.update(data)
                        try:
                            if message.topic.find('broadcast') != -1:
                                topic = "/broadcast/reply/%s" % data['data']
                                self._requests[data['uuid']](topic, resp)
                            else:
                                topic = "/nodes/%s/reply" % data['data']
                                self._requests[data['uuid']](topic, resp)
                            return
                        except Exception:
                            logger.exception("Exception when running on_request method")
                            return
            logger.warning("Unknown request value %s", data)
        except Exception:
            logger.exception("Exception in on_request")


    def request_info_nodes(self, reply_topic, resp):
        """
        """
        resp['data'] = self._controller.to_dict()
        msg = json_dumps(resp)
        self.publish_request(reply_topic, msg)

    def request_info_users(self, reply_topic, resp):
        """
        """
        resp['data'] = {}
        for kvalue in self._controller.values.keys():
            value = self._controller.values[kvalue]
            if value.genre == 0x02:
                if value.hadd not in resp['data']:
                    resp['data'][value.hadd] = {}
                resp['data'][value.hadd][value.uuid] = value.to_dict()
        msg = json_dumps(resp)
        self.publish_request(reply_topic, msg)

    def request_info_configs(self, reply_topic, resp):
        """
        """
        resp['data'] = {}
        for kvalue in self._controller.values.keys():
            value = self._controller.values[kvalue]
            if value.genre == 0x03:
                if value.hadd not in resp['data']:
                    resp['data'][value.hadd] = {}
                resp['data'][value.hadd][value.uuid] = value.to_dict()
        msg = json_dumps(resp)
        self.publish_request(reply_topic, msg)

    def request_info_basics(self, reply_topic, resp):
        """
        """
        resp['data'] = {}
        for kvalue in self._controller.values.keys():
            value = self._controller.values[kvalue]
            if value.genre == 0x01:
                if value.hadd not in resp['data']:
                    resp['data'][value.hadd] = {}
                resp['data'][value.hadd][value.uuid] = value.to_dict()
        msg = json_dumps(resp)
        self.publish_request(reply_topic, msg)

    def request_info_systems(self, reply_topic, resp):
        """
        """
        resp['data'] = {}
        for kvalue in self._controller.values.keys():
            value = self._controller.values[kvalue]
            if value.genre == 0x04:
                if value.hadd not in resp['data']:
                    resp['data'][value.hadd] = {}
                resp['data'][value.hadd][value.uuid] = value.to_dict()
        msg = json_dumps(resp)
        self.publish_request(reply_topic, msg)

    def request_info_commands(self, reply_topic, resp):
        """
        """
        resp['data'] = {}
        for kvalue in self._controller.values.keys():
            value = self._controller.values[kvalue]
            if value.genre == 0x04:
                if value.hadd not in resp['data']:
                    resp['data'][value.hadd] = {}
                resp['data'][value.hadd][value.uuid] = value.to_dict()
        msg = json_dumps(resp)
        self.publish_request(reply_topic, msg)

    def publish_request(self, reply_topic, msg):
        """
        """
        self.mqtt_controller.publish(topic=reply_topic, payload=msg)

