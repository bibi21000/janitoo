# -*- coding: utf-8 -*-
"""The mqtt client

Largely inspired from http://git.eclipse.org/c/paho/org.eclipse.paho.mqtt.python.git/tree/examples/sub-class.py

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

    Original copyright :
    Copyright (c) 2013 Roger Light <roger@atchoo.org>

    All rights reserved. This program and the accompanying materials
    are made available under the terms of the Eclipse Distribution License v1.0
    which accompanies this distribution.

    The Eclipse Distribution License is available at
    http://www.eclipse.org/org/documents/edl-v10.php.

    Contributors:
     - Roger Light - initial implementation

    This example shows how you can use the MQTT client in a class.

"""
__author__ = 'Sébastien GALLET aka bibi21000'
__email__ = 'bibi21000@gmail.com'
__copyright__ = "Copyright © 2013-2014-2015-2016 Sébastien GALLET aka bibi21000"

# Set default logging handler to avoid "No handler found" warnings.
import logging
logger = logging.getLogger(__name__)
import threading
import paho.mqtt.client as mqttc
import uuid as muuid
import traceback

from janitoo.utils import HADD, json_dumps

class MQTTBasic(mqttc.Client):
    """A grandmother for mqtt """
    def __init__(self, options=None, **kwargs):
        """
        """
        client_id = kwargs.pop('client_id', None)
        mqttc.Client.__init__(self, client_id=client_id, **kwargs)
        self.options = options
        if self.options is None:
            self.options = {}

    def disconnect(self):
        """
        """
        try:
            mqttc.Client.disconnect(self)
        except Exception:
            logger.exception('[%s] - Exception in disconnect', self.__class__.__name__)

    def connect_with_options(self):
        """Connect to the mqtt broker using options

        returns :
            0: Connection successful
            1: Connection refused - incorrect protocol version
            2: Connection refused - invalid client identifier
            3: Connection refused - server unavailable
            4: Connection refused - bad username or password
            5: Connection refused - not authorised
            6-255: Currently unused.

        """
        if "broker_user" in self.options and self.options['broker_user'] is not None:
            password = None
            if "broker_password" in self.options:
                password = self.options['broker_password']
            self.username_pw_set(self.options['broker_user'], password)
        server = '127.0.0.1'
        if "broker_ip" in self.options and self.options['broker_ip'] is not None:
            server = self.options['broker_ip']
        #print server
        port = 1883
        if "broker_port" in self.options and self.options['broker_port'] is not None:
            port = self.options['broker_port']
        keepalive = 60
        if "broker_keepalive" in self.options and self.options['broker_keepalive'] is not None:
            keepalive = int(self.options['broker_keepalive'])
        logger.debug('[%s] - Connect with options server:%s, port:%s', self.__class__.__name__, server, port)
        return self.connect(server, port=int(port), keepalive=keepalive)

    def publish_heartbeat(self, add_ctrl, add_node, state='ONLINE', qos=0, retain=False):
        """Publish an heartbeat for the node add_ctrl, add_node.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        :param uuid: The uuid sent in the request.
        :type uuid: str
        :param payload: The actual message to send. If not given, or set to None a
                        zero length message will be used. Passing an int or float will result
                        in the payload being converted to a string representing that number. If
                        you wish to send a true int/float, use struct.pack() to create the
                        payload you require.
        :type payload: message
        :param qos: The quality of service level to use.
        :type qos: int
        :param retain: If set to true, the message will be set as the "last known good"/retained message for the topic.
        :type retain: bool
        """
        self.publish(topic="/dhcp/heartbeat/"+HADD%(add_ctrl, add_node), payload=state, qos=qos, retain=retain)

    def publish_heartbeat_controller(self, add_ctrl, state='ONLINE', qos=0, retain=False):
        """Publish an heartbeat for the controller add_ctrl and all its nodes.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        :param uuid: The uuid sent in the request.
        :type uuid: str
        :param payload: The actual message to send. If not given, or set to None a
                        zero length message will be used. Passing an int or float will result
                        in the payload being converted to a string representing that number. If
                        you wish to send a true int/float, use struct.pack() to create the
                        payload you require.
        :type payload: message
        :param qos: The quality of service level to use.
        :type qos: int
        :param retain: If set to true, the message will be set as the "last known good"/retained message for the topic.
        :type retain: bool
        """
        msg = {'add_ctrl':add_ctrl, 'add_node':-1, 'state':state}
        self.publish(topic="/dhcp/heartbeat/", payload=json_dumps(msg), qos=qos, retain=retain)

    def publish_heartbeat_msg(self, msg, qos=0, retain=False):
        """Publish an heartbeat message.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        :param uuid: The uuid sent in the request.
        :type uuid: str
        :param payload: The actual message to send. If not given, or set to None a
                        zero length message will be used. Passing an int or float will result
                        in the payload being converted to a string representing that number. If
                        you wish to send a true int/float, use struct.pack() to create the
                        payload you require.
        :type payload: message
        :param qos: The quality of service level to use.
        :type qos: int
        :param retain: If set to true, the message will be set as the "last known good"/retained message for the topic.
        :type retain: bool
        """
        #Deprecated. We must send the heart to /dhcp/heartbeat/0011/0001
        self.publish(topic="/dhcp/heartbeat/", payload=json_dumps(msg), qos=qos, retain=retain)

    def publish_heartbeat_resolv_msg(self, msg, qos=0, retain=False):
        """Publish an heartbeat message.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        :param uuid: The uuid sent in the request.
        :type uuid: str
        :param payload: The actual message to send. If not given, or set to None a
                        zero length message will be used. Passing an int or float will result
                        in the payload being converted to a string representing that number. If
                        you wish to send a true int/float, use struct.pack() to create the
                        payload you require.
        :type payload: message
        :param qos: The quality of service level to use.
        :type qos: int
        :param retain: If set to true, the message will be set as the "last known good"/retained message for the topic.
        :type retain: bool
        """
        self.publish(topic="/resolv/dhcp/heartbeat/", payload=json_dumps(msg), qos=qos, retain=retain)

    def publish_value(self, hadd, value, genre='user', qos=0, retain=False):
        """Publish a value.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        :param uuid: The uuid sent in the request.
        :type uuid: str
        :param payload: The actual message to send. If not given, or set to None a
                        zero length message will be used. Passing an int or float will result
                        in the payload being converted to a string representing that number. If
                        you wish to send a true int/float, use struct.pack() to create the
                        payload you require.
        :type payload: message
        :param qos: The quality of service level to use.
        :type qos: int
        :param retain: If set to true, the message will be set as the "last known good"/retained message for the topic.
        :type retain: bool
        """
        #~ print "publish_value : ", hadd, value, genre
        if genre in ["user", "basic", "config"]:
            #For user values with indexes send all instance
            res = value.to_json_with_indexes()
        else:
            res = value.to_json()
        logger.debug('[%s] - Publish new value to /value/%s : %s', self.__class__.__name__, hadd, res)
        self.publish(topic="/values/%s/%s/%s" % (genre, hadd, value.uuid), payload=res, qos=qos, retain=retain)


