# -*- coding: utf-8 -*-
"""The component

An I2C device, ...
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
__copyright__ = "Copyright © 2013-2014 Sébastien GALLET aka bibi21000"

import logging
logger = logging.getLogger(__name__)
from pkg_resources import resource_filename, Requirement, iter_entry_points

from janitoo.utils import JanitooNotImplemented, HADD
from janitoo.node import JNTNode

class JNTComponent(object):
    def __init__(self, oid='generic.generic', bus=None, addr=None, **kwargs):
        """Initialise the component

        :param oid: The oid implemented by the component.
        :type oid: str
        """
        self.name = kwargs.pop('name', 'The name of the node')
        self.product_name = kwargs.pop('product_name', 'The product_name of the node')
        self.product_type = kwargs.pop('product_type', 'The product_type of the node')
        self.product_manufacturer = kwargs.pop('product_manufacturer', 'The product_manufacturer of the node')
        self.oid = oid
        self._bus = bus
        self._addr = addr
        self.values = {}
        self.cmd_classes = []
        self.node = None
        self.mqttc = None
        self.options = kwargs.get('options', {})
        if self._bus is None:
            self.value_factory = {}
            for entrypoint in iter_entry_points(group = 'janitoo.values'):
                self.value_factory[entrypoint.name] = entrypoint.load()
        else:
            self.value_factory = self._bus.value_factory

    @property
    def uuid(self):
        """Return an uuid for the component

        """
        return "%s" % (self._addr)

    def loop(self, stopevent):
        """loop

        """
        pass

    def check_heartbeat(self):
        """Check that the component is 'available'

        """
        if self._bus is not None:
            return self._bus.check_heartbeat()
        return False

    def start(self, mqttc):
        """Start the component. Can be used to start a thread to acquire data.

        """
        self.mqttc = mqttc
        return True

    def stop(self):
        """Stop the component.

        """
        return True

    def create_node(self, hadd, **kwargs):
        """Create a node associated to this component
        """
        cb_check_hearbeat = self.check_heartbeat
        try:
            ret = cb_check_hearbeat()
        except NotImplementedError:
            cb_check_hearbeat = None
        self.node = JNTNode(uuid=self.uuid, cmd_classes=self.cmd_classes, hadd=hadd,
                name=self.name, product_name=self.product_name, product_type=self.product_type, product_manufacturer=self.product_manufacturer,
                check_hearbeat_cb=cb_check_hearbeat, oid=self.oid, **kwargs)
        return  self.node

    def value_poll_get(self, node_uuid, index, prefix=''):
        """
        """
        value_id = '%s_%s'%(prefix,'poll')
        temp_poll = self._bus.nodeman.options.get_option("%s"%node_uuid, value_id)
        if temp_poll is not None:
            try:
                self.node.values[value_id].poll_delay = int(temp_poll)
            except ValueError:
                logger.exception('Exception when retrieving poll temperature')
        #~ print "%s" % self.node.values
        return self.node.values[value_id].poll_delay

    def value_poll_set(self, node_uuid, index, value, prefix=''):
        """
        """
        try:
            value_id = '%s_%s'%(prefix,'poll')
            self.node.values[value_id].poll_delay = int(value)
            self._bus.nodeman.add_poll(self.node.values[value_id])
            self._bus.nodeman.options.set_option("%s"%node_uuid, value_id, '%s'%self.node.values[value_id].poll_delay)
        except ValueError:
            pass

    def resource_filename(self, path='public'):
        """Needed to publish static files
        """
        return resource_filename(Requirement.parse(self.get_package_name().split('.')[0]), path)

    def get_package_name(self):
        """Return the name of the package. Needed to publish static files

        **MUST** be copy paste in every extension that publish statics files
        """
        return __package__
