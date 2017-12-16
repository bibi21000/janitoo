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

import uuid as muuid

#We must NOT subsitute % in value for alembic (database section)
from datetime import datetime, timedelta

from janitoo.compat import configparser
from janitoo.compat import NoOptionError, NoSectionError, RawConfigParser
from janitoo.utils import JanitooNotImplemented, HADD, HADD_SEP, CADD
from janitoo.mqtt import MQTTClient

class JNTOptions(object):
    def __init__(self, options=None):
        """The options

        :param options: The options used to start the worker.
        :type clientid: str
        """
        #retrieve parameters in file
        if options is not None:
            self.data = options
        else:
            self.data = {}
        self._cache = {}

    def load(self):
        """Load system section from file

        :param options: The options used to start the worker.
        :type clientid: str
        """
        #retrieve parameters in file
        system = self.get_options('system')
        self.data.update(system)

    def get_sections(self):
        """Retrieve all sections
        """
        try:
            if 'conf_file' in self.data and self.data['conf_file'] is not None:
                config = RawConfigParser()
                config.read([self.data['conf_file']])
                return config.sections()
        except Exception:
            logger.exception("Catched exception", self.__class__.__name__)
        return []

    def get_options(self, section):
        """Retrieve options from a section
        """
        #~ print self.data['conf_file']
        #~ print "section ", section, " in cache", section in self._cache
        #~ print "data ", self.data
        if section is None:
            return {}
        if section in self._cache:
            return self._cache[section]
        try:
            if 'conf_file' in self.data and self.data['conf_file'] is not None:
                config = RawConfigParser()
                config.read([self.data['conf_file']])
                #~ print "items ", config.items(section)
                self._cache[section] = dict(config.items(section))
                #~ print self._cache[section]
                return self._cache[section]
        except Exception:
            logger.exception("Catched exception", self.__class__.__name__)
        return {}

    def get_option(self, section, key, default = None):
        """Retrieve options from a section
        """
        #print self.data['conf_file']
        if section in self._cache and key in self._cache[section]:
            logger.debug("[%s] - get_option from cache : [%s] %s = %s", self.__class__.__name__, section, key, self._cache[section][key])
            return self._cache[section][key]
        if section not in self._cache:
            self.get_options(section)
            logger.debug("[%s] - get_options from section : [%s] %s", self.__class__.__name__, section, key)
            if section in self._cache and key in self._cache[section]:
                return self._cache[section][key]
        logger.debug("[%s] - get_options from file : [%s] %s", self.__class__.__name__, section, key)
        try:
            if 'conf_file' in self.data and self.data['conf_file'] is not None:
                config = RawConfigParser()
                config.read([self.data['conf_file']])
                opt = config.get(section, key)
                if default is None:
                    self._cache[section][key] = opt
                    return self._cache[section][key]
                else:
                    if type(default) == type(0):
                        try:
                            self._cache[section][key] = int(opt)
                            return self._cache[section][key]
                        except Exception:
                            logger.exception("[%s] - Exception when converting option to integer : [%s] %s = %s", self.__class__.__name__, section, key, opt)
                            return None
                    elif type(default) == type(0.0):
                        try:
                            self._cache[section][key] = float(opt)
                            return self._cache[section][key]
                        except Exception:
                            logger.exception("[%s] - Exception when converting option to float : [%s] %s = %s", self.__class__.__name__, section, key, opt)
                            return None
                    self._cache[section][key] = opt
                    return self._cache[section][key]
        except NoOptionError:
            return default
        except NoSectionError:
        #~ except ValueError:
            return default
        return None

    def set_option(self, section, key, value, create=False):
        """Set option in a section
        """
        if not create:
            if section not in self._cache:
                self.get_options(section)
        if 'conf_file' in self.data and self.data['conf_file'] is not None:
            config = RawConfigParser()
            config.read([self.data['conf_file']])
            if config.has_section(section) == False:
                config.add_section(section)
            if section not in self._cache:
                self._cache[section] = {}
            self._cache[section][key] = value
            config.set(section, key, "%s"%value)
            with open(self.data['conf_file'], 'w') as configfile:
                config.write(configfile)
                return True
        return False

    def set_options(self, section, data):
        """Retrieve options from a section
        """
        if section not in self._cache:
            self.get_options(section)
        #print self.data['conf_file']
        if 'conf_file' in self.data and self.data['conf_file'] is not None:
            config = RawConfigParser()
            config.read([self.data['conf_file']])
            if config.has_section(section) == False:
                config.add_section(section)
            if section not in  self._cache:
                 self._cache[section] = {}
            for key in data:
                self._cache[section][key] = data[key]
                config.set(section, key, "%s"%data[key])
            with open(self.data['conf_file'], 'w') as configfile:
                config.write(configfile)
                return True
        return False

    def remove_options(self, section, data):
        """Retrieve options from a section
        """
        #print self.data['conf_file']
        if 'conf_file' in self.data and self.data['conf_file'] is not None:
            config = RawConfigParser()
            config.read([self.data['conf_file']])
            for key in data:
                config.remove_option(section, key)
                if section in self._cache and key in self._cache[section]:
                    del self._cache[section][key]
            with open(self.data['conf_file'], 'w') as configfile:
                config.write(configfile)
                return True
        return False

    def remove_options(self, section):
        """Remove a n entire section
        """
        #print self.data['conf_file']
        if 'conf_file' in self.data and self.data['conf_file'] is not None:
            config = RawConfigParser()
            config.read([self.data['conf_file']])
            config.remove_section(section)
            with open(self.data['conf_file'], 'w') as configfile:
                config.write(configfile)
            if section in self._cache:
                del self._cache[section]
            return True
        return False

    def get_options_key(self, section, key, strict=False):
        """Retrieve options which started with a key from a section
        """
        #print self.data['conf_file']
        res = {}
        options = self.get_options(section)
        debi = len(key)
        for okey in list(options.keys()):
            if (strict == True and okey == key) or okey.startswith(key):
                res[okey[debi:]] = options[okey]
        return res

    def get_settings(self, section):
        """Retrieve settings from a section
        """
        return self.get_options_key(section, "settings.")

    def get_component_settings(self, section, component):
        """Retrieve component's configuration from a section
        """
        return self.get_options_key("%s.%s"%(section,component), "settings.")


def get_option_autostart(options, section):
    """Retrieve auto_start option from a section
    """
    #print self.data['conf_file']
    if 'conf_file' in options and options['conf_file'] is not None:
        config = RawConfigParser()
        config.read([options['conf_file']])
        try:
            return config.getboolean(section, 'auto_start')
        except NoOptionError:
            return False
        except NoSectionError:
            return False
    return False

def string_to_bool(data):
    """Convert a string to bool
    """
    if type(data) == type(True):
        return data
    data = data.strip().upper()
    if data == "0" or data == "FALSE" or data == 'OFF' or data == 'NO':
        return False
    return True
