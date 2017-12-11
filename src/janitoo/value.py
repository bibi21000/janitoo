# -*- coding: utf-8 -*-
"""The value

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

from janitoo.classes import GENRE_DESC, VALUE_DESC
from janitoo.utils import json_dumps
from janitoo.options import JNTOptions, string_to_bool

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_CONFIGURATION = 0x0070
COMMAND_SENSOR_BINARY = 0x0030
COMMAND_SENSOR_MULTILEVEL = 0x0031

assert(COMMAND_DESC[COMMAND_CONFIGURATION] == 'COMMAND_CONFIGURATION')
assert(COMMAND_DESC[COMMAND_SENSOR_BINARY] == 'COMMAND_SENSOR_BINARY')
assert(COMMAND_DESC[COMMAND_SENSOR_MULTILEVEL] == 'COMMAND_SENSOR_MULTILEVEL')
##############################################################

class JNTValue(object):
    def __init__(self, uuid="a_unik_identifier_for_the_value_on_the_controller", node_uuid="the_unik_identifier_of_the_node", get_data_cb = None, set_data_cb = None, **kwargs):
        """
        :param int uuid: the unique uuid of the value on the controller
        """
        self.uuid = uuid
        """The UUID of the value"""
        self.node_uuid = node_uuid
        """The UUID of the node the valuse is attached to"""
        self.voice_uuid = kwargs.get('voice_uuid', None)
        """The voice_uuid of this value. Can be use to a"""
        self.hadd = kwargs.get('hadd', None)
        """The HADD of the node associated to this value"""
        self.cmd_class = kwargs.get('cmd_class', 0x0000)
        """The command class implemented by the value"""
        self.is_readonly = kwargs.get('is_readonly', True)
        """Is the value readonly"""
        self.is_writeonly = kwargs.get('is_writeonly', True)
        """Is the value writeonly"""
        self.default = kwargs.get('default', None)
        """The default data of the value"""
        self.label = kwargs.get('label', None)
        """The help of the value"""
        self.help = kwargs.get('help', None)
        """The label of the value"""
        self.units = kwargs.get('units', None)
        """The units of the value"""
        self.list_items = kwargs.get('list_items', None)
        """The list of all valid items when the value type is list. This list is separated with pipe : '|'"""
        self.max = kwargs.get('max', None)
        """The max of the value"""
        self.min = kwargs.get('min', None)
        """The min of the value"""
        self.genre = kwargs.get('genre', 0x01)
        """The genre of the value"""
        self.type = kwargs.get('type', 0x01)
        """The type of the value"""
        self.index = kwargs.get('index', 0)
        """Get the value index (use with multi_instance nodes)"""
        self.is_polled = kwargs.get('is_polled', False)
        """Say if the value is polled"""
        self.poll_delay = kwargs.get('poll_delay', 0)
        """The delay between 2 polls"""
        self._get_data_cb = get_data_cb
        """The callback to get the value"""
        self._set_data_cb = set_data_cb
        """The callback to get the value"""
        self._data = None
        """The last known data of the value"""
        self.reply_hadd = None
        """The hadd to reply to"""
        self.master_config_value = kwargs.get('master_config_value', None)
        """The master_value. Used with value_factory entries"""

    def convert(self, data):
        """
        Convert data to the type of value

        :return: The data of the value
        :rtype: depending of the type of the value

        """
        if data is not None:
            try:
                if self.type == 0x01:
                    #Bool
                    return string_to_bool(data)
                elif self.type == 0x02 or self.type == 0x04 or self.type == 0x07:
                    #Byte or Int or Short
                    return int(data)
                elif self.type == 0x03:
                    #Decimal
                    return float(data)
                elif self.type == 0x08:
                    #String
                    return data
                elif self.type == 0x16:
                    #Array
                    return data.split('|')
                logger.warning('[%s] - Do not convert data %s to %s.', self.__class__.__name__, data, VALUE_DESC[self.type]['label'])
                return data
            except Exception:
                logger.exception('[%s] - Exception when converting data %s to %s', self.__class__.__name__, data, VALUE_DESC[self.type]['label'])
                return None
        return None

    @property
    def data(self):
        """
        Get the current data of the value.

        :return: The data of the value
        :rtype: depending of the type of the value

        """
        if self._get_data_cb is not None:
            self._data = self._get_data_cb(self.node_uuid, self.index)
        if self._data is None:
            self._data = self.default
        return self._data

    @data.setter
    def data(self, value):
        """
        Set the data of the value.

        Best practice: Use check_data before setting it:

        new_val = value.check_data(some_data)
        if new_val != None:
            value.data = new_val

        :param value: The new data value
        :type value:

        """
        res = True
        if self._set_data_cb is not None:
            res = self._set_data_cb(self.node_uuid, self.index, value)
        if res == True:
            self._data = value
        return res

    def start(self):
        """Start the value. Can be used to start a thread to acquire data.
        This method is not called in the nodeman process.
        Programmer must call it manually, ie at stat machine change.

        """
        return True

    def stop(self):
        """Stop the value.
        This method is not called in the nodeman process.
        Programmer must call it manually, ie at stat machine change.

        """
        return True

    def from_dict(self, adict):
        """Update internal dict from adict
        """
        self.__dict__.update(adict)
        return self

    def to_dict(self):
        """Retrieve a dict version of the value.
        Include all properties except :
         - ends with lock, _cb,
         - starts with timer, _
        So use the naming convention above or ask for update if you really need it.

        """
        res = {}
        res.update(self.__dict__)
        for key in list(res.keys()):
            if key.endswith('lock') or key.endswith('_cb') \
              or key.startswith('_') or key.startswith('timer') \
              or key in ['instances', 'options', 'master_config_value']:
                del res[key]
        res['data'] = self.data
        return res

    def to_json(self):
        """Retrieve a json version of the value
        """
        res = self.to_dict()
        return json_dumps(res)

def value_system_heartbeat(get_data_cb, set_data_cb):
    return JNTValue( uuid='heartbeat',
        help='The heartbeat delay in seconds',
        label='heartbeat',
        units='seconds',
        index=0,
        cmd_class=COMMAND_CONFIGURATION,
        genre=0x04,
        max=3000,
        min=0,
        type=0x04,
        is_readonly=False,
        is_writeonly=False,
        is_polled=False,
        poll_delay=0,
        get_data_cb = get_data_cb,
        set_data_cb = set_data_cb
    )

def value_system_config_timeout(get_data_cb, set_data_cb):
    return JNTValue( uuid='config_timeout',
        help='The config timeout before applying configuration and rebooting',
        label='config_timeout',
        units='seconds',
        index=0,
        cmd_class=COMMAND_CONFIGURATION,
        genre=0x04,
        max=3000,
        min=0,
        type=0x04,
        is_readonly=False,
        is_writeonly=False,
        is_polled=False,
        poll_delay=0,
        get_data_cb = get_data_cb,
        set_data_cb = set_data_cb
    )

def value_system_hadd(get_data_cb, set_data_cb):
    return JNTValue( uuid='hadd',
        help='The Janitoo Home address',
        label='hadd',
        units='',
        index=0,
        cmd_class=COMMAND_CONFIGURATION,
        genre=0x04,
        type=0x20,
        is_readonly=False,
        is_writeonly=False,
        is_polled=False,
        poll_delay=0,
        get_data_cb = get_data_cb,
        set_data_cb = set_data_cb
    )

def value_config_name(get_data_cb, set_data_cb):
    return JNTValue( uuid='name',
        help='The name of the node',
        label='name',
        index=0,
        cmd_class=COMMAND_CONFIGURATION,
        genre=0x03,
        type=0x08,
        is_readonly=False,
        is_writeonly=False,
        is_polled=False,
        poll_delay=0,
        get_data_cb = get_data_cb,
        set_data_cb = set_data_cb
    )

def value_config_location(get_data_cb, set_data_cb):
    return JNTValue( uuid='location',
        help='The location of the node',
        label='location',
        index=0,
        cmd_class=COMMAND_CONFIGURATION,
        genre=0x03,
        type=0x08,
        is_readonly=False,
        is_writeonly=False,
        is_polled=False,
        poll_delay=0,
        get_data_cb = get_data_cb,
        set_data_cb = set_data_cb
    )

def value_config_poll(uuid, get_data_cb, set_data_cb, help='The poll delay of the value', label="poll_delay", index=0, default = 300):
    return JNTValue( uuid=uuid,
        help=help,
        label=label,
        index=index,
        cmd_class=COMMAND_CONFIGURATION,
        genre=0x03,
        type=0x04,
        is_readonly=False,
        is_writeonly=False,
        is_polled=False,
        default = default,
        poll_delay=0,
        get_data_cb = get_data_cb,
        set_data_cb = set_data_cb
    )
