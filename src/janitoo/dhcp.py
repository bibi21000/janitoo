# -*- coding: utf-8 -*-
"""The dhcp library

TODO :
- actuellement l'etat HEARTBEAT n'existe que pour les primary car il sert pour le discover.
- il faut l'implémenter pour les secondary : par /resolv ? /dhcp/?

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
import datetime
import threading

from janitoo.fsm import Machine, State
from janitoo.utils import HADD, HADD_SEP
from janitoo.utils import json_dumps, json_loads, hadd_split
from janitoo.utils import TOPIC_NODES, TOPIC_NODES_REPLY, TOPIC_NODES_REQUEST
from janitoo.utils import TOPIC_BROADCAST_REPLY, TOPIC_BROADCAST_REQUEST, TOPIC_RESOLV_REQUEST, TOPIC_RESOLV, TOPIC_RESOLV_REPLY, TOPIC_RESOLV_BROADCAST
from janitoo.utils import TOPIC_VALUES_USER, TOPIC_VALUES_CONFIG, TOPIC_VALUES_BASIC, TOPIC_VALUES_SYSTEM, TOPIC_HEARTBEAT
from janitoo.mqtt import MQTTClient
from janitoo.options import JNTOptions, string_to_bool
from janitoo.value import JNTValue
from janitoo.node import JNTNode

##############################################################
##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import CAPABILITY_DESC, COMMAND_DESC

CAPABILITY_DYNAMIC_CONTROLLER = 0x04
CAPABILITY_TINY_CONTROLLER = 0x05
COMMAND_NETWORK_CONTROLLER = 0x1051
COMMAND_DISCOVERY = 0x5000

assert(COMMAND_DESC[COMMAND_DISCOVERY] == 'COMMAND_DISCOVERY')
assert(COMMAND_DESC[COMMAND_NETWORK_CONTROLLER] == 'COMMAND_NETWORK_CONTROLLER')
assert(CAPABILITY_DESC[CAPABILITY_DYNAMIC_CONTROLLER] == 'CAPABILITY_DYNAMIC_CONTROLLER')
assert(CAPABILITY_DESC[CAPABILITY_TINY_CONTROLLER] == 'CAPABILITY_TINY_CONTROLLER')
##############################################################

#https://github.com/tyarkoni/transitions

leases_states = {
    'ONLINE' : 5, #The machine is online
    'BOOT' : 4, #The machine is booting
    'CONFIG' : 4, #The machine is configuring
    'PENDING' : 3, #The machine did not send a ping
    'FAILED' : 2,
    'DEAD' : 1,
    'OFFLINE' : 0, #The machine is offline.
    'UNKNOWN' : -1, #Hummm ... we don' know.
    }

def normalize_request_info_values(data):
    """ """
    if 'uuid' in data:
        ndata = {'0': {'0':data}}
    elif len(data)==0 or 'uuid' in data[data.keys()[0]]:
        ndata = {'0':data}
    else:
        ndata = data
    return ndata

def normalize_request_system_values(data):
    """ """
    if 'uuid' in data:
        ndata = {'0': {'0':data}}
    elif len(data)==0 or 'uuid' in data[data.keys()[0]]:
        ndata = {'0':data}
    else:
        ndata = data
    return ndata

def normalize_request_info_nodes(data):
    """ """
    if 'hadd' in data:
        ndata = {'0':data}
    else:
        ndata = data
    return ndata

class CacheManager(object):

    def __init__(self):
        """
        """
        self.entries = {}

    def start(self, query):
        """Load the cache from db

        """
        #Initialise the cache
        if query is not None:
            self.entries = {}
            data = query.all()
            for line in data:
                self.update(line.add_ctrl, line.add_node, state=line.state, heartbeat=line.heartbeat, last_seen=line.last_seen)

    def flush(self, query=None):
        """Flush the cache to db. Remmove failed name from cache

        :param session: the session to use to communicate with db. May be a scoped_session if used in a separate tread. If None, use the common session.
        :type session: sqlalchemy session
        """
        if query is not None:
            data = query.all()
            for line in data:
                if line.add_ctrl in self.entries and line.add_node in self.entries[line.add_ctrl]:
                    line.state = self.entries[line.add_ctrl][line.add_node]['state']
                    line.last_seen = self.entries[line.add_ctrl][line.add_node]['last_seen']
        #Remove failed nodes from cache
        for ctrl in self.entries.keys():
            for node in self.entries[ctrl].keys():
                if self.entries[ctrl][node]['state'] == 'dead':
                    self.remove(ctrl, node)

    def update(self, add_ctrl, add_node, state="ONLINE", heartbeat=30, last_seen=None):
        """Update an entry in cache

        :param add_ctrl: the controller part of the address
        :type add_ctrl: Integer
        :param add_node: the node part of the address. 0 for controller, -1 for all nodes managed by controller.
        :type add_node: Integer
        :param state: the state of the node.
        :type state: String
        :param last_seen: the last time the node have been seen.
        :type last_seen: datetime
        """
        #~ print "update heartbeat"
        #~ print add_ctrl, add_node, state
        if last_seen is None:
            last_seen=datetime.datetime.now()
        #Create/Update an entry in cache
        #~ print "heartbeat update %s, %s, %s : %s" % (add_ctrl, add_node, heartbeat, last_seen)
        if add_ctrl not in self.entries:
            self.entries[add_ctrl] = {}
        nodes = []
        if add_node == -1:
            for nds in self.entries[add_ctrl]:
                nodes.append(nds)
        else:
            nodes.append(add_node)
        #print nodes
        for nd in nodes:
            if nd not in self.entries[add_ctrl]:
                self.entries[add_ctrl][nd] = {}
            self.entries[add_ctrl][nd]["state"] = state.upper()
            self.entries[add_ctrl][nd]["heartbeat"] = heartbeat * 1.1
            #print "Update state here"
            self.entries[add_ctrl][nd]["last_seen"] = last_seen
            if state == 'ONLINE' or state == 'BOOT':
                #Reset the counter
                self.entries[add_ctrl][nd]["count"] = 0

    def get_state(self, add_ctrl, add_node):
        """Return the state of an entry in cache

        :param add_ctrl: the controller part of the address
        :type add_ctrl: Integer
        :param add_node: the node part of the address. 0 for controller, -1 for all nodes managed by controller.
        :type add_node: Integer
        """
        #Create/Update an entry in cache
        if add_ctrl not in self.entries or add_node not in self.entries[add_ctrl]:
            return 'OFFLINE'
        return self.entries[add_ctrl][add_node]['state']

    def has_entry(self, add_ctrl, add_node):
        """Chech if an entry is in cache

        :param add_ctrl: the controller part of the address
        :type add_ctrl: Integer
        :param add_node: the node part of the address. 0 for controller, -1 for all nodes managed by controller.
        :type add_node: Integer
        """
        #Create/Update an entry in cache
        if add_ctrl not in self.entries:
            return False
        if add_node == -1:
            add_node = 0
        if add_node in self.entries[add_ctrl]:
            return True
        return False

    def remove(self, add_ctrl, add_node):
        """Remove an entry fom cache

        :param add_ctrl: the controller part of the address
        :type add_ctrl: Integer
        :param add_node: the node part of the address. 0 for controller, -1 for all nodes managed by controller.
        :type add_node: Integer
        """
        #Remove an antry from cache and clean tree in needed
        if add_ctrl not in self.entries:
            return
        if add_node in self.entries[add_ctrl]:
            del self.entries[add_ctrl][add_node]
        if len(self.entries[add_ctrl]) == 0 or add_node == -1:
            del self.entries[add_ctrl]

    def len(self):
        """Number of entries in the cache

        """
        return len(self.entries)

    def check_heartbeats(self, heartbeat_timeout=60, heartbeat_count=3, heartbeat_dead=604800):
        """Check the states of the machine. Must be called in a timer
        Called in a separate thread. Must use a scoped_session.

        :param session: the session to use to communicate with db. May be a scoped_session if used in a separate tread. If None, use the common session.
        :type session: sqlalchemy session
        """
        #~ print self.entries
        #~ print "Check heartbeat"
        now = datetime.datetime.now()
        lleases = list()
        for ctrl in self.entries.keys():
            for node in self.entries[ctrl].keys():
                if (now - self.entries[ctrl][node]['last_seen']).total_seconds() > self.entries[ctrl][node]['heartbeat'] \
                  and self.entries[ctrl][node]['state'] in ['ONLINE', 'BOOT', 'CONFIG', 'PENDING', 'FAILED', 'DEAD', 'OFFLINE']:
                    #~ print "add heartbeat %s,%s : %s"   % (ctrl, node, self.entries[ctrl][node]['last_seen'])
                    lleases.append((ctrl, node))
        for ctrl, node in lleases:
            if self.entries[ctrl][node]['state'] == 'FAILED' \
              and (now - self.entries[ctrl][node]['last_seen']).total_seconds() > heartbeat_dead:
                self.entries[ctrl][node]['state'] = 'DEAD'
                self.entries[ctrl][node]['count'] = 0
            else :
                #~ print self.entries[ctrl][node]
                if "count" not in self.entries[ctrl][node]:
                    self.entries[ctrl][node]['count'] = 1
                else:
                    self.entries[ctrl][node]['count'] += 1
                if self.entries[ctrl][node]['count'] >= heartbeat_count:
                    #The count is reached
                    #We need to change the state
                    if self.entries[ctrl][node]['state'] == 'ONLINE':
                        self.entries[ctrl][node]['state'] = 'PENDING'
                        self.entries[ctrl][node]['count'] = 0
                    elif self.entries[ctrl][node]['state'] == 'BOOT':
                        self.entries[ctrl][node]['state'] = 'PENDING'
                        self.entries[ctrl][node]['count'] = 0
                    elif self.entries[ctrl][node]['state'] == 'PENDING':
                        self.entries[ctrl][node]['state'] = 'FAILED'
                        self.entries[ctrl][node]['count'] = 0
                else:
                    lleases.remove((ctrl, node))
            #~ print heartbeat_count
            #~ print self.entries[ctrl][node]
        #~ print self.entries
        #~ print lleases
        return lleases

class HeartbeatMessage(object):
    """
    """
    def __init__(self, message):
        """
        """
        self.message = message

    def get_heartbeat(self):
        add_ctrl = -1
        add_node = -1
        state = 'ONLINE'
        try:
            #Try to decode payload as json
            #And retrieve add_ctrl and add_node from it
            data = json_loads(self.message.payload)
            for ffield in ['add_ctrl', 'add_node']:
                if ffield not in data:
                    logger.warning("mqtt_on_heartbeat receive a request with no %s", ffield)
                    return None, None, None
                try:
                    add_ctrl = int(data['add_ctrl'])
                except ValueError:
                    logger.exception("mqtt_on_heartbeat can't convert add_ctrl %s to integer", data['add_ctrl'])
                    return None, None, None
                except TypeError:
                    logger.exception("mqtt_on_heartbeat can't convert add_ctrl %s to integer", data['add_ctrl'])
                    return None, None, None
                try:
                    add_node = int(data['add_node'])
                except ValueError:
                    logger.exception("mqtt_on_heartbeat can't convert add_node %s to integer", data['add_node'])
                    return None, None, None
                except TypeError:
                    logger.exception("mqtt_on_heartbeat can't convert add_node %s to integer", data['add_node'])
                    return None, None, None
            if 'state' in data:
                state = data['state']
        except ValueError:
            #Try to retrieve adds from topic
            #hadd = message.topic.split('/')[-1]
            hadd = self.message.topic.replace("/dhcp/heartbeat/","")
            #print "hadd %s" % hadd
            try:
                add_ctrl,add_node = hadd_split(hadd)
                if add_ctrl is None:
                    return None, None, None
                state = self.message.payload
            except ValueError:
                logger.exception("get_heartbeat exception")
                return None, None, None
            except TypeError:
                logger.exception("get_heartbeat exception")
                return None, None, None
        return add_ctrl, add_node, state

def threaded_send_resolv(thread_event, options, hadd, resp, data):
    """
    """
    if thread_event.is_set():
        return
    mqttc = MQTTClient(options=options.data)
    mqttc.connect()
    mqttc.start()
    max_in_a_loop = 10
    time_to_sleep = 0.06
    if hadd is None or hadd=='':
        topic = TOPIC_RESOLV_BROADCAST
    else:
        topic = TOPIC_RESOLV_REPLY % hadd
    if data is None or len(data) == 0:
        #We send the response as is
        msg = json_dumps(resp)
        mqttc.publish(topic=topic, payload=msg)
    else :
        #~ print "data : %s"%data
        while len(data)>0:
            in_loop = 0
            for key in data.keys():
                if key in ["nodes", "systems", "configs", "commands", "basics", "users"]:
                    resp['data'] = {}
                    for kkey in data[key].keys():
                        #~ print "data 2: %s"%data
                        #print "in_loop : %s"%in_loop
                        if in_loop < max_in_a_loop:
                            resp['data'][kkey] = data[key][kkey]
                            del data[key][kkey]
                            in_loop +=1
                        else:
                            break
                    if len(data[key]) == 0:
                        del data[key]
                    if len(resp['data'])==0:
                        break
                    #~ print "resp = %s"%resp
                    msg = json_dumps(resp)
                    mqttc.publish(topic=topic, payload=msg)
                    thread_event.wait(time_to_sleep)
    mqttc.stop()
    if mqttc.is_alive():
        try:
            mqttc.join()
        except Exception:
            logger.exception("Catched exception")
    mqttc = None


class JNTNetwork(object):
    """The network manager : handle all nodes, values, ...

    Will be used in dhcp server and web server.

    Should work in 2 modes :
     - resolv : use the dhcp to retrieve information : nodes, values, configs, ...
      - listen to nodes updates sent by the dhcp (node_update, node_added, node_remove, ...
     - broadcast : to retrieve informations from nodes : in case of a dhcp fail or for the dhcp itself
      - heartbeat listening : when we receive a heartbeat from an unknown node, we send it standard system queries
      - send notification for node_added, node_update_info, node_update_config, ...

    Actually, we depend on socket/flask to emit update for the listener. This should be removed for the merge with the dhcp manager
    We can achieve it by callbacks or class heritage.

    Same problem for the lease manager

    heartbeat : heartbeat will be managed inside this class. No more dependcy to /dhcp = > new topic /heartbeat

    Starting as master is simple

    We should implement startup as a state machine :
    master : broadcast -> heartbeat
    secondary : resolv
    and if needed -> failover

    State machines :

        - fsm_network : a global one to manage primary, secondary and fail over states

    """

    fsm_network_states = [
        State(name='STOPPED', on_enter=['stop_resolv_heartbeat','stop_resolv_discover', 'stop_resolv_request', 'stop_nodes_discover', 'stop_heartbeat', 'stop_heartbeat_discover', 'stop_dispatch_heartbeat',
                'unset_failed', 'stop_broadcast_nodes_discover', 'stop_broadcast_configs_discover', 'stop_broadcast_systems_discover', 'stop_broadcast_basics_discover',
                'stop_broadcast_users_discover']),
        State(name='STARTED', on_enter=['start_values_listener', 'fsm_on_started'], on_exit=['stop_values_listener', 'stop_resolv_discover']),
        #~ State(name='BROADCAST_START', on_exit=['start_broadcast_discover']),
        #~ State(name='BROADCAST_STOP', on_exit=['stop_broadcast_discover']),
        State(name='BROADCAST_NODES', on_enter=['start_nodes_discover','start_broadcast_nodes_discover'], on_exit=['stop_broadcast_nodes_discover']),
        State(name='BROADCAST_SYSTEMS', on_enter=['start_broadcast_systems_discover'], on_exit=['stop_broadcast_systems_discover']),
        State(name='BROADCAST_CONFIGS', on_enter=['start_broadcast_configs_discover'], on_exit=['stop_broadcast_configs_discover']),
        State(name='BROADCAST_COMMANDS', on_enter=['start_broadcast_commands_discover'], on_exit=['stop_broadcast_commands_discover']),
        State(name='BROADCAST_BASICS', on_enter=['start_broadcast_basics_discover'], on_exit=['stop_broadcast_basics_discover']),
        State(name='BROADCAST_USERS', on_enter=['start_broadcast_users_discover'], on_exit=['stop_broadcast_users_discover', 'stop_broadcast_discover']),
        State(name='RESOLV', on_enter=['start_resolv_discover', 'start_resolv_heartbeat']),
        State(name='HEARTBEAT_DISCOVER', on_enter=['start_heartbeat_discover']),
        State(name='HEARTBEAT', on_enter=['start_heartbeat']),
        State(name='DISPATCH', on_enter=['start_dispatch_heartbeat', 'start_resolv_request'], on_exit=['stop_resolv_request']),
    ]

    states_str = {
        'STOPPED' : "Network is stopped",
        'STARTED' : "Network is started",
        'BROADCAST_NODES' : "Broadcasting nodes",
        'BROADCAST_USERS' : "Broadcasting user values",
        'BROADCAST_CONFIGS' : "Broadcasting config values",
        'BROADCAST_SYSTEMS' : "Broadcasting system values",
        'BROADCAST_BASICS' : "Broadcasting basic values",
        'BROADCAST_COMMANDS' : "Broadcasting command values",
        'RESOLV' : "Resolving nodes",
        'HEARTBEAT_DISCOVER' : "Start headbeart discovering",
        'HEARTBEAT' : "Start headbeart listening",
        'DISPATCH' : "Start headbeart dispatch",
    }

    """The states of the network
    """

    def __init__(self, stopevent, options, **kwargs):
        """
        """
        self.options = options
        self._stopevent = stopevent
        self.home_id = kwargs.get('home_id', "Unknown")
        self.is_primary = kwargs.get('is_primary', True)
        self.do_heartbeat_dispatch = kwargs.get('do_heartbeat_dispatch', True)
        self.is_secondary = kwargs.get('is_secondary', False)
        self._is_failed = kwargs.get('is_failed', False)
        self.broadcast_timeout = kwargs.get('broadcast_timeout', 3)
        self.resolv_timeout = kwargs.get('resolv_timeout', 5)
        self.request_timeout = kwargs.get('request_timeout', 3)
        self._test = kwargs.get('test', False)
        """For tests only"""

        self.state = 'STOPPED'
        self.fsm_network = None
        self.nodes = {}
        self.users = {}
        self.configs = {}
        self.basics = {}
        self.systems = {}
        self.commands = {}
        self._lock = threading.Lock()
        self.broadcast_mqttc = None
        self.broadcast_mqttc_lock = threading.Lock()
        self.broadcast_nodes_timer = None
        self.broadcast_configs_timer = None
        self.broadcast_systems_timer = None
        self.broadcast_users_timer = None
        self.broadcast_basics_timer = None
        self.broadcast_commands_timer = None
        self.heartbeat_discover_mqttc = None
        self.heartbeat_discover_mqttc_lock = threading.Lock()
        self.nodes_mqttc = None
        self.nodes_mqttc_lock = threading.Lock()
        self.resolv_mqttc = None
        self.resolv_timeout_timer = None
        self.resolv_heartbeat_mqttc = None
        self.resolv_heartbeat_mqttc_lock = threading.Lock()
        self.resolv_heartbeat_timer = None
        self.dispatch_heartbeat_mqttc = None
        self.dispatch_heartbeat_mqttc_lock = threading.Lock()
        self.dispatch_heartbeat_timer = None
        self.values_mqttc = None
        self.values_mqttc_lock = threading.Lock()
        self.resolv_request_mqttc = None
        self.resolv_request_mqttc_lock = threading.Lock()
        self.heartbeat_mqttc = None
        self.heartbeat_mqttc_lock = threading.Lock()

        self.dbcon = None
        self.hadds = {}
        self.heartbeat_cache = None
        self.threads_timers = []

    def __del__(self):
        """
        """
        try:
            self.stop()
        except Exception:
            pass

    @property
    def is_failed(self):
        """
        """
        return self._is_failed

    @property
    def is_stopped(self):
        """Return True if the network is stopped
        """
        return self.fsm_network == None

    @property
    def is_started(self):
        """Return True if the network is started
        """
        return self.state == "STARTED"

    def set_failed(self):
        """
        """
        self._is_failed = True
        self.emit_network()

    def unset_failed(self):
        """
        """
        self._is_failed = False
        self.emit_network()

    def start(self, loop_sleep=0.1):
        """Start the network
        """
        self.heartbeat_cache = CacheManager()
        self.loop_sleep = loop_sleep
        options = self.options.get_options('network')
        self.from_dict(options)
        #print self.__dict__
        if self.is_primary and self.is_secondary:
            raise RuntimeError("Can't start in both modes : primary or secondary")
        logger.debug("Start network with options %s" % options)
        self.heartbeat_cache.start(None)
        self.emit_nodes()
        self.emit_network()
        self._stopevent.clear()
        if self.fsm_network is None:
            self.fsm_network = self.create_fsm()
            self.state = 'STOPPED'
        self.fsm_network_start()

    def create_fsm(self):
        """
        """
        fsm = Machine(model=self, states=self.fsm_network_states, initial='STOPPED')
        fsm.add_ordered_transitions()
        #~ fsm.add_transition('fsm_network_start', 'STOPPED', 'BROADCAST_START', conditions=['is_primary'])
        fsm.add_transition('fsm_network_start', 'STOPPED', 'BROADCAST_NODES', conditions=['fsm_is_primary'])
        fsm.add_transition('fsm_network_start', 'STOPPED', 'RESOLV', conditions=['fsm_is_secondary'])
        #~ fsm.add_transition('fsm_network_next', 'BROADCAST_START', 'BROADCAST_NODES')
        fsm.add_transition('fsm_network_next', 'BROADCAST_NODES', 'BROADCAST_SYSTEMS')
        fsm.add_transition('fsm_network_next', 'BROADCAST_SYSTEMS', 'BROADCAST_COMMANDS')
        fsm.add_transition('fsm_network_next', 'BROADCAST_COMMANDS', 'BROADCAST_CONFIGS')
        fsm.add_transition('fsm_network_next', 'BROADCAST_CONFIGS', 'BROADCAST_BASICS')
        fsm.add_transition('fsm_network_next', 'BROADCAST_BASICS', 'BROADCAST_USERS')
        #~ fsm.add_transition('fsm_network_next', 'BROADCAST_CONFIGS', 'BROADCAST_STOP')
        fsm.add_transition('fsm_network_next', 'BROADCAST_USERS', 'HEARTBEAT_DISCOVER')
        #~ fsm.add_transition('fsm_network_next', 'BROADCAST_STOP', 'HEARTBEAT_DISCOVER')
        fsm.add_transition('fsm_network_next', 'HEARTBEAT_DISCOVER', 'DISPATCH', conditions=['fsm_do_heartbeat_dispatch'])
        fsm.add_transition('fsm_network_next', 'HEARTBEAT_DISCOVER', 'STARTED')
        fsm.add_transition('fsm_network_next', 'DISPATCH', 'STARTED')
        fsm.add_transition('fsm_network_next', 'RESOLV', 'HEARTBEAT')
        fsm.add_transition('fsm_network_next', 'HEARTBEAT', 'STARTED')
        fsm.add_transition('fsm_network_fail', 'STARTED', 'BROADCAST_NODES', before = ['set_failed'])
        fsm.add_transition('fsm_network_fail', 'RESOLV', 'BROADCAST_NODES', before = ['set_failed'])
        fsm.add_transition('fsm_network_recover', 'STARTED', 'RESOLV', before = ['stop_heartbeat_discover', 'stop_dispatch_heartbeat', 'unset_failed'])
        fsm.add_transition('fsm_network_stop', '*', 'STOPPED', before = ['before_stop_fsm'], after = ['delete_fsm'])
        return fsm

    def delete_fsm(self):
        """Delete the fsm
        """
        self.fsm_network = None
        if hasattr(self, "get_graph"):
            delattr(self, "get_graph")
        self.clean_all()

    def clean_all(self):
        """Delete the fsm
        """
        if self.heartbeat_cache is not None:
            self.heartbeat_cache.flush()
            self.heartbeat_cache = None
        self._lock.acquire()
        try:
            self.threads_timers = []
            self.nodes = {}
            self.hadds = {}
            self.configs = {}
            self.users = {}
            self.bascis = {}
            self.systems = {}
        except Exception:
            logger.exception("Exception in network stop")
        finally:
            self._lock.release()

    def before_stop_fsm(self):
        """Stop the network
        """
        self._stopevent.set()
        self.stop_resolv_heartbeat_timer()
        self.stop_dispatch_heartbeat_timer()

    def stop(self):
        """Stop the network
        """
        self.before_stop_fsm()
        if self.fsm_network is not None:
            self.fsm_network_stop()
        self.clean_all()
        #~ self.emit_nodes()
        #~ self.emit_network()

    def fsm_is_primary(self):
        """
        """
        return self.is_primary

    def fsm_is_secondary(self):
        """
        """
        return self.is_secondary and not self.is_primary

    def fsm_do_heartbeat_dispatch(self):
        """
        """
        return self.do_heartbeat_dispatch
        # Temporary fix https://travis-ci.org/bibi21000/janitoo/builds/95463154
        # return True

    def start_broadcast_nodes_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'start_broadcast_nodes_discover')
        if self._test:
            print "start_broadcast_nodes_discover"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            self.broadcast_mqttc_lock.acquire()
            try:
                if self.broadcast_mqttc is None:
                    self.broadcast_mqttc = MQTTClient(options=self.options.data, loop_sleep=self.loop_sleep)
                    self.broadcast_mqttc.connect()
                    self.broadcast_mqttc.subscribe(topic=TOPIC_BROADCAST_REPLY%self.hadds[0], callback=self.on_reply)
                    self.broadcast_mqttc.start()
                msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_nodes', 'reply_hadd':self.hadds[0]}
                self.broadcast_mqttc.publish(TOPIC_BROADCAST_REQUEST, json_dumps(msg))
                self.broadcast_nodes_timer = threading.Timer(self.broadcast_timeout, self.finish_broadcast_nodes_discover)
                self.broadcast_nodes_timer.start()
            finally:
                self.broadcast_mqttc_lock.release()
        self.emit_network()
        self.emit_nodes()

    def stop_broadcast_nodes_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_broadcast_nodes_discover')
        if self._test:
            print "stop_nodes_broadcast_discover"
        else:
            if self.broadcast_nodes_timer is not None:
                self.broadcast_nodes_timer.cancel()
            self.broadcast_nodes_timer = None
        self.emit_network()
        self.emit_nodes()

    def stop_broadcast_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_broadcast_discover')
        if self._test:
            print "stop_broadcast_discover"
        else:
            self.broadcast_mqttc_lock.acquire()
            try:
                if self.broadcast_mqttc is not None:
                    self.broadcast_mqttc.unsubscribe(topic=TOPIC_BROADCAST_REPLY%self.hadds[0])
                    self.broadcast_mqttc.stop()
                    if self.broadcast_mqttc.is_alive():
                        try:
                            self.broadcast_mqttc.join()
                        except Exception:
                            logger.exception("Catched exception")
                    self.broadcast_mqttc = None
            finally:
                self.broadcast_mqttc_lock.release()
        self.emit_network()
        self.emit_nodes()

    def finish_broadcast_nodes_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'finish_broadcast_nodes_discover')
        self.emit_network()
        self.emit_nodes()
        if not self.is_started and not self._stopevent.is_set():
            self.fsm_network_next()

    def start_broadcast_users_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'start_broadcast_users_discover')
        if self._test:
            print "start_broadcast_users_discover"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_users', 'reply_hadd':self.hadds[0]}
            self.broadcast_mqttc.publish(TOPIC_BROADCAST_REQUEST, json_dumps(msg))
            self.broadcast_users_timer = threading.Timer(self.broadcast_timeout, self.finish_broadcast_users_discover)
            self.broadcast_users_timer.start()
        self.emit_network()
        self.emit_nodes()

    def stop_broadcast_users_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_broadcast_users_discover')
        if self._test:
            print "stop_broadcast_users_discover"
        else:
            if self.broadcast_users_timer is not None:
                self.broadcast_users_timer.cancel()
            self.broadcast_users_timer = None
        self.emit_network()
        self.emit_nodes()

    def finish_broadcast_users_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'finish_broadcast_users_discover')
        self.emit_network()
        self.emit_users()
        if self._stopevent.is_set() or self.is_stopped:
            return
        self.fsm_network_next()

    def start_broadcast_configs_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'start_broadcast_configs_discover')
        if self._test:
            print "start_broadcast_configs_discover"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_configs', 'reply_hadd':self.hadds[0]}
            self.broadcast_mqttc.publish(TOPIC_BROADCAST_REQUEST, json_dumps(msg))
            self.broadcast_configs_timer = threading.Timer(self.broadcast_timeout, self.finish_broadcast_configs_discover)
            self.broadcast_configs_timer.start()
        self.emit_network()
        self.emit_nodes()

    def stop_broadcast_configs_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_broadcast_configs_discover')
        if self._test:
            print "stop_broadcast_configs_discover"
        else:
            if self.broadcast_configs_timer is not None:
                self.broadcast_configs_timer.cancel()
            self.broadcast_configs_timer = None

    def finish_broadcast_configs_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'finish_broadcast_configs_discover')
        self.emit_network()
        self.emit_configs()
        if self._stopevent.is_set() or self.is_stopped:
            return
        self.fsm_network_next()

    def start_broadcast_basics_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'start_broadcast_basics_discover')
        if self._test:
            print "start_broadcast_basics_discover"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_basics', 'reply_hadd':self.hadds[0]}
            self.broadcast_mqttc.publish(TOPIC_BROADCAST_REQUEST, json_dumps(msg))
            self.broadcast_basics_timer = threading.Timer(self.broadcast_timeout, self.finish_broadcast_basics_discover)
            self.broadcast_basics_timer.start()
        self.emit_network()
        self.emit_nodes()

    def stop_broadcast_basics_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_broadcast_basics_discover')
        if self._test:
            print "stop_broadcast_basics_discover"
        else:
            if self.broadcast_basics_timer is not None:
                self.broadcast_basics_timer.cancel()
            self.broadcast_basics_timer = None

    def finish_broadcast_basics_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'finish_broadcast_basics_discover')
        self.emit_network()
        self.emit_basics()
        if self._stopevent.is_set() or self.is_stopped:
            return
        self.fsm_network_next()

    def start_broadcast_systems_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'start_broadcast_systems_discover')
        if self._test:
            print "start_broadcast_systems_discover"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_systems', 'reply_hadd':self.hadds[0]}
            self.broadcast_mqttc.publish(TOPIC_BROADCAST_REQUEST, json_dumps(msg))
            self.broadcast_systems_timer = threading.Timer(self.broadcast_timeout, self.finish_broadcast_systems_discover)
            self.broadcast_systems_timer.start()
        self.emit_network()
        self.emit_nodes()

    def stop_broadcast_systems_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_broadcast_systems_discover')
        if self._test:
            print "stop_broadcast_systems_discover"
        else:
            if self.broadcast_systems_timer is not None:
                self.broadcast_systems_timer.cancel()
            self.broadcast_systems_timer = None

    def finish_broadcast_systems_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'finish_broadcast_systems_discover')
        self.emit_network()
        self.emit_systems()
        if self._stopevent.is_set() or self.is_stopped:
            return
        self.fsm_network_next()

    def start_broadcast_commands_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'start_broadcast_commands_discover')
        if self._test:
            print "start_broadcast_commands_discover"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_commands', 'reply_hadd':self.hadds[0]}
            self.broadcast_mqttc.publish(TOPIC_BROADCAST_REQUEST, json_dumps(msg))
            self.broadcast_commands_timer = threading.Timer(self.broadcast_timeout, self.finish_broadcast_commands_discover)
            self.broadcast_commands_timer.start()
        self.emit_network()
        self.emit_nodes()

    def stop_broadcast_commands_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_broadcast_commands_discover')
        if self._test:
            print "stop_broadcast_commands_discover"
        else:
            if self.broadcast_commands_timer is not None:
                self.broadcast_commands_timer.cancel()
            self.broadcast_commands_timer = None

    def finish_broadcast_commands_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'finish_broadcast_commands_discover')
        self.emit_network()
        self.emit_commands()
        if self._stopevent.is_set() or self.is_stopped:
            return
        self.fsm_network_next()

    def fsm_on_started(self):
        """
        """
        logger.debug("fsm_network : %s", 'fsm_on_started')
        self.emit_all()

    def start_resolv_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'start_resolv_discover')
        if self._test:
            print "start_resolv_discover"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            if self.resolv_mqttc is None:
                self.resolv_mqttc = MQTTClient(options=self.options.data, loop_sleep=self.loop_sleep)
                self.resolv_mqttc.connect()
                self.resolv_mqttc.subscribe(topic="%s#"%TOPIC_RESOLV)
                self.resolv_mqttc.add_topic(topic=TOPIC_RESOLV_REPLY%self.hadds[0], callback=self.on_resolv_reply)
                self.resolv_mqttc.add_topic(topic=TOPIC_RESOLV_BROADCAST+'#', callback=self.on_resolv_reply)
                self.resolv_mqttc.start()
                try:
                    self._stopevent.wait(0.5)
                except Exception:
                    logger.exception(u'Catched exception')
                #~ self.resolv_mqttc.on_connect = self.resolv_mqttc_on_connect
                th = threading.Timer(self.request_timeout/4, self.request_resolv_nodes)
                th.start()
                th = threading.Timer(2*self.request_timeout/4, self.request_resolv_systems)
                th.start()
                th = threading.Timer(3*self.request_timeout/4, self.request_resolv_configs)
                th.start()
                th = threading.Timer(4*self.request_timeout/4, self.request_resolv_basics)
                th.start()
                th = threading.Timer(1+self.request_timeout/4, self.request_resolv_users)
                th.start()
                th = threading.Timer(1+2*self.request_timeout/4, self.request_resolv_commands)
                th.start()
            if self.resolv_timeout_timer is not None:
                self.resolv_timeout_timer.cancel()
                self.resolv_timeout_timer = None
            self.resolv_timeout_timer = threading.Timer(self.resolv_timeout, self.finish_resolv_discover)
            self.resolv_timeout_timer.start()
        self.emit_network()
        self.emit_nodes()

    def finish_resolv_discover(self):
        """This function is called when we did nod receive informations on /dhcp/resolv defore timeout. The dhcp server must have send its 'online' status ... so he his dead
        fallback to fail mode
        """
        logger.debug("fsm_network : %s", 'finish_resolv_discover')
        self.resolv_timeout_timer = None
        if self._stopevent.is_set() or self.is_stopped:
            return
        if not self.is_failed:
            logger.warning("The network switch to failed mode")
            self.fsm_network_fail()
        self.emit_network()

    def stop_resolv_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_resolv_discover')
        if self._test:
            print "stop_resolv_discover"
        else:
            if self.resolv_timeout_timer is not None:
                self.resolv_timeout_timer.cancel()
                self.resolv_timeout_timer = None
            if self.resolv_mqttc is not None:
                try:
                    self.resolv_mqttc.remove_topic(topic=TOPIC_RESOLV_REPLY%self.hadds[0])
                    self.resolv_mqttc.remove_topic(topic=TOPIC_RESOLV_BROADCAST+'#')
                    self.resolv_mqttc.unsubscribe(topic="%s#"%TOPIC_RESOLV)
                except Exception:
                    logger.exception("Catched exception")
                try:
                    if self.resolv_mqttc:
                        self.resolv_mqttc.stop()
                except Exception:
                    logger.exception("Catched exception")
                try:
                    if self.resolv_mqttc and self.resolv_mqttc.is_alive():
                        self.resolv_mqttc.join()
                except Exception:
                    logger.exception("Catched exception")
                self.resolv_mqttc = None

    def start_resolv_request(self):
        """
        """
        logger.debug("fsm_network : %s", 'start_resolv_request')
        if self._test:
            print "start_resolv_request"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            self.resolv_request_mqttc_lock.acquire()
            try:
                if self.resolv_request_mqttc is None:
                    self.resolv_request_mqttc = MQTTClient(options=self.options.data, loop_sleep=self.loop_sleep)
                    self.resolv_request_mqttc.connect()
                    self.resolv_request_mqttc.subscribe(topic="%s#"%TOPIC_RESOLV_REQUEST, callback=self.on_resolv_request)
                    self.resolv_request_mqttc.start()
            except AttributeError:
                if self._stopevent.is_set() or self.is_stopped:
                    return
                else:
                    raise
            finally:
                self.resolv_request_mqttc_lock.release()

    def stop_resolv_request(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_resolv_request')
        if self._test:
            print "stop_resolv_request"
        else:
            self.resolv_request_mqttc_lock.acquire()
            try:
                if self.resolv_request_mqttc is not None:
                    self.resolv_request_mqttc.unsubscribe(topic="%s#"%TOPIC_RESOLV_REQUEST)
                    try:
                        self.resolv_request_mqttc.stop()
                        self.resolv_request_mqttc.join()
                    except Exception:
                        logger.exception("Catched exception")
                    self.resolv_request_mqttc = None
            finally:
                self.resolv_request_mqttc_lock.release()

    def start_resolv_heartbeat(self):
        """
        """
        logger.debug("fsm_network : %s", 'start_resolv_heartbeat')
        if self._test:
            print "start_resolv_heartbeat"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            try:
                self.resolv_heartbeat_mqttc_lock.acquire()
                try:
                    if self.resolv_heartbeat_mqttc is None:
                        self.resolv_heartbeat_mqttc = MQTTClient(options=self.options.data, loop_sleep=self.loop_sleep)
                        self.resolv_heartbeat_mqttc.connect()
                        self.resolv_heartbeat_mqttc.subscribe(topic="%sheartbeat"%TOPIC_RESOLV, callback=self.on_resolv_heartbeat)
                        self.resolv_heartbeat_mqttc.start()
                        self.stop_resolv_heartbeat_timer()
                finally:
                    self.resolv_heartbeat_mqttc_lock.release()
            except AttributeError:
                if self._stopevent.is_set() or self.is_stopped:
                    return
                else:
                    raise

    def start_resolv_heartbeat_timer(self):
        """
        """
        logger.debug("fsm_network : %s", 'start_resolv_heartbeat_timer')
        if self._test:
            print "start_resolv_heartbeat_timer"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            self.stop_resolv_heartbeat_timer()
            self.resolv_heartbeat_timer = threading.Timer(self.resolv_timeout, self.finish_resolv_heartbeat_timer)
            self.resolv_heartbeat_timer.start()

    def finish_resolv_heartbeat_timer(self):
        """This function is called when we did nod receive informations on /dhcp/resolv defore timeout. The dhcp server must have send its 'online' status ... so he his dead
        fallback to fail mode
        """
        logger.debug("fsm_network : %s", 'finish_resolv_heartbeat_timer')
        if self._stopevent.is_set() or self.is_stopped:
            return
        if not self.is_failed and self.is_started:
            logger.warning("The network switch to failed mode")
            self.fsm_network_fail()
        self.emit_network()

    def stop_resolv_heartbeat(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_resolv_heartbeat')
        if self._test:
            print "stop_resolv_heartbeat"
        else:
            self.stop_resolv_heartbeat_timer()
            self.resolv_heartbeat_mqttc_lock.acquire()
            try:
                if self.resolv_heartbeat_mqttc is not None:
                    self.resolv_heartbeat_mqttc.unsubscribe(topic="%sheartbeat"%TOPIC_RESOLV)
                    try:
                        self.resolv_heartbeat_mqttc.stop()
                        if self.resolv_heartbeat_mqttc:
                            self.resolv_heartbeat_mqttc.join()
                    except Exception:
                        logger.exception("Catched exception")
                    self.resolv_heartbeat_mqttc = None
            finally:
                self.resolv_heartbeat_mqttc_lock.release()

    def stop_resolv_heartbeat_timer(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_resolv_heartbeat_timer')
        if self._test:
            print "stop_resolv_heartbeat_timer"
        else:
            if self.resolv_heartbeat_timer is not None:
                self.resolv_heartbeat_timer.cancel()
                self.resolv_heartbeat_timer = None

    def stop_nodes_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_nodes_discover')
        if self._test:
            print "stop_nodes_discover"
        else:
            self.nodes_mqttc_lock.acquire()
            try:
                if self.nodes_mqttc is not None:
                    self.nodes_mqttc.unsubscribe(topic='/nodes/%s/reply/#'%self.hadds[0])
                    try:
                        self.nodes_mqttc.stop()
                        self.nodes_mqttc.join()
                    except Exception:
                        logger.exception("Catched exception")
                    self.nodes_mqttc = None
            finally:
                self.nodes_mqttc_lock.release()

    def start_nodes_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'start_nodes_discover')
        if self._test:
            print "start_nodes_discover"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            self.nodes_mqttc_lock.acquire()
            try:
                if self.nodes_mqttc is None:
                    self.nodes_mqttc = MQTTClient(options=self.options.data, loop_sleep=self.loop_sleep)
                    self.nodes_mqttc.connect()
                    self.nodes_mqttc.subscribe(topic='/nodes/%s/reply/#'%self.hadds[0], callback=self.on_reply)
                    logger.debug("start_nodes_discover : listen to %s", self.hadds[0])
                    self.nodes_mqttc.start()
            except AttributeError:
                if self._stopevent.is_set() or self.is_stopped:
                    return
                else:
                    raise
            finally:
                self.nodes_mqttc_lock.release()
        self.emit_nodes()
        self.emit_network()

    def start_heartbeat_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'start_heartbeat_discover')
        if self._test:
            print "start_heartbeat_discover"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            self.heartbeat_discover_mqttc_lock.acquire()
            try:
                if self.heartbeat_discover_mqttc is None:
                    self.heartbeat_discover_mqttc = MQTTClient(options=self.options.data, loop_sleep=self.loop_sleep)
                    self.heartbeat_discover_mqttc.connect()
                    self.heartbeat_discover_mqttc.subscribe(topic='/dhcp/heartbeat/#', callback=self.on_heartbeat_discover)
                    self.heartbeat_discover_mqttc.start()
            except AttributeError:
                if self._stopevent.is_set() or self.is_stopped:
                    return
                else:
                    raise
            finally:
                self.heartbeat_discover_mqttc_lock.release()
        self.emit_network()
        if self._stopevent.is_set() or self.is_stopped:
            return
        self.fsm_network_next()

    def stop_heartbeat_discover(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_heartbeat_discover')
        if self._test:
            print "stop_heartbeat_discover"
        else:
            self.heartbeat_discover_mqttc_lock.acquire()
            try:
                if self.heartbeat_discover_mqttc is not None:
                    self.heartbeat_discover_mqttc.unsubscribe(topic='/dhcp/heartbeat/#')
                    try:
                        self.heartbeat_discover_mqttc.stop()
                        self.heartbeat_discover_mqttc.join()
                    except Exception:
                        logger.exception("Catched exception")
                    self.heartbeat_discover_mqttc = None
            finally:
                self.heartbeat_discover_mqttc_lock.release()
        self.emit_network()

    def start_heartbeat(self):
        """
        """
        logger.debug("fsm_network : %s", 'start_heartbeat')
        if self._test:
            print "start_heartbeat"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            self.heartbeat_mqttc_lock.acquire()
            try:
                if self.heartbeat_mqttc is None:
                    self.heartbeat_mqttc = MQTTClient(options=self.options.data, loop_sleep=self.loop_sleep)
                    self.heartbeat_mqttc.connect()
                    self.heartbeat_mqttc.subscribe(topic='/dhcp/heartbeat/#', callback=self.on_heartbeat)
                    self.heartbeat_mqttc.start()
            except AttributeError:
                if self._stopevent.is_set() or self.is_stopped:
                    return
                else:
                    raise
            finally:
                self.heartbeat_mqttc_lock.release()
        if self._stopevent.is_set() or self.is_stopped:
            return
        self.emit_network()
        self.fsm_network_next()

    def stop_heartbeat(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_heartbeat')
        if self._test:
            print "stop_heartbeat"
        else:
            self.heartbeat_mqttc_lock.acquire()
            try:
                if self.heartbeat_mqttc is not None:
                    self.heartbeat_mqttc.unsubscribe(topic='/dhcp/heartbeat/#')
                    try:
                        self.heartbeat_mqttc.stop()
                    except Exception:
                        logger.exception("Catched exception")
                    try:
                        self.heartbeat_mqttc.join()
                    except Exception:
                        logger.exception("Catched exception")
                    self.heartbeat_mqttc = None
            finally:
                self.heartbeat_mqttc_lock.release()
        self.emit_network()

    def start_dispatch_heartbeat(self):
        """
        """
        logger.debug("fsm_network : %s", 'start_dispatch_heartbeat')
        if self._test:
            print "start_dispatch_heartbeat"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            self.dispatch_heartbeat_mqttc_lock.acquire()
            try:
                if self.dispatch_heartbeat_mqttc is None:
                    self.dispatch_heartbeat_mqttc = MQTTClient(options=self.options.data, loop_sleep=self.loop_sleep)
                    self.dispatch_heartbeat_mqttc.connect()
                    self.dispatch_heartbeat_mqttc.subscribe(topic='/dhcp/heartbeat/#', callback=self.on_heartbeat)
                    self.dispatch_heartbeat_mqttc.start()
                    self.start_dispatch_heartbeat_timer()
                    self.emit_network()
                    self.fsm_network_next()
            finally:
                self.dispatch_heartbeat_mqttc_lock.release()

    def start_dispatch_heartbeat_timer(self):
        """
        """
        #~ logger.debug("fsm_network : %s", 'start_dispatch_heartbeat_timer')
        if self._test:
            print "start_dispatch_heartbeat_timer"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            self.stop_dispatch_heartbeat_timer()
            self.dispatch_heartbeat_timer = threading.Timer(1, self.finish_dispatch_heartbeat_timer)
            self.dispatch_heartbeat_timer.start()

    def finish_dispatch_heartbeat_timer(self):
        """This function is called when we did nod receive informations on /dhcp/resolv defore timeout. The dhcp server must have send its 'online' status ... so he his dead
        fallback to fail mode
        """
        #~ logger.debug("fsm_network : %s", 'finish_dispatch_heartbeat_timer')
        if self._stopevent.is_set() or self.is_stopped:
            return
        self.stop_dispatch_heartbeat_timer()
        self.start_dispatch_heartbeat_timer()
        timeouts = self.heartbeat_cache.check_heartbeats()
        for add_ctrl, add_node in timeouts:
            #~ print add_ctrl, add_node
            msg = {'add_ctrl':add_ctrl, 'add_node':add_node, 'state':self.heartbeat_cache.entries[add_ctrl][add_node]['state']}
            #~ print msg
            self.dispatch_heartbeat_mqttc.publish_heartbeat_msg(msg)
            #~ self.dispatch_heartbeat_mqttc.publish_heartbeat_resolv_msg(msg)
            if self._stopevent is not None:
                self._stopevent.wait(0.02)

    def stop_dispatch_heartbeat(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_dispatch_heartbeat')
        if self._test:
            print "stop_dispatch_heartbeat"
        else:
            self.stop_dispatch_heartbeat_timer()
            try:
                self.dispatch_heartbeat_mqttc_lock.acquire()
                if self.dispatch_heartbeat_mqttc is not None:
                    try:
                        self.dispatch_heartbeat_mqttc.stop()
                        self.dispatch_heartbeat_mqttc.join()
                    except Exception:
                        logger.exception("Catched exception")
                    self.dispatch_heartbeat_mqttc = None
            finally:
                self.dispatch_heartbeat_mqttc_lock.release()

    def stop_dispatch_heartbeat_timer(self):
        """
        """
        #~ logger.debug("fsm_network : %s", 'stop_dispatch_heartbeat_timer')
        if self._test:
            print "stop_dispatch_heartbeat_timer"
        else:
            if self.dispatch_heartbeat_timer is not None:
                self.dispatch_heartbeat_timer.cancel()
                self.dispatch_heartbeat_timer = None

    def start_values_listener(self):
        """
        """
        logger.debug("fsm_network : %s", 'start_values_listener')
        if self._test:
            print "start_values_listener"
        else:
            if self._stopevent.is_set() or self.is_stopped:
                return
            self.values_mqttc_lock.acquire()
            try:
                if self.values_mqttc is None:
                    self.values_mqttc = MQTTClient(options=self.options.data, loop_sleep=self.loop_sleep)
                    self.values_mqttc.connect()
                    self.values_mqttc.subscribe(topic='/values/#', callback=self.on_value)
                    self.values_mqttc.start()
            except AttributeError:
                if self._stopevent.is_set() or self.is_stopped:
                    return
                else:
                    raise
            finally:
                self.values_mqttc_lock.release()
        self.emit_network()

    def stop_values_listener(self):
        """
        """
        logger.debug("fsm_network : %s", 'stop_values_listener')
        if self._test:
            print "stop_values_listener"
        else:
            self.values_mqttc_lock.acquire()
            try:
                if self.values_mqttc is not None:
                    self.values_mqttc.unsubscribe(topic='/values/#')
                    try:
                        self.values_mqttc.stop()
                    except Exception:
                        logger.exception("Catched exception")
                    try:
                        self.values_mqttc.join()
                    except Exception:
                        logger.exception("Catched exception")
                    self.values_mqttc = None
            finally:
                self.values_mqttc_lock.release()
        self.emit_network()

    def on_value(self, client, userdata, message):
        """On value

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        #~ logger.debug("[%s] - on_value %s", self.__class__.__name__, message.payload)
        try:
            mdata = json_loads(message.payload)
            #~ print mdata
            if 'genre' in mdata:
                data = {0:mdata}
            else:
                data = mdata
            logger.debug("[%s] - on_value 2 %s", self.__class__.__name__, data)
            for key in data.keys():
                #~ print data
                if data[key]['genre'] == 0x01:
                    self.add_basics(data)
                    self.emit_basic(data)
                elif data[key]['genre'] == 0x02:
                    self.add_users(data)
                    self.emit_user(data)
                elif data[key]['genre'] == 0x03:
                    self.add_configs(data)
                    self.emit_config(data)
                elif data[key]['genre'] == 0x04:
                    self.add_systems(data)
                    self.emit_system(data)
                elif data[key]['genre'] == 0x05:
                    self.add_commands(data)
                    self.emit_command(data)
                else :
                    logger.warning("Unknown genre in value %s", data)
        except Exception:
            logger.exception("Exception in on_value")

    def on_resolv_request(self, client, userdata, message):
        """On diqpatch request

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        #~ logger.debug("[%s] - on_resolv_request %s", self.__class__.__name__, message.payload)
        #~ logger.debug("[%s] - on_resolv_request %s", self.__class__.__name__, message.payload)
        try:
            data = json_loads(message.payload)
            #~ print data['uuid']
            #We should check what value is requested
            #{'hadd', 'cmd_class', 'type'='list', 'genre'='0x04', 'data'='node|value|config', 'uuid'='request_info'}
            #print self.systems
            if data['cmd_class'] == COMMAND_DISCOVERY:
                if data['genre'] == 0x04:
                    resp = {}
                    resp.update(data)
                    #~ print "data uuid %s" %data['uuid']
                    data_to_send = {'nodes':{}, 'systems':{}, 'configs':{}, 'commands':{}, 'basics':{}, 'users':{}}
                    if data['uuid'] == "request_info_nodes":
                        #~ print " self.nodes %s"%self.nodes
                        for knode in self.nodes.keys():
                            #~ print " self.nodes.keys %s"%self.nodes.keys()
                            data_to_send['nodes'][knode] = self.nodes[knode]
                            #~ print "data_to_send %s"%data_to_send
                    elif data['uuid'] == "request_info_configs":
                        for knode in self.configs.keys():
                            #~ print knode
                            #~ print knode
                            for kvalue in self.configs[knode].keys():
                                #~ print kvalue
                                value = self.configs[knode][kvalue]
                                #~ print value
                                if value['genre'] == 0x03:
                                    if not value['hadd'] in data_to_send['configs']:
                                        data_to_send['configs'][value['hadd']] = {}
                                    data_to_send['configs'][value['hadd']][value['uuid']] = value
                    elif data['uuid'] == "request_info_systems":
                        for knode in self.systems.keys():
                            #~ print knode
                            for kvalue in self.systems[knode].keys():
                                #~ print kvalue
                                value = self.systems[knode][kvalue]
                                #~ print value
                                if value['genre'] == 0x04:
                                    if not value['hadd'] in data_to_send['systems']:
                                        data_to_send['systems'][value['hadd']] = {}
                                    data_to_send['systems'][value['hadd']][value['uuid']] = value
                    elif data['uuid'] == "request_info_commands":
                        for knode in self.commands.keys():
                            #~ print knode
                            for kvalue in self.commands[knode].keys():
                                #~ print kvalue
                                value = self.commands[knode][kvalue]
                                #~ print value
                                if value['genre'] == 0x05:
                                    if not value['hadd'] in data_to_send['commands']:
                                        data_to_send['commands'][value['hadd']] = {}
                                    data_to_send['commands'][value['hadd']][value['uuid']] = value
                    elif data['uuid'] == "request_info_users":
                        for knode in self.users.keys():
                            #~ print knode
                            for kvalue in self.users[knode].keys():
                                #~ print kvalue
                                value = self.users[knode][kvalue]
                                #~ print value
                                if value['genre'] == 0x02:
                                    if not value['hadd'] in data_to_send['users']:
                                        data_to_send['users'][value['hadd']] = {}
                                    data_to_send['users'][value['hadd']][value['uuid']] = value
                    elif data['uuid'] == "request_info_basics":
                        for knode in self.basics.keys():
                            #~ print knode
                            for kvalue in self.basics[knode].keys():
                                #~ print kvalue
                                value = self.basics[knode][kvalue]
                                #~ print value
                                if value['genre'] == 0x01:
                                    if not value['hadd'] in data_to_send['basics']:
                                        data_to_send['basics'][value['hadd']] = {}
                                    data_to_send['basics'][value['hadd']][value['uuid']] = value
                    else:
                        logger.warning("Can't find % in %s", data['uuid'],'on_resolv_request')
                        return
                    #~ print "final data_to_send %s"%data_to_send
                    #~ print
                    try:
                        th = threading.Timer(0.05, threaded_send_resolv, args = (self._stopevent, self.options, data['reply_hadd'], resp, data_to_send))
                        th.start()
                        self.threads_timers.append(th)
                    except Exception:
                        logger.exception("Exception when running on_request method")
                        return
        except Exception:
            logger.exception("Exception in on_resolv_request")

    def on_reply(self, client, userdata, message):
        """On reply

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        logger.debug("[%s] - on_reply %s", self.__class__.__name__, message.payload)
        try:
            data = json_loads(message.payload)
            #We should check what value is requested
            #{'hadd', 'cmd_class', 'type'='list', 'genre'='0x04', 'data'='node|value|config', 'uuid'='request_info'}
            if data['cmd_class'] == COMMAND_DISCOVERY:
                if data['genre'] == 0x04:
                    #~ logger.warning("Data in %s : %s",data['uuid'], data)
                    if len(data['data']) == 0:
                        return
                    if data['uuid'] == "request_info_nodes":
                        self.add_nodes(data['data'])
                    elif data['uuid'] == "request_info_configs":
                        if 'genre' in data['data']:
                            data_to_add = {0:data['data']}
                        else:
                            data_to_add = data['data']
                        #~ print "data", data
                        for key in data_to_add.keys():
                            self.add_configs(data_to_add[key])
                    elif data['uuid'] == "request_info_systems":
                        self.add_systems(data['data'])
                    elif data['uuid'] == "request_info_commands":
                        self.add_commands(data['data'])
                    elif data['uuid'] == "request_info_users":
                        if 'genre' in data['data']:
                            data_to_add = {0:data['data']}
                        else:
                            data_to_add = data['data']
                        #~ print "data", data
                        for key in data_to_add.keys():
                            self.add_users(data_to_add[key])
                    elif data['uuid'] == "request_info_basics":
                        if 'genre' in data['data']:
                            data_to_add = {0:data['data']}
                        else:
                            data_to_add = data['data']
                        #~ print "data", data
                        for key in data_to_add.keys():
                            self.add_basics(data_to_add[key])
                    else:
                        logger.warning("Unknown value %s in %s", data['uuid'],'on_reply')
                        return
                    if self.is_primary and self.is_started:
                        th = threading.Timer(0.05, threaded_send_resolv, args = (self._stopevent, self.options, data['reply_hadd'], data, None))
                        th.start()
                        self.threads_timers.append(th)
        except Exception:
            logger.exception("Exception in on_reply")

    def on_resolv_heartbeat(self, client, userdata, message):
        """On resolv

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        #~ logger.debug("[%s] - on_resolv %s", self.__class__.__name__, message.payload)
        self.start_resolv_heartbeat_timer()
        if self.is_failed and self.is_started:
            logger.warning("The network switch to normal mode")
            self.fsm_network_recover()
        if self.resolv_timeout_timer is not None:
            self.resolv_timeout_timer.cancel()
            self.resolv_timeout_timer = None
            self.fsm_network_next()
        if message.topic == "/dhcp/resolv/heartbeat":
            logger.debug("on_resolv : %s", 'receive heartbeat')
            return

    def on_resolv_reply(self, client, userdata, message):
        """On resolv

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        #~ logger.debug("[%s] - on_resolv_reply %s", self.__class__.__name__, message.payload)
        self.start_resolv_heartbeat_timer()
        self.on_reply(client, userdata, message)

    def emit_network(self):
        """Emit a network state event
        """
        pass

    def emit_nodes(self):
        """Emit a nodes state event
        """
        pass

    def emit_node(self, nodes):
        """Emit a node state event
        nodes : a single node or a dict of nodes
        """
        pass

    def emit_users(self):
        """Emit a nodes state event
        """
        pass

    def emit_user(self, users):
        """Emit a node state event
        nodes : a single node or a dict of nodes
        """
        pass

    def emit_configs(self):
        """Emit a nodes state event
        """
        pass

    def emit_config(self, configs):
        """Emit a node state event
        nodes : a single node or a dict of nodes
        """
        pass

    def emit_basics(self):
        """Emit a nodes state event
        """
        pass

    def emit_basic(self, basics):
        """Emit a node state event
        nodes : a single node or a dict of nodes
        """
        pass

    def emit_commands(self):
        """Emit a nodes state event
        """
        pass

    def emit_command(self, systems):
        """Emit a node state event
        nodes : a single node or a dict of nodes
        """
        pass

    def emit_systems(self):
        """Emit a nodes state event
        """
        pass

    def emit_system(self, systems):
        """Emit a node state event
        nodes : a single node or a dict of nodes
        """
        pass

    def emit_all(self):
        """Emit all events
        nodes : a single node or a dict of nodes
        """
        self.emit_users()
        self.emit_configs()
        self.emit_systems()
        self.emit_commands()
        self.emit_basics()

    def request_node_nodes(self, hadd):
        """
        """
        if self.heartbeat_discover_mqttc is None:
            return
        msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_nodes', 'reply_hadd':self.hadds[0]}
        self.heartbeat_discover_mqttc.publish(TOPIC_NODES_REQUEST%hadd, json_dumps(msg))

    def request_node_users(self, hadd):
        """
        """
        if self.heartbeat_discover_mqttc is None:
            return
        msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_users', 'reply_hadd':self.hadds[0]}
        self.heartbeat_discover_mqttc.publish(TOPIC_NODES_REQUEST%hadd, json_dumps(msg))

    def request_node_systems(self, hadd):
        """
        """
        if self.heartbeat_discover_mqttc is None:
            return
        msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_systems', 'reply_hadd':self.hadds[0]}
        self.heartbeat_discover_mqttc.publish(TOPIC_NODES_REQUEST%hadd, json_dumps(msg))

    def request_node_basics(self, hadd):
        """
        """
        if self.heartbeat_discover_mqttc is None:
            return
        msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_basics', 'reply_hadd':self.hadds[0]}
        self.heartbeat_discover_mqttc.publish(TOPIC_NODES_REQUEST%hadd, json_dumps(msg))

    def request_node_configs(self, hadd):
        """
        """
        if self.heartbeat_discover_mqttc is None:
            return
        msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_configs', 'reply_hadd':self.hadds[0]}
        self.heartbeat_discover_mqttc.publish(TOPIC_NODES_REQUEST%hadd, json_dumps(msg))

    def request_node_commands(self, hadd):
        """
        """
        if self.heartbeat_discover_mqttc is None:
            return
        msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_commands', 'reply_hadd':self.hadds[0]}
        self.heartbeat_discover_mqttc.publish(TOPIC_NODES_REQUEST%hadd, json_dumps(msg))

    def request_resolv_nodes(self):
        """
        """
        if self.resolv_mqttc is None:
            return
        msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_nodes', 'reply_hadd':self.hadds[0]}
        self.resolv_mqttc.publish(TOPIC_RESOLV_REQUEST, json_dumps(msg))

    def request_resolv_users(self):
        """
        """
        if self.resolv_mqttc is None:
            return
        msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_users', 'reply_hadd':self.hadds[0]}
        self.resolv_mqttc.publish(TOPIC_RESOLV_REQUEST, json_dumps(msg))

    def request_resolv_systems(self):
        """
        """
        if self.resolv_mqttc is None:
            return
        msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_systems', 'reply_hadd':self.hadds[0]}
        self.resolv_mqttc.publish(TOPIC_RESOLV_REQUEST, json_dumps(msg))

    def request_resolv_basics(self):
        """
        """
        if self.resolv_mqttc is None:
            return
        msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_basics', 'reply_hadd':self.hadds[0]}
        self.resolv_mqttc.publish(TOPIC_RESOLV_REQUEST, json_dumps(msg))

    def request_resolv_configs(self):
        """
        """
        if self.resolv_mqttc is None:
            return
        msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_configs', 'reply_hadd':self.hadds[0]}
        self.resolv_mqttc.publish(TOPIC_RESOLV_REQUEST, json_dumps(msg))

    def request_resolv_commands(self):
        """
        """
        if self.resolv_mqttc is None:
            return
        msg = { 'cmd_class': COMMAND_DISCOVERY, 'genre':0x04, 'uuid':'request_info_commands', 'reply_hadd':self.hadds[0]}
        self.resolv_mqttc.publish(TOPIC_RESOLV_REQUEST, json_dumps(msg))

    def boot(self, hadds, loop_sleep=0.1):
        """Boot the node manager
        """
        self.hadds = hadds
        self.start(loop_sleep=loop_sleep)

    def on_heartbeat(self, client, userdata, message):
        """on_heartbeat

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        logger.debug("[%s] - on_heartbeat %s : %s", self.__class__.__name__, message.topic, message.payload)
        hb = HeartbeatMessage(message)
        add_ctrl, add_node, state = hb.get_heartbeat()
        #~ print "!"*30, "On heartbeat", add_ctrl, add_node
        if add_ctrl is None or add_node is None:
            return
        hadd = HADD % (add_ctrl, add_node)
        #~ print self.nodes
        if hadd not in self.nodes:
           return
        if hadd in self.nodes:
        #~ if hadd in self.nodes and state != self.heartbeat_cache.get_state(add_ctrl, add_node):
            node = {}
            node.update(self.nodes[hadd])
            node['state'] = state if state is not None else 'PENDING'
            data = normalize_request_info_nodes(node)
            self.emit_node(data)
        #~ print " node : %s" % self.nodes[hadd]
        self.heartbeat_cache.update(add_ctrl, add_node, state=state, heartbeat=self.nodes[hadd]['heartbeat'])

    def on_heartbeat_discover(self, client, userdata, message):
        """on_heartbeat_discover

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        logger.debug("[%s] - on_heartbeat_discover %s : %s", self.__class__.__name__, message.topic, message.payload)
        hb = HeartbeatMessage(message)
        add_ctrl, add_node, state = hb.get_heartbeat()
        self.incoming_hearbeat(add_ctrl, add_node, state)

    def incoming_hearbeat(self, add_ctrl, add_node, state):
        """
        """
        #print add_ctrl, add_node, state
        if add_ctrl == None:
            return
        if add_node == -1:
            hadd = HADD % (add_ctrl, 0)
        else:
            hadd = HADD % (add_ctrl, add_node)
        #Check if we already know this entry
        if not self.heartbeat_cache.has_entry(add_ctrl, add_node) and add_node == 0:
            #NO. So we ask from some info
            logger.debug("heartbeat from an unknown device %s,%s,%s", add_ctrl, add_node, state)
            th = threading.Timer(self.request_timeout/4, self.request_node_nodes, [hadd])
            th.start()
            self.threads_timers.append(th)
            th = threading.Timer(2*self.request_timeout/4, self.request_node_systems, [hadd])
            th.start()
            self.threads_timers.append(th)
            th = threading.Timer(3*self.request_timeout/4, self.request_node_configs, [hadd])
            th.start()
            self.threads_timers.append(th)
            th = threading.Timer(self.request_timeout, self.request_node_basics, [hadd])
            th.start()
            self.threads_timers.append(th)
            th = threading.Timer(self.request_timeout+self.request_timeout/4, self.request_node_users, [hadd])
            th.start()
            self.threads_timers.append(th)
            th = threading.Timer(self.request_timeout+2*self.request_timeout/4, self.request_node_commands, [hadd])
            th.start()
            self.threads_timers.append(th)
        else :
            #~ print " node : %s" % self.nodes[hadd]
            #~ if hadd in self.nodes and state != self.heartbeat_cache.get_state(add_ctrl, add_node):
            if hadd in self.nodes:
                node = {}
                node.update(self.nodes[hadd])
                #~ print "   node : %s" % node
                node['state'] = state if state != None else 'PENDING'
                data = normalize_request_info_nodes(node)
                self.emit_node(data)
            if hadd in self.nodes:
                try:
                    self.heartbeat_cache.update(add_ctrl, add_node, state=state, heartbeat=self.nodes[hadd]['heartbeat'])
                except Exception:
                    logger.exception("Exception in self.heartbeat_cache.update : %s", self.heartbeat_cache)

    def add_nodes(self, data):
        """
        """
        initial_startup = False
        do_emit = False
        self._lock.acquire()
        #~ print 'nodes data', data
        try:
            if self.broadcast_nodes_timer != None:
                #This is the initial startup.
                initial_startup = True
                self.broadcast_nodes_timer.cancel()
                self.broadcast_nodes_timer = None
                self.broadcast_nodes_timer = threading.Timer(self.broadcast_timeout, self.finish_broadcast_nodes_discover)
                self.broadcast_nodes_timer.start()
            ndata = normalize_request_info_nodes(data)
            #~ print "nodes ddddaaaaaaaaaaaaaaaaaaaata : %s" % ndata
            for knode in ndata.keys():
                self.nodes[ndata[knode]['hadd']] = {}
                self.nodes[ndata[knode]['hadd']].update(JNTNode().to_dict())
                self.nodes[ndata[knode]['hadd']].update(ndata[knode])
                self.nodes[ndata[knode]['hadd']].update(ndata[knode])
                add_ctrl, add_node = hadd_split(ndata[knode]['hadd'])
                if self.heartbeat_cache.has_entry(add_ctrl, add_node) == False:
                    do_emit = True
                #~ print self.nodes[ndata[knode]['hadd']]
                #~ print self.nodes[ndata[knode]['hadd']]['heartbeat']
                self.heartbeat_cache.update(add_ctrl, add_node, heartbeat=self.nodes[ndata[knode]['hadd']]['heartbeat'])
                ndata[knode]['state'] = 'PENDING'
            #~ if do_emit == True and initial_startup == False:
            self.emit_node(ndata)
        except Exception:
            logger.exception("Exception in add_nodes : ndata = %s", ndata)
        finally:
            self._lock.release()
        self.emit_network()

    def add_users(self, data):
        """
        """
        self._lock.acquire()
        #~ print 'users data', data
        try:
            if self.broadcast_users_timer != None:
                self.broadcast_users_timer.cancel()
                self.broadcast_users_timer = None
                self.broadcast_users_timer = threading.Timer(self.broadcast_timeout, self.finish_broadcast_users_discover)
                self.broadcast_users_timer.start()
            ndata = normalize_request_info_values(data)
            #~ print "ddddaaaaaaaaaaaaaaaaaaaata : %s" % ndata
            for nval in ndata:
                for kval in ndata[nval]:
                    hadd = ndata[nval][kval]['hadd']
                    uuid = ndata[nval][kval]['uuid']
                    #~ print "haaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaadddddddddd", hadd, uuid
                    index = 0
                    if 'index' in ndata[nval][kval]:
                        index = ndata[nval][kval]['index']
                    if hadd not in self.users:
                        self.users[hadd] = {}
                    if uuid not in self.users[hadd]:
                        self.users[hadd][uuid] = {}
                    if index not in self.users[hadd][uuid]:
                        self.users[hadd][uuid][index] = ndata[nval][kval]
                    else:
                        self.users[hadd][uuid][index].update(ndata[nval][kval])
                    ndata[nval][kval].update(self.users[hadd][uuid][index])
                    #~ print 'add_users', self.users[hadd][uuid][index]
            #~ print "seeeeeeeeeeeeeeeeeeeeeeeeeeeeeeelf.users"
            #~ print self.users
        except Exception:
            logger.exception("Exception in add_users : ndata = %s", ndata)
        finally:
            self._lock.release()

    def add_configs(self, data):
        """
        """
        self._lock.acquire()
        #~ print 'configs data', data
        try:
            if self.broadcast_configs_timer != None:
                self.broadcast_configs_timer.cancel()
                self.broadcast_configs_timer = None
                self.broadcast_configs_timer = threading.Timer(self.broadcast_timeout, self.finish_broadcast_configs_discover)
                self.broadcast_configs_timer.start()
            ndata = normalize_request_info_values(data)
            for nval in ndata:
                for kval in ndata[nval]:
                    #~ print "haaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaadddddddddd", ndata[nval][kval]
                    hadd = ndata[nval][kval]['hadd']
                    uuid = ndata[nval][kval]['uuid']
                    #~ print "haaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaadddddddddd", hadd, uuid
                    index = 0
                    if 'index' in ndata[nval][kval]:
                        index = ndata[nval][kval]['index']
                    if hadd not in self.configs:
                        self.configs[hadd] = {}
                    if uuid not in self.configs[hadd]:
                        self.configs[hadd][uuid] = {}
                    if index not in self.configs[hadd][uuid]:
                        self.configs[hadd][uuid][index] = ndata[nval][kval]
                    else:
                        self.configs[hadd][uuid][index].update(ndata[nval][kval])
                    ndata[nval][kval].update(self.configs[hadd][uuid][index])
            #~ for nval in ndata:
                #~ for kval in ndata[nval]:
                    #~ if ndata[nval][kval]['hadd'] not in self.configs:
                        #~ self.configs[ndata[nval][kval]['hadd']] = {}
                    #~ self.configs[ndata[nval][kval]['hadd']][ndata[nval][kval]['uuid']] = ndata[nval][kval]
            #~ print "add_configs self.configs ", self.configs
        except Exception:
            logger.exception("Exception in add_configs : ndata = %s", ndata)
        finally:
            self._lock.release()

    def add_basics(self, data):
        """
        """
        self._lock.acquire()
        #~ print 'basics data', data
        try:
            if self.broadcast_basics_timer != None:
                self.broadcast_basics_timer.cancel()
                self.broadcast_basics_timer = None
                self.broadcast_basics_timer = threading.Timer(self.broadcast_timeout, self.finish_broadcast_basics_discover)
                self.broadcast_basics_timer.start()
            ndata = normalize_request_info_values(data)
            #~ print "ddddaaaaaaaaaaaaaaaaaaaata : %s" % ndata
            for nval in ndata:
                for kval in ndata[nval]:
                    hadd = ndata[nval][kval]['hadd']
                    uuid = ndata[nval][kval]['uuid']
                    #~ print "haaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaadddddddddd", hadd, uuid
                    index = 0
                    if 'index' in ndata[nval][kval]:
                        index = ndata[nval][kval]['index']
                    if hadd not in self.basics:
                        self.basics[hadd] = {}
                    if uuid not in self.basics[hadd]:
                        self.basics[hadd][uuid] = {}
                    if index not in self.basics[hadd][uuid]:
                        self.basics[hadd][uuid][index] = ndata[nval][kval]
                    else:
                        self.basics[hadd][uuid][index].update(ndata[nval][kval])
                    ndata[nval][kval].update(self.basics[hadd][uuid][index])
                    #~ print 'add_basics', self.basics[hadd][uuid][index]
            #~ print "seeeeeeeeeeeeeeeeeeeeeeeeeeeeeeelf.basics"
            #~ print self.basics
        except Exception:
            logger.exception("Exception in add_basics : ndata = %s", ndata)
        finally:
            self._lock.release()

    def add_systems(self, data):
        """
        """
        self._lock.acquire()
        #~ print 'systems data', data
        try:
            if self.broadcast_systems_timer != None:
                self.broadcast_systems_timer.cancel()
                self.broadcast_systems_timer = None
                self.broadcast_systems_timer = threading.Timer(self.broadcast_timeout, self.finish_broadcast_systems_discover)
                self.broadcast_systems_timer.start()
            ndata = normalize_request_system_values(data)
            #~ print "ddddaaaaaaaaaaaaaaaaaaaata : %s" % ndata
            for nval in ndata:
                for kval in ndata[nval]:
                    if ndata[nval][kval]['hadd'] not in self.systems:
                        self.systems[ndata[nval][kval]['hadd']] = {}
                    self.systems[ndata[nval][kval]['hadd']][ndata[nval][kval]['uuid']] = ndata[nval][kval]
                    if 'node_uuid' not in ndata[nval][kval]:
                        ndata[nval][kval]['node_uuid'] = self.nodes[ndata[nval][kval]['hadd']]
        except Exception:
            logger.exception("Exception in add_systems : ndata = %s", ndata)
        finally:
            self._lock.release()

    def add_commands(self, data):
        """
        """
        self._lock.acquire()
        #~ print 'commands data', data
        try:
            if self.broadcast_commands_timer != None:
                self.broadcast_commands_timer.cancel()
                self.broadcast_commands_timer = None
                self.broadcast_commands_timer = threading.Timer(self.broadcast_timeout, self.finish_broadcast_commands_discover)
                self.broadcast_commands_timer.start()
            ndata = normalize_request_info_values(data)
            #~ print "ddddaaaaaaaaaaaaaaaaaaaata : %s" % ndata
            for nval in ndata:
                for kval in ndata[nval]:
                    hadd = ndata[nval][kval]['hadd']
                    uuid = ndata[nval][kval]['uuid']
                    #~ print "haaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaadddddddddd", hadd, uuid
                    index = 0
                    if 'index' in ndata[nval][kval]:
                        index = ndata[nval][kval]['index']
                    if hadd not in self.commands:
                        self.commands[hadd] = {}
                    if uuid not in self.commands[hadd]:
                        self.commands[hadd][uuid] = {}
                    if index not in self.commands[hadd][uuid]:
                        self.commands[hadd][uuid][index] = ndata[nval][kval]
                    else:
                        self.commands[hadd][uuid][index].update(ndata[nval][kval])
                    ndata[nval][kval].update(self.commands[hadd][uuid][index])
                    #~ print 'add_commands', self.commands[hadd][uuid][index]
            #~ print "seeeeeeeeeeeeeeeeeeeeeeeeeeeeeeelf.commands"
            #~ print self.commands
        except Exception:
            logger.exception("Exception in add_commands : ndata = %s", ndata)
        finally:
            self._lock.release()

    #~ def loop(self, mqttc, stopevent):
        #~ """
        #~ """
        #~ if mqttc is None:
            #~ mqttc = self.nodes_mqttc
        #~ try:
            #~ for th in self.threads_timers:
                #~ if not th.is_alive():
                    #~ self.threads_timers.remove(th)
        #~ except Exception:
            #~ logger.exception("Catched exception in loop")
        #~ to_polls = []
        #~ keys = self.polls.keys()
        #~ for key in keys:
            #~ if self.polls[key]['next_run'] < datetime.datetime.now():
                #~ to_polls.append(self.polls[key]['value'])
        #~ if len(to_polls)>0:
            #~ logger.debug(u'Found polls in timeout : %s', to_polls)
        #~ for value in to_polls:
            #~ self.publish_poll(mqttc, value, self._stopevent)
            #~ self._stopevent.wait(0.05)
        #~ try:
            #~ sleep = float(self.loop_sleep) - 0.05*len(to_polls)
        #~ except ValueError:
            #~ sleep = 0
        #~ if sleep<0:
            #~ sleep=0.1
        #~ self._stopevent.wait(sleep)

    @property
    def nodes_count(self):
        """

        :rtype: int

        """
        return len(self.nodes)

    @property
    def users_count(self):
        """

        :rtype: int

        """
        lvl1 = len(self.users)
        lvl2 = 0
        lvl3 = 0
        for k in self.users:
            lvl2 += len(self.users[k])
            for kk in self.users[k]:
                lvl3 += len(self.users[k][kk])
        return lvl1, lvl2, lvl3

    @property
    def configs_count(self):
        """

        :rtype: int

        """
        lvl1 = len(self.configs)
        lvl2 = 0
        lvl3 = 0
        for k in self.configs:
            lvl2 += len(self.configs[k])
            for kk in self.configs[k]:
                lvl3 += len(self.configs[k][kk])
        return lvl1, lvl2, lvl3

    @property
    def systems_count(self):
        """

        :rtype: int

        """
        return len(self.systems)

    @property
    def commands_count(self):
        """

        :rtype: int

        """
        lvl1 = len(self.commands)
        lvl2 = 0
        lvl3 = 0
        for k in self.commands:
            lvl2 += len(self.commands[k])
            for kk in self.commands[k]:
                lvl3 += len(self.commands[k][kk])
        return lvl1, lvl2, lvl3

    @property
    def basics_count(self):
        """

        :rtype: int

        """
        lvl1 = len(self.basics)
        lvl2 = 0
        lvl3 = 0
        for k in self.basics:
            lvl2 += len(self.basics[k])
            for kk in self.basics[k]:
                lvl3 += len(self.basics[k][kk])
        return lvl1, lvl2, lvl3

    @property
    def state_str(self):
        """

        :rtype: str

        """
        return self.states_str[self.state]

    @property
    def kvals(self):
        """
        The keyvals store in db for this object.

        :rtype: {}

        """
        if self.dbcon is None:
            return None
        res = {}
        cur = self.network.dbcon.cursor()
        cur.execute("SELECT key,value FROM %s WHERE object_id=%s"%(self.__class__.__name__, self.object_id))
        while True:
            row = cur.fetchone()
            if row == None:
                break
            res[row[0]] = row[1]
        return res

    @kvals.setter
    def kvals(self, kvs):
        """
        The keyvals store in db for this object.

        :param kvs: The key/valuse to store in db. Setting a value to None will remove it.
        :type kvs: {}
        :rtype: boolean

        """
        if self.dbcon is None:
            return False
        if len(kvs) == 0:
            return True
        cur = self.network.dbcon.cursor()
        for key in kvs.keys():
            logger.debug("DELETE FROM %s WHERE object_id=%s and key='%s'", self.__class__.__name__, self.object_id, key)
            cur.execute("DELETE FROM %s WHERE object_id=%s and key='%s'"%(self.__class__.__name__, self.object_id, key))
            if kvs[key] is not None:
                logger.debug("INSERT INTO %s(object_id, 'key', 'value') VALUES (%s,'%s','%s');", self.__class__.__name__, self.object_id, key, kvs[key])
                cur.execute("INSERT INTO %s(object_id, 'key', 'value') VALUES (%s,'%s','%s');"%(self.__class__.__name__, self.object_id, key, kvs[key]))
        self.network.dbcon.commit()
        return True

    def from_dict(self, adict):
        """Update internal dict from adict
        """
        for field in ['is_primary','do_heartbeat_dispatch','is_secondary','is_failed','is_stopped','is_started']:
            if field in adict:
                try:
                    if type(adict[field]) == type(''):
                        adict[field] = string_to_bool(adict[field])
                except ValueError:
                    logger.exception("Error in from_dict")
        for field in ['broadcast_timeout','resolv_timeout','request_timeout']:
            if field in adict:
                try:
                    adict[field] = float(adict[field])
                except ValueError:
                    logger.exception("Error in fron_dict")
        if 'resolv_timeout' in adict and 'request_timeout' in adict:
            assert (adict['resolv_timeout'] > adict['request_timeout']),"request_timeout must be smaller than resolv_timeout"
        self.__dict__.update(adict)

    def get_scenes(self):
        """Retrieves scenes on the network
        """
        pass

    def emit_scenes(self):
        """Emit a scene state event
        """
        pass

    def emit_scene(self, scene):
        """Emit a scene state event
        nodes : a single scene or a dict of scene
        """
        pass

    def get_scenarios(self):
        """Retrieves scenarios on the network
        """
        pass

    def emit_scenarios(self):
        """Emit a scenario state event
        """
        pass

    def emit_scenario(self, scenario):
        """Emit a scenario state event
        nodes : a single scenario or a dict of scenario
        """
        pass

    def get_crons(self):
        """Retrieves crons on the network
        """
        pass

    def emit_crons(self):
        """Emit a cron state event
        """
        pass

    def emit_cron(self, cron):
        """Emit a cron state event
        nodes : a single cron or a dict of cron
        """
        pass

    def state_to_dict(self):
        """state to dict
        """
        ret = {}
        ret['state'] = self.state
        ret['state_str'] = self.state_str
        ret['nodes_count'] = self.nodes_count
        ret['home_id'] = self.home_id
        ret['is_failed'] = self.is_failed
        ret['is_secondary'] = self.is_secondary
        ret['is_primary'] = self.is_primary
        return ret

    def nodes_to_dict(self, nodes):
        """nodes to dict
        """
        res = {}
        res.update(nodes)
        for key in res:
            try:
                add_ctrl, add_node = hadd_split(res[key]["hadd"])
                try:
                    res[key]['state'] = self.heartbeat_cache.entries[add_ctrl][add_node]['state']
                except Exception:
                    res[key]['state'] = 'UNKNOWN'
                    logger.warning("Exception catched in nodes_to_dict", exc_info=True)
                #Fix old protocols
                if "capabilities" not in res[key]:
                    res[key]['capabilities'] = []
            except Exception:
                logger.exception("Exception in nodes_to_dict : nodes = %s", nodes)
        return res

    def to_dict(self, which='state'):
        """Create a dict of which : state, nodes, configs, ...
        """
        if which == 'state':
            return self.state_to_dict()
        elif which == 'nodes':
            return self.nodes_to_dict(self.nodes)

    def find_network_controllers(self):
        """Retrieve network controller nodes on the network
        """
        ctrls = [ self.nodes[node]['hadd'] for node in self.nodes if COMMAND_NETWORK_CONTROLLER in self.nodes[node]['cmd_classes'] ]
        #~ logger.debug('[%s] - find_network_controllers nodes : %s', self.__class__.__name__, self.nodes)
        logger.debug('[%s] - find_network_controllers : %s', self.__class__.__name__, ctrls)
        return ctrls

    def find_primary_controllers(self):
        """Retrieve primaries nodes on the network
        """
        ctrls = self.find_network_controllers()
        res = [ self.nodes[node]['hadd'] for node in ctrls if self.systems[node]['network_controller']['data'] == 'primary' ]
        logger.debug('[%s] - find_primary_controllers : %s', self.__class__.__name__, res)
        return res

    def find_secondary_controllers(self):
        """Retrieve secondaries nodes on the network
        """
        ctrls = self.find_network_controllers()
        res = [ self.nodes[node]['hadd'] for node in ctrls if self.systems[node]['network_controller']['data'] == 'secondary' ]
        logger.debug('[%s] - find_secondary_controllers : %s', self.__class__.__name__, res)
        return res

    def find_controllers(self):
        """Retrieve controller nodes on the network
        """
        return [ self.nodes[node]['hadd'] for node in self.nodes if self.nodes[node]['hadd'].endswith('/0000') ]

    def find_controller_nodes(self, add_ctrl):
        """Retrieve nodes of a controller
        """
        return [ self.nodes[node]['hadd'] for node in self.nodes if self.nodes[node]['hadd'].startswith('%s/'%add_ctrl) and not self.nodes[node]['hadd'].endswith('/0000')]

    def find_node_values(self, node_hadd, genre='systems'):
        """Retrieve values of a node on the network :
        """
        if genre == 'systems':
            return self.systems[node_hadd] if node_hadd in self.systems else {}
        elif genre == 'configs':
            return self.configs[node_hadd] if node_hadd in self.configs else {}
        elif genre == 'basics':
            return self.basics[node_hadd] if node_hadd in self.basics else {}
        elif genre == 'users':
            return self.users[node_hadd] if node_hadd in self.users else {}
        elif genre == 'commands':
            return self.commands[node_hadd] if node_hadd in self.commands else {}
        return {}

    def find_node_value(self, node_hadd, genre='systems', vuuid=None):
        """Retrieve value of a node on the network :
        """
        if genre == 'systems':
            return self.systems[node_hadd][vuuid] if node_hadd in self.systems and vuuid in self.systems[node_hadd] else {}
        elif genre == 'configs':
            return self.configs[node_hadd][vuuid] if node_hadd in self.configs and vuuid in self.configs[node_hadd] else {}
        elif genre == 'basics':
            return self.basics[node_hadd][vuuid] if node_hadd in self.basics and vuuid in self.basics[node_hadd] else {}
        elif genre == 'users':
            return self.users[node_hadd][vuuid] if node_hadd in self.users and vuuid in self.users[node_hadd] else {}
        elif genre == 'commands':
            return self.commands[node_hadd][vuuid] if node_hadd in self.commands and vuuid in self.commands[node_hadd] else {}
        return {}

    def find_neighbors(self, node_hadd):
        """Retrieve neighbors of a node on the network :

        All controllers are neighbors of the network controllers
        A controller has all the nodes it holds as neighbors
        A simple node has only one neighbor : its controller

        """
        neighbors = []
        controllers = self.find_controllers()
        network_controllers = self.find_network_controllers()
        add_ctrl, add_node = hadd_split(node_hadd)
        if node_hadd in network_controllers:
            neighbors += controllers
        elif node_hadd in controllers:
            neighbors += network_controllers
            neighbors += self.find_controller_nodes(add_ctrl)
        else:
            neighbors += [HADD%(add_ctrl,0)]
        logger.debug('[%s] - find_neighbors for %s : %s', self.__class__.__name__, node_hadd, neighbors)
        return neighbors

def check_heartbeats(entries, heartbeat_timeout=60, heartbeat_count=3, heartbeat_dead=604800):
    """Check the states of the machine. Must be called in a timer
    Called in a separate thread. Must use a scoped_session.

    :param session: the session to use to communicate with db. May be a scoped_session if used in a separate tread. If None, use the common session.
    :type session: sqlalchemy session
    """
    now = datetime.datetime.now()
    lleases = list()
    for ctrl in entries.keys():
        for node in entries[ctrl].keys():
            if (now - entries[ctrl][node]['last_seen']).total_seconds() > heartbeat_timeout \
              and entries[ctrl][node]['state'] in ['online', 'boot', 'pending', 'failed']:
                lleases.append((ctrl, node))
    for ctrl, node in lleases:
        if entries[ctrl][node]['state'] == 'failed' \
          and (now - entries[ctrl][node]['last_seen']).total_seconds() > heartbeat_dead:
            entries[ctrl][node]['state'] = 'dead'
            entries[ctrl][node]['count'] = 0
        else :
            if "count" not in entries[ctrl][node]:
                entries[ctrl][node]['count'] = 1
            else:
                entries[ctrl][node]['count'] += 1
            if entries[ctrl][node]['count'] >= heartbeat_count:
                #The count is reached
                #We need to change the state
                if entries[ctrl][node]['state'] == 'online':
                    entries[ctrl][node]['state'] = 'pending'
                    entries[ctrl][node]['count'] = 0
                elif entries[ctrl][node]['state'] == 'boot':
                    entries[ctrl][node]['state'] = 'pending'
                    entries[ctrl][node]['count'] = 0
                elif entries[ctrl][node]['state'] == 'pending':
                    entries[ctrl][node]['state'] = 'failed'
                    entries[ctrl][node]['count'] = 0
