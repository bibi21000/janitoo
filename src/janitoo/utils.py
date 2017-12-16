# -*- coding: utf-8 -*-
"""The common utils

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

from datetime import datetime
import json
from bson import json_util
import warnings
import codecs

from janitoo.compat import to_str

import logging
logger = logging.getLogger(__name__)

HADD = "%0.4d/%0.4d"
CADD = "%0.4d/"
HADD_SEP = "/"

TOPIC_HEARTBEAT = "/dhcp/heartbeat/#"
TOPIC_HEARTBEAT_NODE = "/dhcp/heartbeat/%s/#"
TOPIC_RESOLV_REQUEST = "/dhcp/resolv/request/"
TOPIC_RESOLV_REPLY = "/dhcp/resolv/reply/%s"
TOPIC_RESOLV_BROADCAST = "/dhcp/resolv/broadcast/"
TOPIC_RESOLV = "/dhcp/resolv/"
TOPIC_NODES = "/nodes/%s"
TOPIC_NODES_REPLY = "/nodes/%s/reply"
TOPIC_NODES_REQUEST = "/nodes/%s/request"
TOPIC_BROADCAST_REPLY = "/broadcast/reply/%s"
TOPIC_BROADCAST_REQUEST = "/broadcast/request"
TOPIC_VALUES = "/values/#"
TOPIC_VALUES_USERS = "/values/user/#"
TOPIC_VALUES_USER = "/values/user/%s"
TOPIC_VALUES_CONFIG = "/values/config/%s"
TOPIC_VALUES_SYSTEM = "/values/system/%s"
TOPIC_VALUES_COMMAND = "/values/command/%s"
TOPIC_VALUES_BASIC = "/values/basic/%s"

NETWORK_REQUESTS = ['request_info_nodes', 'request_info_users', 'request_info_configs', 'request_info_systems', 'request_info_basics', 'request_info_commands']

def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emmitted
    when the function is used."""
    def new_func(*args, **kwargs):
        warnings.simplefilter('always', DeprecationWarning)#turn off filter
        warnings.warn("Call to deprecated function {}.".format(func.__name__),
                      category=DeprecationWarning, stacklevel=2)
        warnings.simplefilter('default', DeprecationWarning) #reset filter
        return func(*args, **kwargs)
    new_func.__name__ = func.__name__
    new_func.__doc__ = func.__doc__
    new_func.__dict__.update(func.__dict__)
    return new_func

class JanitooException(Exception):
    """
    Exception class for Janitoo
    """
    def __init__(self, exx="Janitoo Exception", message=''):
        Exception.__init__(self, exx)
        self.message = message

    def __str__(self):
        return repr(self.message)

class JanitooNotImplemented(JanitooException):
    """
    Not Implemented Exception class for Janitoo
    """
    def __init__(self, message=''):
        JanitooException.__init__(self, "Janitoo Not Implemented Exception", message=message, )

class JanitooRuntime(JanitooException):
    """
    Runtime Exception class for Janitoo
    """
    def __init__(self, message=''):
        JanitooException.__init__(self, "Janitoo Runtime Exception", message=message, )


def json_dumps(data_as_object):
    return json.dumps(data_as_object, default=json_util.default)

def json_loads(data_as_string):
    return json.loads(to_str(data_as_string), object_hook=json_util.object_hook)

def hadd_split(hadd):
    sadd_ctrl,sadd_node = hadd.split(HADD_SEP)
    try:
        add_ctrl = int(sadd_ctrl)
    except ValueError:
        logger.debug("[%s] - mqtt_on_heartbeat can't convert add_ctrl %s to integer", self.__class__.__name__, sadd_ctrl)
        return None, None
    try:
        add_node = int(sadd_node)
    except ValueError:
        logger.debug("[%s] - mqtt_on_heartbeat can't convert add_node %s to integer", self.__class__.__name__, sadd_node)
        return None, None
    return add_ctrl, add_node
