# -*- coding: utf-8 -*-
"""The Node

about the pollinh mechanism :
 - simplest way to do it : define a poll_thread_timer for every value that needed to publish its data
 - Add a kind of polling queue that will launch the method to get and publish the value

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

import datetime
import threading
import random

from janitoo.fsm import State, Machine
import janitoo.value
from janitoo.value_factory import JNTValueFactoryEntry
from janitoo.utils import HADD, HADD_SEP, json_dumps, json_loads
from janitoo.utils import TOPIC_NODES, TOPIC_NODES_REPLY, TOPIC_NODES_REQUEST
from janitoo.utils import TOPIC_BROADCAST_REPLY, TOPIC_BROADCAST_REQUEST
from janitoo.utils import TOPIC_VALUES_USER, TOPIC_VALUES_CONFIG, TOPIC_VALUES_BASIC, TOPIC_VALUES_SYSTEM, TOPIC_HEARTBEAT
from janitoo.mqtt import MQTTClient
from janitoo.options import string_to_bool

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_DISCOVERY = 0x5000
COMMAND_CONFIGURATION = 0x0070

assert(COMMAND_DESC[COMMAND_DISCOVERY] == 'COMMAND_DISCOVERY')
assert(COMMAND_DESC[COMMAND_CONFIGURATION] == 'COMMAND_CONFIGURATION')
##############################################################

class JNTNodeMan(object):
    """The node manager
    """

    fsm_states = [
        State(name='NEW'),
        State(name='BOOT', on_enter=['start_controller_uuid', 'start_heartbeat_sender'], on_exit=['stop_controller_uuid']),
        State(name='SYSTEM', on_enter=['start_controller_reply', 'start_controller_reply_system']),
        State(name='CONFIG', on_enter=['start_controller_reply_config']),
        State(name='INIT', on_enter=['start_nodes_init'], on_exit=['stop_boot_timer', 'stop_controller_reply']),
        State(name='ONLINE',
                on_enter=['start_broadcast_request', 'start_nodes_request', 'start_hourly_timer'],
                on_exit=['stop_broadcast_request', 'stop_nodes_request']),
        State(name='OFFLINE',
                on_enter=['stop_boot_timer', 'stop_hourly_timer',
                    'stop_heartbeat_sender', 'stop_controller_uuid',
                    'stop_controller_reply','stop_broadcast_request',
                    'stop_nodes_request']),
    ]

    states_str = {
        'BOOT' : "The nodes are booting",
        'SYSTEM' : "Configuring the nodes (system)",
        'CONFIG' : "Configuring the nodes",
        'INIT' : "Initialising the nodes",
        'ONLINE' : "The nodes are online",
        'OFFLINE' : "The nodes are offline",
    }

    def __init__(self, options, section, thread_uuid, **kwargs):
        """
        """
        self.options = options
        self._test = kwargs.get('test', False)
        """For tests only"""
        self.loop_sleep = 0.05
        self.nodes = {}
        self.polls = {}
        self.heartbeats = {}
        self.section = section
        self.thread_uuid = thread_uuid
        self.mqtt_nodes = None
        self.mqtt_nodes_lock = threading.Lock()
        self.mqtt_controller_reply = None
        self.mqtt_controller_reply_lock = threading.Lock()
        self.mqtt_controller_uuid = None
        self.mqtt_controller_uuid_lock = threading.Lock()
        self.mqtt_broadcast = None
        self.mqtt_broadcast_lock = threading.Lock()
        self.mqtt_heartbeat = None
        self.mqtt_heartbeat_lock = threading.Lock()
        self.request_controller_system_response = False
        self.request_controller_config_response = False
        self.request_controller_uuid_response = False
        self.request_nodes_system_response = False
        self.nodes_system_response = None
        self.request_nodes_hadds_response = False
        self.nodes_hadds_response = None
        self.request_nodes_config_response = False
        self.nodes_config_response = None
        self.config_timeout = 3
        self.slow_start = 0.05
        self._controller = None
        self._controller_hadd = None
        self._requests = {'request_info_nodes' : self.request_info_nodes,
                          'request_info_users' : self.request_info_users,
                          'request_info_configs' : self.request_info_configs,
                          'request_info_systems' : self.request_info_systems,
                          'request_info_basics' : self.request_info_basics,
                          'request_info_commands' : self.request_info_commands }
        self.fsm_state = None
        self.state = "OFFLINE"
        self.trigger_reload = None
        self.hourly_timer = None
        self._hourly_jobs = None
        self._daily_jobs = None

        self.request_boot_timer = None
        self.request_boot_timer_lock = threading.Lock()

    def __del__(self):
        """
        """
        try:
            self.stop()
            self._hourly_jobs = None
            self._daily_jobs = None
        except Exception:
            pass

    def start(self, trigger_reload=None, loop_sleep=0.1, slow_start=0.05):
        """
        """
        if trigger_reload is not None:
            self.trigger_reload = trigger_reload
        self.loop_sleep = loop_sleep
        self.fsm_state = self.create_fsm()
        self.fsm_state_start()
        self._hourly_jobs = []
        self._daily_jobs = []
        self.slow_start = slow_start

    def create_fsm(self):
        """
        """
        fsm_state = Machine(model=self, states=self.fsm_states, initial='OFFLINE')
        fsm_state.add_ordered_transitions()
        fsm_state.add_transition('fsm_state_start', 'OFFLINE', 'BOOT')
        fsm_state.add_transition('fsm_state_next', 'BOOT', 'SYSTEM')
        fsm_state.add_transition('fsm_state_next', 'SYSTEM', 'CONFIG')
        fsm_state.add_transition('fsm_state_next', 'CONFIG', 'INIT')
        fsm_state.add_transition('fsm_state_next', 'INIT','ONLINE')
        fsm_state.add_transition('fsm_state_stop', '*', 'OFFLINE', after=['after_fsm_stop']
        )
        return fsm_state

    def stop(self):
        """
        """
        self.fsm_state_stop()
        self.stop_hourly_timer()
        self.stop_heartbeat_sender()
        self.stop_controller_uuid()
        self.stop_controller_reply()
        self.stop_broadcast_request()
        self.stop_nodes_request()
        self.stop_boot_timer()

    def after_fsm_stop(self):
        """
        """
        self.nodes = {}
        self.polls = {}
        self.heartbeats = {}
        self.fsm_state = None
        self._hourly_jobs = []
        self.state = "OFFLINE"

    @property
    def is_stopped(self):
        """Return True if the network is stopped
        """
        return self.fsm_state is None or self.state == "OFFLINE"

    @property
    def is_started(self):
        """Return True if the network is started
        """
        return self.state == "ONLINE"

    def start_heartbeat_sender(self):
        """
        """
        logger.debug("fsm_state : %s", 'start_heartbeat_sender')
        if self._test:
            print "start_heartbeat_sender"
        else:
            if self.mqtt_heartbeat is None:
                self.mqtt_heartbeat_lock.acquire()
                if self.is_stopped:
                    return
                try:
                    self.mqtt_heartbeat = MQTTClient(options=self.options.data)
                    self.mqtt_heartbeat.connect()
                    self.mqtt_heartbeat.start()
                except Exception:
                    logger.exception("[%s] - start_heartbeat_sender", self.__class__.__name__)
                finally:
                    self.mqtt_heartbeat_lock.release()

    def stop_heartbeat_sender(self):
        """
        """
        logger.debug("fsm_state : %s", 'stop_heartbeat_seander')
        if self._test:
            print "stop_heartbeat_seander"
        else:
            if self.mqtt_heartbeat is not None:
                self.mqtt_heartbeat_lock.acquire()
                for node in self.nodes:
                    if self.nodes[node].hadd is not None:
                        add_ctrl, add_node = self.nodes[node].split_hadd()
                        self.mqtt_heartbeat.publish_heartbeat(int(add_ctrl), int(add_node), 'OFFLINE')
                try:
                    self.mqtt_heartbeat.stop()
                    if self.mqtt_heartbeat.is_alive():
                        self.mqtt_heartbeat.join()
                except Exception:
                    logger.exception("[%s] - stop_heartbeat_sender", self.__class__.__name__)
                finally:
                    self.mqtt_heartbeat = None
                    self.mqtt_heartbeat_lock.release()

    def start_broadcast_request(self):
        """
        """
        logger.debug("fsm_state : %s", 'start_broadcast_request')
        if self._test:
            print "start_broadcast_request"
        else:
            if self.mqtt_broadcast is None:
                self.mqtt_broadcast_lock.acquire()
                if self.is_stopped:
                    return
                try:
                    self.mqtt_broadcast = MQTTClient(options=self.options.data)
                    self.mqtt_broadcast.connect()
                    self.mqtt_broadcast.subscribe(topic=TOPIC_BROADCAST_REQUEST, callback=self.on_request)
                    self.mqtt_broadcast.start()
                except Exception:
                    logger.exception("[%s] - start_broadcast_request", self.__class__.__name__)
                finally:
                    self.mqtt_broadcast_lock.release()

    def stop_broadcast_request(self):
        """
        """
        logger.debug("fsm_state : %s", 'stop_broadcast_request')
        if self._test:
            print "stop_broadcast_request"
        else:
            if self.mqtt_broadcast is not None:
                self.mqtt_broadcast_lock.acquire()
                try:
                    self.mqtt_broadcast.unsubscribe(topic=TOPIC_BROADCAST_REQUEST)
                    self.mqtt_broadcast.stop()
                    if self.mqtt_broadcast.is_alive():
                        self.mqtt_broadcast.join()
                except Exception:
                    logger.exception("[%s] - stop_broadcast_request", self.__class__.__name__)
                finally:
                    self.mqtt_broadcast = None
                    self.mqtt_broadcast_lock.release()

    def start_nodes_request(self):
        """
        """
        logger.debug("fsm_state : %s", 'start_nodes_request')
        if self._test:
            print "start_nodes_request"
        else:
            if self.mqtt_nodes is None:
                if self.is_stopped:
                    return
                self.mqtt_nodes_lock.acquire()
                try:
                    self.mqtt_nodes = MQTTClient(options=self.options.data)
                    self.mqtt_nodes.connect()
                    add_ctrl, add_node = self._controller.split_hadd()
                    logger.debug("[%s] - Subscribe to topic %s", self.__class__.__name__, TOPIC_NODES%("%s/#"%add_ctrl))
                    self.mqtt_nodes.subscribe(topic=TOPIC_NODES%("%s/#"%add_ctrl), callback=self.on_generic_request)
                    self.mqtt_nodes.start()
                    logger.debug("[%s] - Add topic %s", self.__class__.__name__, TOPIC_NODES_REQUEST%(self._controller_hadd))
                    self.mqtt_nodes.add_topic(topic=TOPIC_NODES_REQUEST%(self._controller_hadd), callback=self.on_request)
                    for node in self.nodes:
                        if self.nodes[node] != self._controller:
                            logger.debug("[%s] - Add topic %s", self.__class__.__name__, TOPIC_NODES_REQUEST%(self.nodes[node].hadd))
                            self.mqtt_nodes.add_topic(topic=TOPIC_NODES_REQUEST%(self.nodes[node].hadd), callback=self.on_request)
                except Exception:
                    logger.exception("[%s] - start_nodes_request", self.__class__.__name__)
                finally:
                    self.mqtt_nodes_lock.release()

    def stop_nodes_request(self):
        """
        """
        logger.debug("fsm_state : %s", 'stop_nodes_request')
        if self._test:
            print "stop_nodes_request"
        else:
            if self.mqtt_nodes is not None:
                self.mqtt_nodes_lock.acquire()
                try:
                    for node in self.nodes:
                        self.mqtt_nodes.remove_topic(topic=TOPIC_NODES_REQUEST%(self.nodes[node].hadd))
                    self.mqtt_nodes.remove_topic(topic=TOPIC_NODES_REQUEST%(self._controller_hadd))
                    add_ctrl, add_node = self._controller.split_hadd()
                    self.mqtt_nodes.unsubscribe(topic=TOPIC_NODES%("%s/#"%add_ctrl))
                    self.mqtt_nodes.stop()
                    if self.mqtt_nodes.is_alive():
                        self.mqtt_nodes.join()
                except Exception:
                    logger.exception("[%s] - stop_nodes_request", self.__class__.__name__)
                finally:
                    self.mqtt_nodes = None
                    self.mqtt_nodes_lock.release()

    def start_controller_reply(self):
        """
        """
        logger.debug("fsm_state : %s", 'start_controller_reply')
        if self._test:
            print "start_controller_reply"
        else:
            if self.is_stopped:
                return
            if self.mqtt_controller_reply is None:
                self.mqtt_controller_reply_lock.acquire()
                try:
                    pass
                    #~ self.mqtt_controller_reply = MQTTClient(options=self.options.data)
                    #~ self.mqtt_controller_reply.connect()
                    #~ self.mqtt_controller_reply.subscribe(topic=TOPIC_NODES_REPLY%(self._controller.hadd), callback=self.on_reply)
                    #~ self.mqtt_controller_reply.start()
                except Exception:
                    logger.exception("[%s] - start_controller_reply", self.__class__.__name__)
                finally:
                    self.mqtt_controller_reply_lock.release()

    def stop_controller_reply(self):
        """
        """
        logger.debug("fsm_state : %s", 'stop_controller_reply')
        if self._test:
            print "stop_controller_reply"
        else:
            if self.mqtt_controller_reply is not None:
                self.mqtt_controller_reply_lock.acquire()
                try:
                    self.mqtt_controller_reply.unsubscribe(topic=TOPIC_NODES_REPLY%(self._controller_hadd))
                    self.mqtt_controller_reply.stop()
                    if self.mqtt_controller_reply.is_alive():
                        self.mqtt_controller_reply.join()
                except Exception:
                    logger.exception("[%s] - stop_controller_reply", self.__class__.__name__)
                finally:
                    self.mqtt_controller_reply = None
                    self.mqtt_controller_reply_lock.release()

    def start_controller_uuid(self):
        """
        """
        logger.debug("fsm_state : %s", 'start_controller_uuid')
        if self._test:
            print "start_controller_uuid"
        else:
            if self.is_stopped:
                return
            if self.mqtt_controller_uuid is None:
                self.mqtt_controller_uuid_lock.acquire()
                try:
                    pass
                    #~ self.mqtt_controller_uuid = MQTTClient(options=self.options.data)
                    #~ self.mqtt_controller_uuid.connect()
                    #~ self.mqtt_controller_uuid.subscribe(topic=TOPIC_NODES_REPLY%(self._controller_hadd), callback=self.on_reply_uuid)
                    #~ self.mqtt_controller_uuid.start()
                except Exception:
                    logger.exception("[%s] - start_controller_uuid", self.__class__.__name__)
                finally:
                    self.mqtt_controller_uuid_lock.release()
            self.request_boot_timer_lock.acquire()
            try:
                self._stop_boot_timer()
                if self.is_stopped:
                    return
                self.request_boot_timer = threading.Timer(self.config_timeout+self.slow_start, self.finish_controller_uuid)
                self.request_boot_timer.start()
            finally:
                self.request_boot_timer_lock.release()

    def finish_controller_uuid(self):
        """
        """
        logger.debug("fsm_state : %s in state %s", 'finish_controller_uuid', self.state)
        if self.is_stopped:
            return
        self.request_boot_timer_lock.acquire()
        try:
            self._stop_boot_timer()
            if self.is_stopped:
                return
            if not self.request_controller_uuid_response:
                #retrieve hadd from local configuration
                controller = self.create_controller_node()
                self.add_controller_node(controller.uuid, controller)
                self._controller.hadd_get(controller.uuid, None)
                self._controller_hadd = self._controller.hadd
                self.add_heartbeat(self._controller)
                logger.debug("[%s] - Added controller node with uuid %s and hadd %s", self.__class__.__name__, self._controller.uuid, self._controller_hadd)
                #~ print self._controller.__dict__
                #~ print self.config_timeout
        except Exception:
            logger.exception("[%s] - finish_controller_uuid", self.__class__.__name__)
        finally:
            self.request_boot_timer_lock.release()
        if not self.is_stopped:
            self.fsm_state_next()

    def stop_controller_uuid(self):
        """
        """
        logger.debug("fsm_state : %s in state %s", 'stop_controller_uuid', self.state)
        if self._test:
            print "stop_controller_uuid"
        else:
            if self.mqtt_controller_uuid is not None:
                self.mqtt_controller_uuid_lock.acquire()
                try:
                    self.mqtt_controller_uuid.unsubscribe(topic=TOPIC_NODES_REPLY%(self._controller_hadd))
                    self.mqtt_controller_uuid.stop()
                    if self.mqtt_controller_uuid.is_alive():
                        self.mqtt_controller_uuid.join()
                except Exception:
                    logger.exception("[%s] - stop_controller_uuid", self.__class__.__name__)
                finally:
                    self.mqtt_controller_uuid = None
                    self.mqtt_controller_uuid_lock.release()

    def start_controller_reply_system(self):
        """
        """
        logger.debug("fsm_state : %s", 'start_controller_reply_system')
        if self._test:
            print "start_controller_reply_system"
        else:
            if self.is_stopped:
                return
            self.request_boot_timer_lock.acquire()
            try:
                self._stop_boot_timer()
                if self.is_stopped:
                    return
                self.request_boot_timer = threading.Timer(self.config_timeout+self.slow_start, self.finish_controller_reply_system)
                self.request_boot_timer.start()
            finally:
                self.request_boot_timer_lock.release()

    def stop_boot_timer(self):
        """
        """
        self.request_boot_timer_lock.acquire()
        try:
            self._stop_boot_timer()
        finally:
            self.request_boot_timer_lock.release()

    def _stop_boot_timer(self):
        """
        """
        if self.request_boot_timer is not None:
            self.request_boot_timer.cancel()
            self.request_boot_timer = None

    def after_controller_reply_system(self):
        """
        """
        pass

    def finish_controller_reply_system(self):
        """
        """
        logger.debug("fsm_state : %s in state %s", 'finish_controller_reply_system', self.state)
        if self.is_stopped:
            return
        self.request_boot_timer_lock.acquire()
        try:
            self._stop_boot_timer()
            if self.is_stopped:
                return
            if not self.request_controller_system_response:
                self._controller.load_system_from_local()
            self.config_timeout = self._controller.config_timeout
            self.request_controller_controller_system_response = False
            self.after_controller_reply_system()
        finally:
            self.request_boot_timer_lock.release()
        if not self.is_stopped:
            self.fsm_state_next()

    def after_controller_reply_config(self):
        """
        """
        pass

    def start_controller_reply_config(self):
        """
        """
        logger.debug("fsm_state : %s", 'start_controller_reply_config')
        if self._test:
            print "start_controller_reply_config"
        else:
            if self.is_stopped:
                return
            self.request_boot_timer_lock.acquire()
            try:
                self._stop_boot_timer()
                if self.is_stopped:
                    return
                self.request_boot_timer = threading.Timer(self.config_timeout+self.slow_start, self.finish_controller_reply_config)
                self.request_boot_timer.start()
            finally:
                self.request_boot_timer_lock.release()

    def before_controller_reply_config(self):
        """
        """
        pass

    def after_create_node(self, uuid):
        """After the node is created
        """
        pass

    def after_system_node(self, uuid):
        """After the node system
        """
        pass

    def after_config_node(self, uuid):
        """After the node config
        """
        pass

    def finish_controller_reply_config(self):
        """
        """
        logger.debug("fsm_state : %s in state %s", 'finish_reply_config', self.state)
        if self.is_stopped:
            return
        self.request_boot_timer_lock.acquire()
        try:
            self._stop_boot_timer()
            if self.is_stopped:
                return
            self.before_controller_reply_config()
            if not self.request_controller_config_response:
                self._controller.load_config_from_local()
            self.request_controller_config_response = False
            self.after_controller_reply_config()
        finally:
            self.request_boot_timer_lock.release()
        if not self.is_stopped:
            self.fsm_state_next()

    def start_nodes_init(self):
        """
        """
        logger.debug("fsm_state : %s", 'start_nodes_init')
        if self._test:
            print "start_nodes_init"
        else:
            if self.is_stopped:
                return
            self.request_boot_timer_lock.acquire()
            if self.is_stopped:
                return
            try:
                self.request_boot_timer = threading.Timer(self.config_timeout+self.slow_start, self.finish_nodes_hadds)
                self.request_boot_timer.start()
            finally:
                self.request_boot_timer_lock.release()

    def finish_nodes_hadds(self):
        """
        """
        logger.debug("fsm_state : %s in state %s", 'finish_nodes_hadds', self.state)
        logger.debug("finish_nodes_hadds : nodes = %s", self.nodes)
        #~ print "self.request_nodes_hadds_response ", self.request_nodes_hadds_response
        if self.is_stopped:
            return
        self.request_boot_timer_lock.acquire()
        try:
            self._stop_boot_timer()
            if self.is_stopped:
                return
            if not self.request_nodes_hadds_response:
                self.nodes_hadds_response = self.get_nodes_hadds_from_local_config()
                logger.debug("finish_nodes_hadds : nodes_hadds_response = %s", self.nodes_hadds_response)
                for node in self.nodes_hadds_response:
                    self.create_node(node, hadd=self.nodes_hadds_response[node])
                    self.after_create_node(node)
                    #~ print onode.__dict__
            self.request_boot_timer = threading.Timer(self.config_timeout+self.slow_start, self.finish_nodes_system)
            self.request_boot_timer.start()
        finally:
            self.request_boot_timer_lock.release()

    def finish_nodes_system(self):
        """
        """
        logger.debug("fsm_state : %s in state %s", 'finish_nodes_system', self.state)
        logger.debug("finish_nodes_system : nodes = %s", self.nodes)
        if self.is_stopped:
            return
        self.request_boot_timer_lock.acquire()
        try:
            self._stop_boot_timer()
            if self.is_stopped:
                return
            if not self.request_nodes_system_response:
                for node in self.nodes:
                    if node != self._controller.uuid and not self.is_stopped:
                        onode = self.nodes[node]
                        onode.load_system_from_local()
                        self.after_system_node(node)
                        #~ print onode.__dict__
            self.request_boot_timer = threading.Timer(self.config_timeout+self.slow_start, self.finish_nodes_config)
            self.request_boot_timer.start()
        finally:
            self.request_boot_timer_lock.release()

    def finish_nodes_config(self):
        """
        """
        logger.debug("fsm_state : %s in state %s", 'finish_nodes_config', self.state)
        logger.debug("finish_nodes_config : nodes = %s", self.nodes)
        #~ print "self.request_nodes_hadds_response ", self.request_nodes_config_response
        if self.is_stopped:
            return
        self.request_boot_timer_lock.acquire()
        try:
            self._stop_boot_timer()
            if self.is_stopped:
                return
            if not self.request_nodes_config_response:
                for node in self.nodes:
                    if node != self._controller.uuid and not self.is_stopped:
                        onode = self.nodes[node]
                        onode.load_config_from_local()
                        self.after_config_node(node)
        finally:
            self.request_boot_timer_lock.release()
        if not self.is_stopped:
            self.add_heartbeat(self._controller)
            self.fsm_state_next()

    def on_reply(self, client, userdata, message):
        """On request

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        pass

    def on_generic_request(self, client, userdata, message):
        """On request

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        pass

    def on_request(self, client, userdata, message):
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
                                topic = "/broadcast/reply/%s" % data['reply_hadd']
                                self._requests[data['uuid']](topic, resp)
                            else:
                                topic = "/nodes/%s/reply" % data['reply_hadd']
                                self._requests[data['uuid']](topic, resp)
                            return
                        except Exception:
                            logger.exception("Exception when running on_request method")
                            return
            elif data['cmd_class'] == COMMAND_CONFIGURATION:
                #print "message %s" % message
                if 'reply_hadd' not in data:
                    logger.warning("No reply_hadd in message %s", message)
                logger.debug("on_request COMMAND_CONFIGURATION message %s,%s", message.topic, message.payload)
                node = self.get_node_from_hadd(data['hadd'])
                #~ print node.values
                if data['genre'] == 0x04:
                    #print "message %s" % message
                    if data['uuid'] in node.values:
                        read_only = True
                        write_only = False
                        try:
                            read_only = string_to_bool(data['is_readonly'])
                        except KeyError:
                            pass
                        except ValueError:
                            pass
                        try:
                            write_only = string_to_bool(data['is_writeonly'])
                        except KeyError:
                            pass
                        except ValueError:
                            pass
                        if write_only:
                            node.values[data['uuid']].data = data['data']
                            if data['uuid'] == "heartbeat":
                                self.add_heartbeat(node)
                            data['is_writeonly'] = False
                            data['is_readonly'] = True
                        elif read_only:
                            data['data'] = node.values[data['uuid']].data
                        data['label'] = node.values[data['uuid']].label
                        data['help'] = node.values[data['uuid']].help
                        msg = json_dumps(data)
                        topic = TOPIC_VALUES_SYSTEM % ("%s/%s" % (data['hadd'], data['uuid']))
                        self.publish_request(topic, msg)
                        return
                elif data['genre'] == 0x03:
                    #print "message %s" % message
                    #~ print node.values
                    if data['uuid'] in node.values:
                        read_only = True
                        write_only = False
                        try:
                            read_only = string_to_bool(data['is_readonly'])
                        except KeyError:
                            pass
                        except ValueError:
                            pass
                        try:
                            write_only = string_to_bool(data['is_writeonly'])
                        except KeyError:
                            pass
                        except ValueError:
                            pass
                        if write_only:
                            node.values[data['uuid']].data = data['data']
                            data['is_writeonly'] = False
                            data['is_readonly'] = True
                        elif read_only:
                            data['data'] = node.values[data['uuid']].data
                            data['is_writeonly'] = False
                            data['is_readonly'] = True
                        data['label'] = node.values[data['uuid']].label
                        data['help'] = node.values[data['uuid']].help
                        msg = json_dumps(data)
                        topic = TOPIC_VALUES_CONFIG % ("%s/%s" % (data['hadd'], data['uuid']))
                        self.publish_request(topic, msg)
                        return
            else:
                logger.debug("on_request else message %s,%s", message.topic, message.payload)
                node = self.get_node_from_hadd(data['hadd'])
                #~ print node.values
                if data['genre'] == 0x02:
                    #~ print data['cmd_class'], node.values[data['uuid']].cmd_class
                    #~ print node.hadd
                    if data['uuid'] in node.values and data['cmd_class'] == node.values[data['uuid']].cmd_class:
                        res = node.values[data['uuid']].to_dict()
                        res.update(data)
                        data = res
                        read_only = True
                        write_only = False
                        try:
                            read_only = string_to_bool(data['is_readonly'])
                        except KeyError:
                            pass
                        except ValueError:
                            pass
                        try:
                            write_only = string_to_bool(data['is_writeonly'])
                        except KeyError:
                            pass
                        except ValueError:
                            pass
                        if write_only:
                            #~ print "write_only"
                            node.values[data['uuid']].data = data['data']
                            data['is_writeonly'] = False
                            data['is_readonly'] = True
                        elif read_only:
                            #~ print "read_only"
                            data['data'] = node.values[data['uuid']].data
                            data['is_writeonly'] = False
                            data['is_readonly'] = True
                        data['label'] = node.values[data['uuid']].label
                        data['help'] = node.values[data['uuid']].help
                        msg = json_dumps(data)
                        topic = TOPIC_NODES_REPLY % (data['reply_hadd'])
                        self.publish_request(topic, msg)
                        topic = TOPIC_VALUES_USER % ("%s/%s" % (data['hadd'], data['uuid']))
                        self.publish_request(topic, msg)
                        return
            logger.warning("Unknown request value %s", data)
        except Exception:
            logger.exception("Exception in on_request")

    def request_info_nodes(self, reply_topic, resp):
        """
        """
        resp['data'] = {}
        for knode in self.nodes.keys():
            resp['data'][knode] = self.nodes[knode].to_dict()
            ret = self.nodes[knode].check_heartbeat()
            if ret is None :
                state = self.state
            elif ret:
                state = 'ONLINE'
            else:
                state = 'OFFLINE'
            resp['data'][knode]['state'] = state
        logger.debug("request_info_nodes : response data %s", resp['data'])
        msg = json_dumps(resp)
        self.publish_request(reply_topic, msg)

    def request_info_users(self, reply_topic, resp):
        """
        """
        resp['data'] = {}
        i = 0
        for knode in self.nodes.keys():
            for kvalue in self.nodes[knode].values.keys():
                value = self.nodes[knode].values[kvalue]
                if value.genre == 0x02:
                    if value.hadd not in resp['data']:
                        resp['data'][value.hadd] = {}
                    if value.uuid not in resp['data'][value.hadd]:
                        resp['data'][value.hadd][value.uuid] = {}
                    if isinstance(value, JNTValueFactoryEntry) and value.get_max_index() > 0:
                        for i in range(0, value.get_max_index() + 1 ):
                            resp['data'][value.hadd][value.uuid][i] = value.to_dict_with_index(i)
                    else:
                        resp['data'][value.hadd][value.uuid][0] = value.to_dict()
        logger.debug("request_info_users : response data %s", resp['data'])
        msg = json_dumps(resp)
        self.publish_request(reply_topic, msg)

    def request_info_configs(self, reply_topic, resp):
        """
        """
        resp['data'] = {}
        for knode in self.nodes.keys():
            for kvalue in self.nodes[knode].values.keys():
                value = self.nodes[knode].values[kvalue]
                if value.genre == 0x03:
                    if value.hadd not in resp['data']:
                        resp['data'][value.hadd] = {}
                    if value.uuid not in resp['data'][value.hadd]:
                        resp['data'][value.hadd][value.uuid] = {}
                    if value.master_config_value is not None and value.master_config_value.get_max_index() > 0 :
                        for i in range(0, value.master_config_value.get_max_index() + 1 ) :
                            resp['data'][value.hadd][value.uuid][i] = value.to_dict()
                            resp['data'][value.hadd][value.uuid][i]['index'] = i
                            resp['data'][value.hadd][value.uuid][i]['data'] = value.master_config_value.get_config(value.node_uuid, i)
                    else:
                        resp['data'][value.hadd][value.uuid][0] = value.to_dict()
        logger.debug("request_info_configs : response data %s", resp['data'])
        msg = json_dumps(resp)
        self.publish_request(reply_topic, msg)

    def request_info_basics(self, reply_topic, resp):
        """
        """
        resp['data'] = {}
        for knode in self.nodes.keys():
            for kvalue in self.nodes[knode].values.keys():
                value = self.nodes[knode].values[kvalue]
                if value.genre == 0x01:
                    if value.hadd not in resp['data']:
                        resp['data'][value.hadd] = {}
                    if value.uuid not in resp['data'][value.hadd]:
                        resp['data'][value.hadd][value.uuid] = {}
                    #~ if value.master_config_value is not None and value.master_config_value.get_max_index() > 0 :
                        #~ for i in range(0, value.master_config_value.get_max_index() + 1 ) :
                            #~ resp['data'][value.hadd][value.uuid][i] = value.to_dict()
                            #~ resp['data'][value.hadd][value.uuid][i]['index'] = i
                            #~ resp['data'][value.hadd][value.uuid][i]['data'] = value.master_config_value.get_config(value.node_uuid, i)
                    #~ else:
                        #~ resp['data'][value.hadd][value.uuid][0] = value.to_dict()
                    if isinstance(value, JNTValueFactoryEntry) and value.get_max_index() > 0:
                        for i in range(0, value.get_max_index() + 1 ):
                            resp['data'][value.hadd][value.uuid][i] = value.to_dict_with_index(i)
                    else:
                        resp['data'][value.hadd][value.uuid][0] = value.to_dict()
        logger.debug("request_info_basics : response data %s", resp['data'])
        msg = json_dumps(resp)
        self.publish_request(reply_topic, msg)

    def request_info_systems(self, reply_topic, resp):
        """
        """
        resp['data'] = {}
        for knode in self.nodes.keys():
            for kvalue in self.nodes[knode].values.keys():
                value = self.nodes[knode].values[kvalue]
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
        for knode in self.nodes.keys():
            for kvalue in self.nodes[knode].values.keys():
                value = self.nodes[knode].values[kvalue]
                if value.genre == 0x05:
                    if value.hadd not in resp['data']:
                        resp['data'][value.hadd] = {}
                    resp['data'][value.hadd][value.uuid] = value.to_dict()
        msg = json_dumps(resp)
        self.publish_request(reply_topic, msg)

    def publish_request(self, reply_topic, msg):
        """
        """
        self.mqtt_broadcast.publish(topic=reply_topic, payload=msg)

    def loop(self, stopevent):
        """
        """
        if not self.is_started:
            return
        to_polls = []
        nodes = self.polls.keys()
        for node in nodes:
            for key in self.polls[node]:
                if self.polls[node][key]['next_run'] < datetime.datetime.now():
                    to_polls.append(self.polls[node][key]['value'])
        if len(to_polls)>0:
            logger.debug('[%s] - Found polls in timeout : [ %s ]', self.__class__.__name__, ', '.join(str(e.uuid) for e in to_polls))
        for value in to_polls:
            self.publish_poll(self.mqtt_nodes, value, stopevent)
            stopevent.wait(0.1)
        to_heartbeats = []
        keys = self.heartbeats.keys()
        for node in keys:
            if self.heartbeats[node]['next_run'] < datetime.datetime.now():
                to_heartbeats.append(node)
        if len(to_heartbeats)>0:
            logger.debug('[%s] - Found heartbeats in timeout : %s', self.__class__.__name__, to_heartbeats)
            self.heartbeat(to_heartbeats, self.mqtt_heartbeat, stopevent)
        try:
            sleep = float(self.loop_sleep) - 0.02*len(to_polls) - 0.02*len(to_heartbeats)
        except ValueError:
            sleep = 0.05
        if sleep<0:
            sleep=0.05
        stopevent.wait(sleep)

    def heartbeat(self, nodes, mqttc=None, stopevent=None):
        """Send a add_ctrl:-1 heartbeat message. It will ping all devices managed by this controller.
        """
        for node in nodes:
            self.add_heartbeat(self.nodes[node])
            logger.debug('[%s] - Try to send heartbeat for node %s with hadd %s', self.__class__.__name__, node, self.nodes[node].hadd)
            if self.nodes[node].hadd is not None:
                #~ print self.nodes[node].hadd
                add_ctrl, add_node = self.nodes[node].split_hadd()
                ret = self.nodes[node].check_heartbeat()
                if ret is None :
                    state = self.state
                elif ret == True:
                    state = 'ONLINE'
                else:
                    state = 'OFFLINE'
                #~ print "node : %s/%s, state : %s"%(add_ctrl, add_node, state)
                #~ msg = {'add_ctrl':add_ctrl, 'add_node':add_node, 'state':state}
                mqt = mqttc if mqttc is not None else self.mqtt_heartbeat
                if mqt is not None:
                    mqt.publish_heartbeat(int(add_ctrl), int(add_node), state)
                if stopevent is not None:
                    stopevent.wait(0.02)

    def publish_poll(self, mqttc, value, stopevent=None):
        """
        """
        node = self.nodes[value.node_uuid]
        mqt = mqttc if mqttc is not None else self.mqtt_nodes
        genres = {1:'basic', 2:'user', 3:'config', }
        if value.genre in genres:
            genre = genres[value.genre]
        else:
            genre = "user"
        if mqt is not None:
            mqt.publish_value(node.hadd, value, genre)
            self.add_poll(value)
        else:
            self.add_poll(value, timeout=self.config_timeout+self.slow_start)

    def add_controller_node(self, uuid, node):
        """
        """
        if uuid not in self.nodes:
            logger.debug("[%s] - Add controller node with uuid %s and hadd %s", self.__class__.__name__, uuid, node.hadd)
            self.nodes[uuid] = node
            self._controller = node
            self._controller_hadd = node.hadd
            node.options = self.options
            self.add_internal_system_values_to_node(node)
            self.add_internal_config_values_to_node(node)
            return True
        else:
            return False

    def create_controller_node(self, **kwargs):
        """
        """
        return JNTNode(options=self.options, **kwargs)

    def create_node(self, uuid, **kwargs):
        """
        """
        node = JNTNode(uuid=uuid, options=self.options, **kwargs)
        self.add_node(node.uuid, node)
        return node

    def get_controller_node(self):
        """
        """
        return self._controller

    def get_node_from_hadd(self, hadd):
        """
        """
        for nid in self.nodes.keys():
            if self.nodes[nid].hadd == hadd:
                return self.nodes[nid]
        return None

    def get_node_from_uuid(self, uuid):
        """
        """
        if uuid in self.nodes:
            return self.nodes[uuid]
        return None

    def get_add_ctrl(self):
        """
        """
        add_ctrl, add_node = self._controller_hadd.split(HADD_SEP)
        return int(add_ctrl)

    def get_nodes_hadds_from_local_config(self):
        """ {'uuid':'hadd'}
        """
        return {}

    def get_components(self):
        """Retrieve components from a section
        """
        return self.options.get_options_key(self.section, "components.")

    def add_node(self, uuid, node):
        """
        """
        if uuid not in self.nodes:
            logger.debug("[%s] - Add node with uuid %s", self.__class__.__name__, uuid)
            self.nodes[uuid] = node
            if node.hadd is not None:
                self.add_heartbeat(node)
            node.options = self.options
            self.add_internal_system_values_to_node(node)
            self.add_internal_config_values_to_node(node)
            return True
        else:
            return False

    def add_internal_system_values_to_node(self, node):
        """
        """
        node.add_internal_system_values()

    def add_internal_config_values_to_node(self, node):
        """
        """
        node.add_internal_config_values()

    def add_value_to_node(self, uuid, node, value):
        """
        """
        if node.uuid not in self.nodes or uuid in self.nodes[node.uuid].values:
            return False
        node.add_value(uuid, value)
        if value.is_polled and not value.is_writeonly:
            self.add_poll(value)
        if value.cmd_class not in self.nodes[node.uuid].cmd_classes:
            self.nodes[node.uuid].cmd_classes.append(value.cmd_class)
        return True

    def is_polled(self, value):
        """Is the value poll active (in the polling system)
        """
        if value.hadd not in self.polls:
            return False
        if value.uuid not in self.polls[value.hadd]:
            return False

    def add_poll(self, value, timeout=None, overwrite=True):
        """Add a value to the polling system
        """
        if value is None:
            return
        if value.poll_delay == 0:
            self.remove_poll(value)
            return
        if value.hadd not in self.polls:
            self.polls[value.hadd] = {}
        if value.uuid not in self.polls[value.hadd] or timeout:
            if timeout is None:
                timeout = self.config_timeout
            self.polls[value.hadd][value.uuid] = {'next_run':datetime.datetime.now()+datetime.timedelta(seconds=timeout+random.random()*(1+self.slow_start)), 'value':value}
            value.is_polled = True
        elif overwrite:
            self.polls[value.hadd][value.uuid]['next_run'] = datetime.datetime.now()+datetime.timedelta(seconds=value.poll_delay)
            value.is_polled = True

    def add_polls(self, values, timeout=None, slow_start=False, overwrite=True):
        """Add values to the polling system
        """
        if timeout is None:
            timeout = 0
        if slow_start:
            slow_start = 1 + self.slow_start
        else:
            slow_start = 0.1
        i = 0
        for value in values:
            self.add_poll(value, timeout=slow_start * i + timeout, overwrite=overwrite)
            i += 1

    def remove_polls(self, values):
        """Remove polls from polling system
        """
        for value in values:
            self.remove_poll(value)

    def remove_poll(self, value):
        """Remove poll from polling system
        """
        if value and value.hadd in self.polls and value.uuid in self.polls[value.hadd]:
            #~ value.is_polled= False
            del self.polls[value.hadd][value.uuid]
        if value and value.hadd in self.polls and len(self.polls[value.hadd]) == 0:
            del self.polls[value.hadd]

    def add_heartbeat(self, node):
        """Add a node to the heartbeat system
        """
        #~ print "heartbeats = %s" % self.heartbeats
        if node.uuid not in self.heartbeats:
            self.heartbeats[node.uuid] = {'next_run':datetime.datetime.now()+datetime.timedelta(seconds=self.config_timeout+random.random()*(1+self.slow_start))}
        else:
            self.heartbeats[node.uuid]['next_run'] = datetime.datetime.now()+datetime.timedelta(seconds=node.heartbeat)

    def remove_heartbeat(self, node):
        """Remove a node from the heartbeat system
        """
        if node.uuid in self.heartbeats:
            del self.heartbeats[node.uuid]

    def find_nodes(self, node_oid):
        """Find a node usinf its uuid
        """
        nodes = [ self.nodes[node] for node in self.nodes if self.nodes[node].oid == node_oid ]
        return nodes

    def find_node(self, node_uuid):
        """Find a node using its uuid
        """
        nuuid='%s__%s'%(self.section, node_uuid)
        #~ nuuid=node_uuid
        nodes = [ self.nodes[node] for node in self.nodes if self.nodes[node].uuid == nuuid ]
        if len(nodes)>1:
            logger.warning("[%s] - Found 2 nodes %s with uuid %s. Returning the fisrt one.", self.__class__.__name__, nodes, node_uuid)
        if len(nodes)==0:
            return None
        return nodes[0]

    def find_value(self, node_uuid, value_uuid):
        """Find a value using its uuid and the node one
        """
        nuuid='%s__%s'%(self.section, node_uuid)
        #~ nuuid=node_uuid
        nodes = [ self.nodes[node] for node in self.nodes if self.nodes[node].uuid == nuuid ]
        if len(nodes)>1:
            logger.warning("[%s] - Found 2 nodes %s with uuid %s.", self.__class__.__name__, nodes, node_uuid)
        if len(nodes)==0:
            return None
        vuuid='%s'%(value_uuid)
        values = [ nodes[0].values[value] for value in nodes[0].values if nodes[0].values[value].uuid == vuuid]
        if len(values)>1:
            logger.warning("[%s] - Found 2 valus %s with uuid %s. Returning the fisrt one.", self.__class__.__name__, nodes, value_uuid)
        if len(values)==0:
            return None
        return values[0]

    def start_hourly_timer(self):
        """Start the hourly timer
        """
        if self.hourly_timer is not None:
            self.hourly_timer.cancel()
            self.hourly_timer = None
        hourly = False
        try:
            hourly = string_to_bool(self.options.get_option(self.section, 'hourly_timer', default = False))
        except Exception:
            logger.warning("[%s] - C'ant get hourly_timer from configuration file. Disable it", self.__class__.__name__)
            hourly = False
        if hourly:
            logger.debug("[%s] - start_hourly_timer", self.__class__.__name__)
            self.hourly_timer = threading.Timer(60*60, self.do_hourly_timer)
            self.hourly_timer.start()

    def stop_hourly_timer(self):
        """Stop the hourly timer
        """
        logger.debug("[%s] - Stop_hourly_timer", self.__class__.__name__)
        if self.hourly_timer is not None:
            self.hourly_timer.cancel()
            self.hourly_timer = None

    def add_hourly_job(self, callback):
        """Add an hourly job.
        """
        logger.debug("[%s] - Add_hourly_job %s", self.__class__.__name__, callback)
        self._hourly_jobs.append(callback)

    def remove_hourly_job(self, callback):
        """Remove an hourly job.
        """
        logger.debug("[%s] - Remove_hourly_job %s", self.__class__.__name__, callback)
        if self._hourly_jobs is not None and callback in self._hourly_jobs:
            self._hourly_jobs.remove(callback)

    def add_daily_job(self, callback):
        """Add an daily job.
        """
        logger.debug("[%s] - Add_daily_job %s", self.__class__.__name__, callback)
        self._daily_jobs.append(callback)

    def remove_daily_job(self, callback):
        """Remove an daily job.
        """
        logger.debug("[%s] - Remove_daily_job %s", self.__class__.__name__, callback)
        if self._daily_jobs is not None and callback in self._daily_jobs:
            self._daily_jobs.remove(callback)

    def do_hourly_timer(self):
        """Do the hourly timer thread
        """
        self.stop_hourly_timer()
        self.start_hourly_timer()
        logger.debug("[%s] - do_hourly_timer", self.__class__.__name__)
        try:
            self.options.set_option(self.section, 'hourly_timer_lastrun', datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S'))
        except Exception:
            logger.exception("[%s] - Can't save hourly_timer_lastrun in configuration file.", self.__class__.__name__)
        for job in self._hourly_jobs:
            try:
                job()
            except Exception:
                logger.exception("[%s] - Exception in hourly timers", self.__class__.__name__)
        if datetime.datetime.now().hour == 0:
            try:
                self.options.set_option(self.section, 'daily_timer_lastrun', datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S'))
            except Exception:
                logger.exception("[%s] - Can't save daily_timer_lastrun in configuration file.", self.__class__.__name__)
            for job in self._daily_jobs:
                try:
                    job()
                except Exception:
                    logger.exception("[%s] - exception in do daily timers", self.__class__.__name__)
        logger.debug("[%s] - Finish do_hourly_timer", self.__class__.__name__)

class JNTBusNodeMan(JNTNodeMan):
    """The node manager
    """
    def __init__(self, options, bus, section, thread_uuid, **kwargs):
        JNTNodeMan.__init__(self, options, section, thread_uuid, **kwargs)
        self.bus = bus
        self.uuid = thread_uuid

    def stop(self):
        """
        """
        logger.info("[%s] - Stop the node manager", self.__class__.__name__)
        try:
            self.bus.stop()
        except Exception:
            logger.exception("[%s] - Exception when stopping", self.__class__.__name__)
        JNTNodeMan.stop(self)

    def after_controller_reply_config(self):
        """Start the bus
        """
        self.bus.start(self.mqtt_nodes, self.trigger_reload)
        self.build_bus_components()

    def create_controller_node(self, **kwargs):
        """
        """
        return self.bus.create_node(self, None, options=self.options, **kwargs)

    def create_node(self, uuid, hadd, **kwargs):
        """
        """
        node = None
        #~ print uuid
        logger.info("[%s] - Create node for component %s in factory", self.__class__.__name__, uuid)
        if uuid in self.bus.components:
            compo = self.bus.components[uuid]
            node = compo.create_node(hadd)
            if node is not None:
                self.add_node(node.uuid, node)
                for keyv in compo.values.keys():
                    value = compo.values[keyv]
                    self.add_value_to_node(value.uuid, node, value)
            else:
                logger.error("[%s] - Can't create node for component %s in factory", self.__class__.__name__, self.bus.components[uuid])
        else:
            logger.error("[%s] - Can't create node because can't find component %s in components %s", self.__class__.__name__, uuid, self.bus.components)
        return node

    def after_config_node(self, uuid):
        """After configuring the node
        """
        #~ print self.bus.components
        if uuid in self.bus.components:
            compo = self.bus.components[uuid]
            try:
                compo.start(self.mqtt_nodes)
            except Exception:
                logger.exception("[%s] - Can't start component %s", self.__class__.__name__, uuid)
        elif not self.is_stopped:
            if uuid != self._controller.uuid:
                logger.error("[%s] - Can't start component because can't find %s in components", self.__class__.__name__, uuid)

    def after_fsm_stop(self):
        """
        """
        JNTNodeMan.after_fsm_stop(self)

    def get_nodes_hadds_from_local_config(self):
        """ {'uuid':'hadd'}
        """
        components = self.get_components()
        res = {}
        for component in components:
            uuid = '%s__%s' % (self.bus.uuid, component)
            options = self.options.get_options(uuid)
            #~ print "option ", uuid, options
            if 'hadd' not in options:
                logger.error("[%s] - Found component %s  without hadd in local config", self.__class__.__name__, uuid)
            else:
                res[uuid] = options['hadd']
        #~ print res
        logger.debug("[%s] - Founds hadds in local config %s", self.__class__.__name__, res)
        return res

    #~ def start_bus_components(self, **kwargs):
        #~ """Start the components
        #~ """
        #~ logger.debug("[%s] - Start the components", self.__class__.__name__)
        #~ for key in self.bus.components.keys():
            #~ try:
                #~ compo.start(self.mqtt_nodes)
            #~ except Exception:
                #~ logger.exception("[%s] - Can't start component %s on address %s", self.__class__.__name__, self.bus.components[key], compo._addr)

    def build_bus_components(self):
        """Build the bus components from factory
        """
        components = self.get_components()
        logger.debug("[%s] - Build components from factory : %s", self.__class__.__name__, components)
        for key in components.keys():
            try:
                logger.debug('[%s] - Add component %s', self.__class__.__name__, key)
                if components[key] not in self.bus.factory:
                    logger.error("[%s] - Can't find component %s in factory", self.__class__.__name__, components[key])
                add_comp = '%s__%s' % (self.bus.uuid, key)
                #add_comp = key
                self.bus.add_component(components[key], add_comp, options=self.options)
            except Exception:
                logger.exception("[%s] - Can't add component %s", self.__class__.__name__, key)

    def before_controller_reply_config(self):
        """
        """
        for keyv in self.bus.values.keys():
            value = self.bus.values[keyv]
            self.add_value_to_node(value.uuid, self._controller, value)

    def loop(self, stopevent):
        """
        """
        JNTNodeMan.loop(self, stopevent)
        try:
            self.bus.loop(stopevent)
        except Exception:
            logger.exception("Exception in nodeman loop")

