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

import logging
logger = logging.getLogger(__name__)

from janitoo.utils import json_dumps
from janitoo.value import JNTValue

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

class JNTValueFactoryEntry(JNTValue):
    """Implement a value entry for the factory. Used to create complex values.
    """
    def __init__(self, uuid="value_entry_uuid", **kwargs):
        """
        """
        self.entry_name = kwargs.pop('entry_name', 'an_entry_name')
        self.options = kwargs.pop('options', None)
        JNTValue.__init__(self, entry_name = "value_entry_name", uuid=uuid, **kwargs)
        self.instances = {}
        self._keys = {}
        """The different instances of the values (indexed on index)
        """

    def create_config_value(self, **kwargs):
        """
        """
        return self._create_config_value(**kwargs)

    def create_poll_value(self, **kwargs):
        """
        """
        return self._create_poll_value(**kwargs)

    def _create_config_value(self, **kwargs):
        """Create a config value associated to the main value
        """
        index = kwargs.pop('index', 0)
        help = kwargs.pop('help', 'A value config')
        label = kwargs.pop('label', 'config')
        uuid = kwargs.pop('uuid', '%s_%s' % (self.uuid,'config'))
        type = kwargs.pop('type', 0x02)
        get_data_cb = kwargs.pop('get_data_cb', self.get_config)
        set_data_cb = kwargs.pop('set_data_cb', self.set_config)
        return JNTValue(uuid=uuid, help=help, label=label,
            index=index, type=type,
            get_data_cb=get_data_cb, set_data_cb=set_data_cb,
            cmd_class=COMMAND_CONFIGURATION, genre=0x03, is_writeonly=False, is_readonly=False,
            master_config_value=self)

    def set_config(self, node_uuid, index, data):
        """
        """
        if index not in self.instances:
            self.instances[index] = {}
        try:
            if 'config' not in self.instances[index] or self.instances[index]['config'] != data:
                self.instances[index]['config'] = data
                self.options.set_option(node_uuid, '%s_%s_%s'%(self.uuid, 'config', index), data)
        except Exception:
            logger.exception('[%s] - Exception when writing %s_%s_%s for node %s', self.__class__.__name__, self.uuid, 'config', index, node_uuid)

    def get_config(self, node_uuid, index):
        """
        """
        if index not in self.instances:
            self.instances[index] = {}
        if 'config' not in self.instances[index]:
            self.instances[index]['config'] = None
        if index != 0:
            if self.instances[index]['config'] is None:
                try:
                    self.instances[index]['config'] = self.options.get_option(node_uuid, '%s_%s_%s'%(self.uuid, 'config', index))
                except Exception:
                    logger.exception('[%s] - Exception when retrieving %s_%s_%s for node %s', self.__class__.__name__, self.uuid, 'config', index, node_uuid)
        else:
            stopped = False
            i = 0
            while not stopped:
                try:
                    data = self.options.get_option(node_uuid, '%s_%s_%s'%(self.uuid, 'config', i))
                    #~ print "get data", self.uuid, data
                    if data is not None:
                        if i not in self.instances:
                            self.instances[i] = {}
                        self.instances[i]['config'] = data
                        i += 1
                    else:
                        stopped = True
                except Exception:
                    logger.exception('[%s] - Exception when retrieving %s_%s_%s for node %s', self.__class__.__name__, self.uuid, 'config', i, node_uuid)
        if index not in self.instances:
            return None
        return self.instances[index]['config']

    def _create_poll_value(self, **kwargs):
        """Create a poll value associated to the main value
        """
        index = kwargs.pop('index', 0)
        help = kwargs.pop('help', 'The poll delay of the value')
        label = kwargs.pop('label', 'poll_delay')
        uuid = kwargs.pop('uuid', '%s_%s' % (self.uuid,'poll'))
        default = kwargs.pop('default', 30)
        self._update_poll(default)
        units = kwargs.pop('units', "seconds")
        get_data_cb = kwargs.pop('get_data_cb', self._get_poll)
        set_data_cb = kwargs.pop('set_data_cb', self._set_poll)
        return JNTValue(uuid=uuid, help=help, label=label,
            index=index, units=units, poll_delay=default,
            get_data_cb=get_data_cb, set_data_cb=set_data_cb,
            cmd_class=COMMAND_CONFIGURATION, genre=0x03, type=0x04, is_writeonly=False, is_readonly=False)

    def _update_poll(self, data):
        """
        """
        if data > 0:
            self.is_polled = True
            self.poll_delay = data
        else:
            self.is_polled = False
            self.poll_delay = 0

    def _set_poll(self, node_uuid, index, data):
        """
        """
        try:
            if index not in self.instances:
                self.instances[index] = {}
            if index not in self.instances or self.instances[index]['poll'] != int(data):
                self.instances[index]['poll'] = int(data)
                self.options.set_option(node_uuid, '%s_%s_%s'%(self.uuid, 'poll', index), data)
                if index == 0:
                    self._update_poll(self.instances[index]['poll'])
        except Exception:
            logger.exception('[%s] - Exception when writing %s_%s_%s for node %s', self.__class__.__name__, self.uuid, 'poll', index, node_uuid)

    def _get_poll(self, node_uuid, index):
        """
        """
        if index not in self.instances:
            self.instances[index] = {}
        if 'poll' not in self.instances[index]:
            self.instances[index]['poll'] = None
        if self.instances[index]['poll'] is None:
            try:
                data = self.options.get_option(node_uuid, '%s_%s_%s'%(self.uuid, 'poll', index))
                if data is None:
                    data = self.poll_delay
                data = int(data)
                self.instances[index]['poll'] = data
                if index == 0:
                    self._update_poll(data)
                return data
            except Exception:
                logger.exception('[%s] - Exception when retrieving %s_%s_%s for node %s', self.__class__.__name__, self.uuid, 'poll', index, node_uuid)
        return self.instances[index]['poll']

    def get_length(self, node_uuid=None):
        """Returns the number of defindes instances
        """
        ret = []
        i=0
        stopped = False
        while not stopped :
            if i in self.instances and \
               ( ('config' in self.instances[i] and self.instances[i]['config'] is not None) or \
                 ('data' in self.instances[i] and self.instances[i]['data'] is not None) ):
                ret.append(self.instances[i])
                i += 1
            else:
                stopped = True
        return len(ret)

    def get_max_index(self, node_uuid=None):
        """
        """
        return len(self.get_index_configs())-1

    def get_index_configs(self):
        """
        """
        ret = []
        if len(self.instances) > 0 :
            #~ print "_instances", self.instances
            i=0
            stopped = False
            while not stopped :
                if i in self.instances  and 'config' in self.instances[i] and self.instances[i]['config'] is not None:
                    ret.append(self.instances[i]['config'])
                    i += 1
                else:
                    stopped = True
        #~ print "ret of index_configs", ret
        return ret

    def get_data_index(self, node_uuid=None, index=None, config=None):
        """
        """
        try:
            if node_uuid is None:
                node_uuid = self.node_uuid
            if config is not None:
                configs = self.get_index_configs()
                i = 0
                for conf in configs:
                    if config == conf:
                        index = i
                        break
                    i += 1
            if index is None:
                index = self.index
            if index not in self.instances:
                self.instances[index] = {'data':None, 'config':None}
            if 'data' not in self.instances[index]:
                self.instances[index]['data'] = None
            if self.instances[index]['data'] is None and self.genre == 0x03:
                #It's a config, try to retrieve option from config
                self.instances[index]['data'] = self.convert(self.options.get_option(node_uuid, '%s_%s'%(self.uuid, index)))
            if self._data is not None:
                self.instances[index]['data'] = self._data
            if self.instances[index]['data'] is None:
                self.instances[index]['data'] = self.default
            return self.instances[index]['data']
        except Exception:
            logger.exception('[%s] - Exception when retrieving %s_%s_%s for node %s', self.__class__.__name__, self.uuid, 'poll', index, node_uuid)
        return self.default

    def set_data_index(self, node_uuid=None, index=None, config=None, data=None):
        """
        """
        if node_uuid is None:
            node_uuid = self.node_uuid
        if config is not None:
            configs = self.get_index_configs()
            i = 0
            for conf in configs:
                if config == conf:
                    index = i
                    break
                i += 1
        if index is None:
            index = self.index
        if index not in self.instances:
            self.instances[index] = {}
        if 'data' not in self.instances[index]:
            self.instances[index]['data'] = None
        #~ print index, self.instances[index]['data'], data
        try:
            #~ self.instances[index]['data'] = self.default
            if node_uuid is None:
                node_uuid = self.node_uuid
            if index is None:
                index = self.index
            self.instances[index]['data'] = data
            if index == 0:
                self._data = data
            #~ print "Ok"
            if self.genre == 0x03:
                #~ print "Ok", '%s_%s'%(self.uuid, index)
                self.options.set_option(node_uuid, '%s_%s'%(self.uuid, index), data)
            #~ print index, self.instances[index]['data']
        except Exception:
            logger.exception('[%s] - Exception when setting %s_%s_%s for node %s', self.__class__.__name__, self.uuid, 'data', index, node_uuid)

    def to_dict_with_index(self, index, initial=None):
        """Retrieve a json version of the value
        """
        if initial is None:
            initial = JNTValue.to_dict(self)
        configs = self.get_index_configs()
        res = {}
        res.update(initial)
        #~ print "len(configs)", len(configs)
        if len(configs) == 0:
            return res
        res['index'] = index
        res['label'] = "%s (%s)" % (res['label'], configs[index])
        if index in self.instances and 'data' in self.instances[index]:
            res['data'] = self.instances[index]['data']
        elif self._get_data_cb is not None:
            res['data'] = self._get_data_cb(self.node_uuid, index)
        else:
            res['data'] = self.default
        if res['data'] is None:
            res['data'] = self.default
        #~ print "---------------------------------------------------------- res ", res
        return res

    def to_dict_with_indexes(self):
        """Retrieve a dict version of the value
        """
        res = JNTValue.to_dict(self)
        #~ print "self.instances[0] %s"%self.instances[0]
        #~ print "---------------------------------------------------------- self.get_max_index() ", self.get_max_index()
        #~ print "---------------------------------------------------------- self.instances ", self.instances
        if self.get_max_index() == -1 or 'config' not in self.instances[0]:
            return res
        if self.get_max_index() == -1 or self.instances[0]['config'] is None:
            return {}
        ret = {}
        try:
            #~ configs = self.get_index_configs()
            #~ print "self.get_index_configs() %s"%configs
            i = 0
            #~ print i, res['label']
            #~ print i, '%s'%self.instances
            #~ print i, '%s'%self.instances[i]
            while i <= self.get_max_index():
                #~ print "---------------------------------------------------------- i ", i
                #~ print i, res['label'], configs[i]
                ret[i] = self.to_dict_with_index(i, res)
                i += 1
        except Exception:
            logger.exception('[%s] - Exception in to_dict_with_indexes', self.__class__.__name__)
        #~ print "---------------------------------------------------------- ret ", ret
        return ret

    def to_json_with_indexes(self):
        """Retrieve a json version of the value
        """
        try:
            res = self.to_dict_with_indexes()
            #~ print "to_json_with_indexes", res
            return json_dumps(res)
        except Exception:
            logger.exception('[%s] - Exception in to_json_with_indexes', self.__class__.__name__)
        return None
