# -*- coding: utf-8 -*-
"""The bus

A physical or logical bus : i2c, 1-wire, thermal, ...
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
#~ logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)

from pkg_resources import iter_entry_points
import subprocess
import threading

from janitoo.node import JNTNode
from janitoo.compat import str_to_native

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_CONTROLLER = 0x1050

assert(COMMAND_DESC[COMMAND_CONTROLLER] == 'COMMAND_CONTROLLER')
##############################################################
##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import CAPABILITY_DESC

CAPABILITY_DYNAMIC_CONTROLLER = 0x04

assert(CAPABILITY_DESC[CAPABILITY_DYNAMIC_CONTROLLER] == 'CAPABILITY_DYNAMIC_CONTROLLER')
##############################################################

class JNTBus(object):
    """A bus holds components
    A bus is mapped in a controller node

    Bus aggregation
    ---------------
    A master bus can aggregate multiple bus to hold different compenents on the same bus.

    Look at janitoo_raspberry_fishtank, janitoo_lapinoo, ...

    Bus extension
    ---------------
    A bus can be extended to add new features, shared resource, ...

    Look at janitoo_raspberry_spi, janitoo_raspberry_i2c and janitoo_raspberry_i2c_pca9865, janitoo_events and janitoo_events_cron, ...

    """
    def __init__(self, oid='generic', **kwargs):
        """Initialise the bus
        A bus can define values to configure itself.
        A bus can agregate other bus. Values from the buss are exported to the master.
        So they must be prefixed by the oid of the bus (in a hard way not usinf self.oid)

        :param oid: The oid implemented by the bus.
        :type oid: str
        """
        self.oid = oid
        if not hasattr(self,'factory'):
            self.factory = {}
            for entry in iter_entry_points(group='janitoo.components', name=None):
                if entry.name.startswith('%s.'%self.oid):
                    try:
                        self.factory[entry.name] = entry.load()
                    except Exception:
                        logger.exception('[%s] - Exception when loading entry_point %s', self.__class__.__name__,  entry.name)
        if not hasattr(self,'value_factory'):
            self.value_factory = {}
            for entrypoint in iter_entry_points(group = 'janitoo.values'):
                try:
                    self.value_factory[entrypoint.name] = entrypoint.load()
                except Exception:
                    logger.exception('[%s] - Exception when loading entry_point %s', self.__class__.__name__,  entrypoint.name)
        if not hasattr(self,'components'):
            self.components = {}
        if not hasattr(self,'values'):
            self.values = {}
        if not hasattr(self,'cmd_classes'):
            self.cmd_classes = [COMMAND_CONTROLLER]
        if not hasattr(self,'capabilities'):
            self.capabilities = [CAPABILITY_DYNAMIC_CONTROLLER]
        self._trigger_thread_reload_cb = None
        self.mqttc = None
        self.options = kwargs.get('options', None)
        """The options"""
        self.product_name = kwargs.get('product_name', 'Default product name')
        """The product name of the node"""
        self.product_type = kwargs.get('product_type', 'Default product type')
        """The product type of the node"""
        self.name = kwargs.get('name', 'Default bus name')
        """The name"""
        self.nodeman = None
        self._masters = kwargs.get('masters', [])
        if not isinstance(self._masters, type([])):
            self._masters = [ self._masters ]
        self.is_started = False

    def __del__(self):
        """
        """
        try:
            self.stop()
        except Exception:
            pass

    def cant_aggregate(self, oid):
        """
        """
        if self.oid != oid:
            raise RuntimeError("This bus can't be aggregated.")

    def get_bus_value(self, value_uuid, oid = None):
        '''Retrieve a bus's private value. Take care of exported buses
        This is the preferred way to retrieve a value of the bus
        '''
        #~ logger.debug("[%s] - Look for value %s on bus %s", self.__class__.__name__, value_uuid, self)
        #~ if value_uuid in self.values:
            #~ return self.values[value_uuid]
        if oid is None:
            oid = self.oid
        value_uuid = "%s_%s"%(oid, value_uuid)
        if value_uuid in self.values:
            return self.values[value_uuid]
        return None

    def export_values(self):
        '''Export values to all targets'''
        logger.debug("[%s] - Export values to all buses", self.__class__.__name__)
        for target in self._masters:
            for value in list(self.values.keys()):
                #~ nvalue = value.replace('%s_'%OID,'%s_'%target.oid)
                #~ logger.debug("[%s] - Export value %s to bus %s (twice is %s)", self.__class__.__name__, value, target, nvalue)
                logger.debug("[%s] - Export value %s to bus %s", self.__class__.__name__, value, target)
                target.values[value] = self.values[value]
                #~ target.values[nvalue] = self.values[value]

    def export_attrs(self, objname, obj):
        '''Export object to all targets'''
        logger.debug("[%s] - Export attrs to all buses", self.__class__.__name__)
        for target in self._masters:
            if hasattr(target, objname):
                logger.error("[%s] - Collision found on attribute %s. Continue anyway by overriding.", self.__class__.__name__, objname)
            setattr(target, objname, obj)

    def clean_attrs(self, objname):
        '''Clean exported object from all targets'''
        logger.debug("[%s] - Clean attrs to all buses", self.__class__.__name__)
        for target in self._masters:
            if hasattr(target, objname):
                delattr(target, objname)
            else:
                logger.warning("[%s] - Missing attribute found %s when cleaning. Continue anyway.", self.__class__.__name__, objname)

    def update_attrs(self, objname, obj):
        '''Update object to all targets'''
        logger.debug("[%s] - Update attrs to all buses", self.__class__.__name__)
        for target in self._masters:
            setattr(target, objname, obj)

    def start(self, mqttc, trigger_thread_reload_cb=None, **kwargs):
        """Start the bus
        Components will be started by the nodemanager after retrieving configuration.
        """
        logger.debug("[%s] - Start the bus", self.__class__.__name__)
        self.export_values()
        self._trigger_thread_reload_cb = trigger_thread_reload_cb
        self.mqttc = mqttc
        self.is_started = True
        return self.is_started

    def stop(self, **kwargs):
        """Stop the bus and components"""
        logger.debug("[%s] - Stop the bus", self.__class__.__name__)
        if self.is_started:
            self.is_started = False
            for compo in list(self.components.keys()):
                self.components[compo].stop()
                del self.components[compo]
        return True

    @property
    def uuid(self):
        """Return an uuid for the bus. Must be the same as the section name to retrieve the hadd of the controller

        """
        return "%s" % self.oid

    def loop(self, stopevent):
        """Loop
        Don't do long task in loop. Use a separated thread to not perturbate the nodeman

        """
        pass

    def add_component(self, oid, addr, **kwargs):
        """Add a component on the bus

        """
        if addr in self.components:
            return False
        if oid not in self.factory:
            logger.warning("[%s] - Can't find %s in factory", self.__class__.__name__, oid)
            return None
        compo = self.factory[oid](addr=addr, bus=self, **kwargs)
        self.components[addr] = compo
        return compo

    def find_components(self, component_oid):
        """Find components using an oid
        """
        components = [ self.components[addr] for addr in self.components if self.components[addr].oid == component_oid ]
        return components

    def find_values(self, component_oid, value_uuid):
        """Find a value using its uuid and the component oid
        """
        components = self.find_components(component_oid)
        if len(components)==0:
            return []
        res = []
        for component in components:
            if component.node is not None:
                for value in component.node.values:
                    if component.node.values[value].uuid == value_uuid:
                        res.append(component.node.values[value])
        return res

    def create_node(self, nodeman, hadd, **kwargs):
        """Create a node associated to this bus
        """
        self.nodeman = nodeman
        name = kwargs.pop('name', "%s controller"%self.name)
        self.node = JNTNode( uuid=self.uuid,
            cmd_classes=self.cmd_classes,
            capabilities=self.capabilities,
            hadd=hadd,
            name=name,
            product_name=self.product_name,
            product_type=self.product_type,
            oid=self.oid,
            **kwargs)
        #~ self.check_heartbeat = self.node.check_heartbeat
        return self.node

    def check_heartbeat(self):
        """Check that the bus is 'available'. Is replaced by the node one when it's creates

        """
        return False

    def get_components(self):
        """Retrieve components from a section
        """
        return self.options.get_options_key(self.section, "components.")

    def extend_from_entry_points(self, oid, eps=None):
        """"Extend the bus with methods found in entrypoints
        """
        if eps is None:
            return
        for entrypoint in iter_entry_points(group = '%s.extensions'%oid):
            if entrypoint.name in eps:
                logger.info('[%s] - Extend bus with oid %s extension %s', self.__class__.__name__, oid, entrypoint.module_name )
                extend = entrypoint.load()
                extend( self )

    def load_extensions(self, oid):
        """"Load extensions from config file.
        """
        logger.debug('[%s] - Load bus extensions %s in section %s', self.__class__.__name__, oid, self.oid )
        try:
            exts = self.options.get_option(self.oid, 'extensions', default="").split(',')
        except Exception:
            logger.warning("[%s] - Can't load_extensions", self.__class__.__name__, exc_info=True)
            exts = []
        self.extend_from_entry_points(oid, exts)

    def kernel_modprobe(self, module, params=''):
        """Load a kernel module. Needs to be root (raspberry)

        :param str module: the kernel module to load
        :param str params: module parameters
        """
        try:
            cmd = '/sbin/modprobe %s %s' % (module, params)
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            stdout = [x for x in stdout.split(str_to_native("\n")) if x != ""]
            stderr = [x for x in stderr.split(str_to_native("\n")) if x != ""]
            if process.returncode < 0 or len(stderr):
                for error in stderr:
                    logger.error(error)
            else:
                return True
        except Exception:
            logger.exception("Can't load kernel module %s", module)

    def kernel_rmmod(self, module):
        """Remove a kernel module. Needs to be root (raspberry)

        :param str module: the kernel module to remove
        """
        try:
            cmd = '/sbin/rmmod %s' % (module)
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            stdout = [x for x in stdout.split(str_to_native("\n")) if x != ""]
            stderr = [x for x in stderr.split(str_to_native("\n")) if x != ""]
            if process.returncode < 0 or len(stderr):
                for error in stderr:
                    logger.error(error)
            else:
                return True
        except Exception:
            logger.exception("Can't remove kernel module %s", module)

    def stop_buses(self, buses, **kwargs):
        event = kwargs.get('event', threading.Event())
        for bus in self.buses:
            self.buses[bus].stop()
            event.wait(0.05)