class JNTNode(object):
    def __init__(self, uuid="a_unik_identifier_for_the_node_on_the_controller", **kwargs):
        """
        :param int uuid: the unique uuid of the node on the controller
        """
        self.uuid = uuid
        """The UUID of the node"""
        self.oid = kwargs.get('oid', 'generic')
        """The oid of the component associated to the node"""
        self.cmd_classes = kwargs.get('cmd_classes', [])
        """The command classes implemented by the node"""
        self.name = kwargs.get('name', 'Default name')
        """The name of the node"""
        self.product_name = kwargs.get('product_name', 'Default product name')
        """The product name of the node"""
        self.product_type = kwargs.get('product_type', 'Default product type')
        """The product type of the node"""
        self.product_manufacturer = kwargs.get('product_manufacturer', 'Default product manufacturer')
        """The product manufacturer of the node"""
        self.location = kwargs.get('location', 'Default location')
        """The location of the node"""
        self.values = {}
        """The values assumed by the node"""
        self.heartbeat = 30
        """The heartbeat delay"""
        self.config_timeout = 3
        """The delay before reloading the thread"""
        self._hadd = kwargs.get('hadd', None)
        """The HAAD of the node"""
        self._check_hearbeat_cb = kwargs.get('check_hearbeat_cb', None)
        """The callback to thr check_hearbeat method of the component"""
        self.options = kwargs.get('options', None)
        """The option inherited from startup"""

    def split_hadd(self):
        """Return the node part of the address node
        """
        return self.hadd.split(HADD_SEP)

    def check_heartbeat(self):
        """Check
        """
        if self._check_hearbeat_cb is not None:
            return self._check_hearbeat_cb()
        else:
            return None

    def from_dict(self, adict):
        """Update internal dict from adict
        """
        self.__dict__.update(adict)
        return self

    def to_dict(self):
        """Retrieve a dict version of the node
        """
        res = {}
        res.update(self.__dict__)
        for key in res.keys():
            if key.startswith('_') or key in ["values", "options"]:
                del res[key]
        res['hadd'] = self.hadd
        return res

    def to_json(self):
        """Retrieve a json version of the node
        """
        res = self.to_dict()
        return json_dumps(res)

    def add_internal_system_values(self):
        """
        """
        myval = janitoo.value.value_system_heartbeat(get_data_cb=self.heartbeat_get, set_data_cb=self.heartbeat_set)
        self.add_value(myval.uuid, myval)
        myval = janitoo.value.value_system_hadd(get_data_cb=self.hadd_get, set_data_cb=self.hadd_set)
        self.add_value(myval.uuid, myval)
        myval = janitoo.value.value_system_config_timeout(get_data_cb=self.config_timeout_get, set_data_cb=self.config_timeout_set)
        self.add_value(myval.uuid, myval)

    def add_internal_config_values(self):
        """
        """
        myval = janitoo.value.value_config_name(get_data_cb=self.name_get, set_data_cb=self.name_set)
        self.add_value(myval.uuid, myval)
        myval = janitoo.value.value_config_location(get_data_cb=self.location_get, set_data_cb=self.location_set)
        self.add_value(myval.uuid, myval)

    def add_value(self, uuid, value):
        """
        """
        self.values[uuid] = value
        self.values[uuid].node_uuid = self.uuid
        self.values[uuid].hadd = self.hadd
        return True

    def load_system_from_local(self):
        """Retrieve a json version of the node
        """
        self.config_timeout_get(None,None)
        self.heartbeat_get(None,None)

    def load_config_from_local(self):
        """Retrieve a json version of the node
        """
        for value in self.values:
            #~ print value
            if self.values[value].genre == 0x03:
                #~ print self.values[value]._get_data_cb
                temp = self.values[value].data
                #~ print "********************load config from local"
                #~ print "%s = %s"%(value,temp)
                #~ print self.location
                #self.__dict__[value] = self.values[value].data

    def heartbeat_get(self, node_uuid, index):
        """
        """
        hb = self.options.get_option(node_uuid, 'heartbeat')
        if hb is not None:
            try:
                self.heartbeat = int(hb)
            except ValueError:
                logger.exception('Exception when retrieving heartbeat')
        return self.heartbeat

    def heartbeat_set(self, node_uuid, index, value):
        """
        """
        try:
            self.heartbeat = int(value)
            self.options.set_option(node_uuid, 'heartbeat', self.heartbeat)
        except ValueError:
            logger.exception('Exception when setting heartbeat')

            return self.options.get_option(self.node.uuid, 'heartbeat')

    def config_timeout_get(self, node_uuid, index):
        """
        """
        config_timeout = self.options.get_option(node_uuid, 'config_timeout')
        if config_timeout is not None:
            try:
                self.config_timeout = float(config_timeout)
            except ValueError:
                logger.exception('Exception when retrieving timeout')
        return self.config_timeout

    def config_timeout_set(self, node_uuid, index, value):
        """
        """
        try:
            self.config_timeout = float(value)
            self.options.set_option(node_uuid, 'config_timeout', self.config_timeout)
        except ValueError:
            logger.exception('Exception when setting timeout')

    @property
    def hadd(self):
        """
        """
        return self._hadd

    @hadd.setter
    def hadd(self, value):
        """
        """
        self._hadd = value
        for val in self.values:
            self.values[val].hadd = value

    def hadd_get(self, node_uuid, index):
        """
        """
        hadd = self.options.get_option(node_uuid, 'hadd')
        if hadd is not None:
            try:
                self.hadd = hadd
            except ValueError:
                logger.exception('Exception when retrieving hadd')
        return self.hadd

    def hadd_set(self, node_uuid, index, value):
        """
        """
        try:
            self.hadd = value
            self.options.set_option(node_uuid, 'hadd', self.hadd)
        except ValueError:
            logger.exception('Exception when setting hadd')

    def name_get(self, node_uuid, index):
        """
        """
        name = self.options.get_option(node_uuid, 'name')
        #~ print name
        if name is not None:
            self.name = name
        return self.name

    def name_set(self, node_uuid, index, value):
        """
        """
        try:
            self.name = value
            self.options.set_option(node_uuid, 'name', self.name)
            #~ print self.uuid
        except ValueError:
            logger.exception('Exception when setting name')

    def location_get(self, node_uuid, index):
        """
        """
        location = self.options.get_option(node_uuid, 'location')
        #~ print location
        if location is not None:
            self.location = location
        return self.location

    def location_set(self, node_uuid, index, value):
        """
        """
        try:
            self.location = value
            self.options.set_option(node_uuid, 'location', self.location)
        except ValueError:
            logger.exception('Exception when setting location')