class MQTTClient(threading.Thread):
    def __init__(self, client_id=None, options=None, loop_sleep=0.15):
        """Initialise the client

        :param client_id: use a specific client id which must be unique on the broker. Use None to let the client generate a random id for you.
        :type client_id: str
        """
        threading.Thread.__init__(self)
        self._stopevent = threading.Event()
        self.options = options
        if self.options is None:
            self.options = {}
        self.loop_sleep = loop_sleep
        self.client = MQTTBasic(client_id=client_id, options=options)
        self.client.on_connect = self.mqtt_on_connect
        self.client.on_publish = self.mqtt_on_publish
        self.client.on_subscribe = self.mqtt_on_subscribe

    def mqtt_on_connect(self, client, userdata, flags, rc):
        """Called when the broker responds to our connection request.


        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param flags: flags is a dict that contains response flags from the broker:
                      flags['session present'] - this flag is useful for clients that are
                      using clean session set to 0 only. If a client with clean
                      session=0, that reconnects to a broker that it has previously
                      connected to, this flag indicates whether the broker still has the
                      session information for the client. If 1, the session still exists.
        :type flags: dict
        :param rc: the value of rc determines success or not:
                       0: Connection successful
                       1: Connection refused - incorrect protocol version
                       2: Connection refused - invalid client identifier
                       3: Connection refused - server unavailable
                       4: Connection refused - bad username or password
                       5: Connection refused - not authorised
                       6-255: Currently unused.
        :type rc: in
        """
        logger.debug("[%s] - Connected to broker", self.__class__.__name__)
        #print("rc: "+str(rc))
        #raise JanitooNotImplemented('mqtt_on_connect not implemnted')

    def mqtt_on_message(self, client, userdata, message):
        """Called when a message has been received on a
        topic that the client subscribes to.

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage

        """
        logger.debug("[%s] - mqtt_on_message topic : %s, qos : %s, payload: %s", self.__class__.__name__, message.topic, message.qos, message.payload)
        #print(message.topic+" "+str(message.qos)+" "+str(message.payload))
        #raise JanitooNotImplemented('mqtt_on_message not implemnted')

    def mqtt_on_publish(self, client, userdata, mid):
        """called when a message that was to be sent using the
        publish() call has completed transmission to the broker.

        For messages with QoS levels 1 and 2, this means that the appropriate handshakes have
        completed. For QoS 0, this simply means that the message has left the
        client.
        This callback is important because even if the publish() call returns
        success, it does not always mean that the message has been sent.

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param mid: (Not used) The mid variable matches the mid variable returned from the
                    corresponding publish() call, to allow outgoing messages to be tracked.
        :type mid: unknow

        """
        #print("mid: "+str(mid))
        logger.debug("[%s] - The message have been published", self.__class__.__name__)

    def mqtt_on_subscribe(self, client, userdata, mid, granted_qos):
        """called when the broker responds to a subscribe request.

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param mid: (Not used) The mid variable matches the mid variable returned from the
                    corresponding publish() call, to allow outgoing messages to be tracked.
        :type mid: unknow
        :param granted_qos: The granted_qos variable is a list of integers that give the QoS level the broker has granted for each
                            of the different subscription requests..
        :type granted_qos: list()

        """
        #print("Subscribed: "+str(mid)+" "+str(granted_qos))
        logger.debug("[%s] - The subscription is done", self.__class__.__name__)

    def mqtt_on_log(self, client, userdata, level, buff):
        """called when the client has log information. Define to allow debugging.

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param level: The level variable gives the severity of the message
                      and will be one of MQTT_LOG_INFO, MQTT_LOG_NOTICE, MQTT_LOG_WARNING,
                      MQTT_LOG_ERR, and MQTT_LOG_DEBUG.
        :type level: int
        :param buff: The message itself.
        :type buff: str

        """
        if level == mqttc.MQTT_LOG_DEBUG:
            logger.debug(buff)
        elif level == mqttc.MQTT_LOG_ERR:
            logger.error(buff)
        elif level == mqttc.MQTT_LOG_WARNING:
            logger.warning(buff)
        elif level == mqttc.MQTT_LOG_NOTICE or level == mqttc.MQTT_LOG_INFO:
            logger.info(buff)

    def remove_topic(self, topic=None):
        """Remove a message callback previously registered with message_callback_add().

        :param topic: a string specifying the subscription topic to subscribe to.
        :type topic: str
        """
        self.client.message_callback_remove(topic)

    def add_topic(self, topic=None, callback=None):
        """Register a message callback for a specific topic.

        Messages that match 'topic' will be passed to 'callback'. Any
        non-matching messages will be passed to the default on_message
        callback.

        Call multiple times with different 'sub' to define multiple topic
        specific callbacks.

        Topic specific callbacks may be removed with message_callback_remove().

        :param topic: a string specifying the subscription topic to subscribe to.
        :type topic: str
        :param callback: the function called when a message arrived.
        :type callback: func
        """
        #mqttc.message_callback_add("$SYS/broker/messages/#", on_message_msgs)
        #mqttc.message_callback_add("$SYS/broker/bytes/#", on_message_bytes)
        self.client.message_callback_add(topic, callback)

    def subscribe(self, topic=None, topics=None, qos=0, callback=None):
        """Subscribe to a topic

        This function may be called in three different ways:

        Simple string and integer
        -------------------------
        e.g. subscribe("my/topic", 2)

        topic: A string specifying the subscription topic to subscribe to.
        qos: The desired quality of service level for the subscription.
             Defaults to 0.

        String and integer tuple
        ------------------------
        e.g. subscribe(("my/topic", 1))

        topic: A tuple of (topic, qos). Both topic and qos must be present in
               the tuple.
        qos: Not used.

        List of string and integer tuples
        ------------------------
        e.g. subscribe([("my/topic", 0), ("another/topic", 2)])

        This allows multiple topic subscriptions in a single SUBSCRIPTION
        command, which is more efficient than using multiple calls to
        subscribe().

        topic: A list of tuple of format (topic, qos). Both topic and qos must
               be present in all of the tuples.
        qos: Not used.

        :param topic: a string specifying the subscription topic to subscribe to.
        :type topic: str
        :param qos: the desired quality of service level for the subscription. Defaults to 0.
        :type qos: int
        :param callback: the function called when a message arrived.
        :type callback: func
        """
        #self.client.subscribe("$SYS/#", 0)
        self.client.on_message = callback
        if type(topics) == type([]):
            self.client.subscribe(topics)
        else:
            self.client.subscribe(topic, qos)
        logger.debug("[%s] - Subscribe to %s or %s", self.__class__.__name__, topic, topics)

    def unsubscribe(self, topic):
        """Unsubscribe the client from one or more topics.

        :param topic: a string specifying the subscription topic to subscribe to.
        :type topic: str

        Raises a ValueError if topic is None or has zero string length, or is not a string or list.
        """
        self.client.unsubscribe(topic)

    def subscribe_reply(self, uuid=None, qos=0, callback=None):
        """Subscribe to the reply mechanisme

        :param uuid: An uuid.
        :type uuid: str
        :param qos: the desired quality of service level for the subscription. Defaults to 0.
        :type qos: int
        :param callback: the function called when a message arrived.
        :type callback: func
        """
        if uuid is None:
            uuid = str(muuid.uuid1())
        self.subscribe(topic='/reply/'+uuid, callback=callback)
        return uuid

    def unsubscribe_reply(self, uuid):
        """Unsubscribe the client from one or more topics.

        :param topic: a string specifying the subscription topic to subscribe to.
        :type topic: str

        Raises a ValueError if topic is None or has zero string length, or is not a string or list.
        """
        self.remove_topic(topic='/reply/'+uuid)

    def publish_reply(self, uuid, payload=None, qos=0, retain=False):
        """Publish an uuid reply to clients.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        :param uuid: The uuid sent in the request.
        :type uuid: str
        :param payload: The actual message to send. If not given, or set to None a
                        zero length message will be used. Passing an int or float will result
                        in the payload being converted to a string representing that number. If
                        you wish to send a true int/float, use struct.pack() to create the
                        payload you require.
        :type payload: message
        :param qos: The quality of service level to use.
        :type qos: int
        :param retain: If set to true, the message will be set as the "last known good"/retained message for the topic.
        :type retain: bool
        """
        self.publish(topic="/reply/"+uuid, payload=payload, qos=qos, retain=retain)

    def publish(self, topic, payload=None, qos=0, retain=False):
        """Publish a message on a topic.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        :param topic: The topic that the message should be published on.
        :type topic: str
        :param payload: The actual message to send. If not given, or set to None a
                        zero length message will be used. Passing an int or float will result
                        in the payload being converted to a string representing that number. If
                        you wish to send a true int/float, use struct.pack() to create the
                        payload you require.
        :type payload: message
        :param qos: The quality of service level to use.
        :type qos: int
        :param retain: If set to true, the message will be set as the "last known good"/retained message for the topic.
        :type retain: bool
        """
        self.client.publish(topic, payload, qos, retain)

    def publish_heartbeat(self, add_ctrl, add_node, state='ONLINE', qos=0, retain=False):
        """Publish an heartbeat for the node add_ctrl, add_node.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        :param uuid: The uuid sent in the request.
        :type uuid: str
        :param payload: The actual message to send. If not given, or set to None a
                        zero length message will be used. Passing an int or float will result
                        in the payload being converted to a string representing that number. If
                        you wish to send a true int/float, use struct.pack() to create the
                        payload you require.
        :type payload: message
        :param qos: The quality of service level to use.
        :type qos: int
        :param retain: If set to true, the message will be set as the "last known good"/retained message for the topic.
        :type retain: bool
        """
        self.client.publish_heartbeat(add_ctrl, add_node, state=state, qos=qos, retain=retain)

    def publish_heartbeat_controller(self, add_ctrl, state='ONLINE', qos=0, retain=False):
        """Publish an heartbeat for the controller add_ctrl and all its nodes.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        :param uuid: The uuid sent in the request.
        :type uuid: str
        :param payload: The actual message to send. If not given, or set to None a
                        zero length message will be used. Passing an int or float will result
                        in the payload being converted to a string representing that number. If
                        you wish to send a true int/float, use struct.pack() to create the
                        payload you require.
        :type payload: message
        :param qos: The quality of service level to use.
        :type qos: int
        :param retain: If set to true, the message will be set as the "last known good"/retained message for the topic.
        :type retain: bool
        """
        msg = {'add_ctrl':add_ctrl, 'add_node':-1}
        self.client.publish_heartbeat_controller(add_ctrl, state=state, qos=qos, retain=retain)

    def publish_heartbeat_msg(self, msg, qos=0, retain=False):
        """Publish an heartbeat message.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        :param uuid: The uuid sent in the request.
        :type uuid: str
        :param payload: The actual message to send. If not given, or set to None a
                        zero length message will be used. Passing an int or float will result
                        in the payload being converted to a string representing that number. If
                        you wish to send a true int/float, use struct.pack() to create the
                        payload you require.
        :type payload: message
        :param qos: The quality of service level to use.
        :type qos: int
        :param retain: If set to true, the message will be set as the "last known good"/retained message for the topic.
        :type retain: bool
        """
        #Deprecated. We must send the heart to /dhcp/heartbeat/0011/0001
        self.client.publish_heartbeat_msg(msg, qos=qos, retain=retain)

    def publish_heartbeat_resolv_msg(self, msg, qos=0, retain=False):
        """Publish an heartbeat message.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        :param uuid: The uuid sent in the request.
        :type uuid: str
        :param payload: The actual message to send. If not given, or set to None a
                        zero length message will be used. Passing an int or float will result
                        in the payload being converted to a string representing that number. If
                        you wish to send a true int/float, use struct.pack() to create the
                        payload you require.
        :type payload: message
        :param qos: The quality of service level to use.
        :type qos: int
        :param retain: If set to true, the message will be set as the "last known good"/retained message for the topic.
        :type retain: bool
        """
        self.client.publish_heartbeat_resolv_msg(msg, qos=qos, retain=retain)

    def publish_value(self, hadd, value, genre='user', qos=0, retain=False):
        """Publish a value.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        :param uuid: The uuid sent in the request.
        :type uuid: str
        :param payload: The actual message to send. If not given, or set to None a
                        zero length message will be used. Passing an int or float will result
                        in the payload being converted to a string representing that number. If
                        you wish to send a true int/float, use struct.pack() to create the
                        payload you require.
        :type payload: message
        :param qos: The quality of service level to use.
        :type qos: int
        :param retain: If set to true, the message will be set as the "last known good"/retained message for the topic.
        :type retain: bool
        """
        #~ print "publish_value : ", hadd, value, genre
        if genre in ["user", "basic", "config"]:
            #For user values with indexes send all instance
            res = value.to_json_with_indexes()
        else:
            res = value.to_json()
        logger.debug('[%s] - Publish new value to /value/%s : %s', self.__class__.__name__, hadd, res)
        self.client.publish_value(hadd, value, genre=genre, qos=qos, retain=retain)

    def run(self):
        """Run the loop
        """
        #print "Start run"
        rc = 0
        while rc == 0 and not self._stopevent.isSet():
            try:
                rc = self.client.loop_forever()
            except Exception:
                logger.warning("[%s] - Exception in run : %s", self.__class__.__name__, traceback.format_exc())
        #~ self.client.loop_forever(retry_first_connection=False)
        self.client = None

    def stop(self):
        """Stop the mqtt thread
        """
        logger.debug("[%s] - Stop the mqtt client", self.__class__.__name__)
        self._stopevent.set( )
        if self.client is not None:
            self.client.disconnect()

    def connect(self):
        """Connect to the mqtt broker
        """
        logger.info("[%s] - Connect the mqtt client", self.__class__.__name__)
        return self.client.connect_with_options()
