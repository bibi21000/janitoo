# -*- coding: utf-8 -*-

"""The classes

Largely inspired from https://github.com/OpenZWave/open-zwave/tree/master/cpp/src/command_classes

The capabilites of the nodes or the controller

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

"""
A machine can implement one or more command classes
"""

CAPABILITY_DESC = {
        0x00: 'CAPABILITY_NO_OPERATION',
        0x01: 'CAPABILITY_PRIMARY_CONTROLLER',
        0x02: 'CAPABILITY_STATIC_UPDATE_CONTROLLER',
        0x03: 'CAPABILITY_BRIDGE_CONTROLLER',
        0x04: 'CAPABILITY_DYNAMIC_CONTROLLER', #Full management using dhcp
        0x05: 'CAPABILITY_TINY_CONTROLLER',    #Full management using dhcp for arduino and friends. Limit the size of message to 128,256 or 512 bytes
        0x10: 'CAPABILITY_ROUTING',
        0x20: 'CAPABILITY_LISTENING',
        0x21: 'CAPABILITY_FREQUENT',
        0x50: 'CAPABILITY_SECURITY',
        0x60: 'CAPABILITY_BEAMING',
        0x80: 'CAPABILITY_SLEEPING',
}

COMMAND_DESC = {
#OpenZWave
        0x0000: 'COMMAND_NO_OPERATION',
        0x0020: 'COMMAND_BASIC',
        0x0021: 'COMMAND_CONTROLLER_REPLICATION',
        0x0022: 'COMMAND_APPLICATION_STATUS',
        0x0023: 'COMMAND_ZIP_SERVICES',
        0x0024: 'COMMAND_ZIP_SERVER',
        0x0025: 'COMMAND_SWITCH_BINARY',
        0x0026: 'COMMAND_SWITCH_MULTILEVEL',
        0x0027: 'COMMAND_SWITCH_ALL',
        0x0028: 'COMMAND_SWITCH_TOGGLE_BINARY',
        0x0029: 'COMMAND_SWITCH_TOGGLE_MULTILEVEL',
        0x002A: 'COMMAND_CHIMNEY_FAN',
        0x002B: 'COMMAND_SCENE_ACTIVATION',
        0x002C: 'COMMAND_SCENE_ACTUATOR_CONF',
        0x002D: 'COMMAND_SCENE_CONTROLLER_CONF',
        0x002E: 'COMMAND_ZIP_CLIENT',
        0x002F: 'COMMAND_ZIP_ADV_SERVICES',
        0x0030: 'COMMAND_SENSOR_BINARY',
        0x0031: 'COMMAND_SENSOR_MULTILEVEL',
        0x0032: 'COMMAND_METER',
        0x0033: 'COMMAND_CLASS_COLOR',
        0x0034: 'COMMAND_ZIP_ADV_CLIENT',
        0x0035: 'COMMAND_METER_PULSE',
        0x003C: 'COMMAND_METER_TBL_CONFIG',
        0x003D: 'COMMAND_METER_TBL_MONITOR',
        0x003E: 'COMMAND_METER_TBL_PUSH',
        0x0038: 'COMMAND_THERMOSTAT_HEATING',
        0x0040: 'COMMAND_THERMOSTAT_MODE',
        0x0042: 'COMMAND_THERMOSTAT_OPERATING_STATE',
        0x0043: 'COMMAND_THERMOSTAT_SETPOINT',
        0x0044: 'COMMAND_THERMOSTAT_FAN_MODE',
        0x0045: 'COMMAND_THERMOSTAT_FAN_STATE',
        0x0046: 'COMMAND_CLIMATE_CONTROL_SCHEDULE',
        0x0047: 'COMMAND_THERMOSTAT_SETBACK',
        0x004c: 'COMMAND_DOOR_LOCK_LOGGING',
        0x004E: 'COMMAND_SCHEDULE_ENTRY_LOCK',
        0x0050: 'COMMAND_BASIC_WINDOW_COVERING',
        0x0051: 'COMMAND_MTP_WINDOW_COVERING',
        0x0060: 'COMMAND_MULTI_CHANNEL_V2',
        0x0061: 'COMMAND_DISPLAY',
        0x0062: 'COMMAND_DOOR_LOCK',
        0x0063: 'COMMAND_USER_CODE',
        0x0064: 'COMMAND_GARAGE_DOOR',
        0x0070: 'COMMAND_CONFIGURATION',
        0x0071: 'COMMAND_ALARM',
        0x0072: 'COMMAND_MANUFACTURER_SPECIFIC',
        0x0073: 'COMMAND_POWERLEVEL',
        0x0075: 'COMMAND_PROTECTION',
        0x0076: 'COMMAND_LOCK',
        0x0077: 'COMMAND_NODE_NAMING',
        0x0078: 'COMMAND_ACTUATOR_MULTILEVEL',
        0x0079: 'COMMAND_KICK',
        0x007A: 'COMMAND_FIRMWARE_UPDATE_MD',
        0x007B: 'COMMAND_GROUPING_NAME',
        0x007C: 'COMMAND_REMOTE_ASSOCIATION_ACTIVATE',
        0x007D: 'COMMAND_REMOTE_ASSOCIATION',
        0x0080: 'COMMAND_BATTERY',
        0x0081: 'COMMAND_CLOCK',
        0x0082: 'COMMAND_HAIL',
        0x0083: 'COMMAND_NETWORK_STAT',
        0x0084: 'COMMAND_WAKE_UP',
        0x0085: 'COMMAND_ASSOCIATION',
        0x0086: 'COMMAND_VERSION',
        0x0087: 'COMMAND_INDICATOR',
        0x0088: 'COMMAND_PROPRIETARY',
        0x0089: 'COMMAND_LANGUAGE',
        0x008A: 'COMMAND_TIME',
        0x008B: 'COMMAND_TIME_PARAMETERS',
        0x008C: 'COMMAND_GEOGRAPHIC_LOCATION',
        0x008D: 'COMMAND_COMPOSITE',
        0x008E: 'COMMAND_MULTI_INSTANCE_ASSOCIATION',
        0x008F: 'COMMAND_MULTI_CMD',
        0x0090: 'COMMAND_ENERGY_PRODUCTION',
        0x0091: 'COMMAND_MANUFACTURER_PROPRIETARY',
        0x0092: 'COMMAND_SCREEN_MD',
        0x0093: 'COMMAND_SCREEN_ATTRIBUTES',
        0x0094: 'COMMAND_SIMPLE_AV_CONTROL',
        0x0095: 'COMMAND_AV_CONTENT_DIRECTORY_MD',
        0x0096: 'COMMAND_AV_RENDERER_STATUS',
        0x0097: 'COMMAND_AV_CONTENT_SEARCH_MD',
        0x0098: 'COMMAND_SECURITY',
        0x0099: 'COMMAND_AV_TAGGING_MD',
        0x009A: 'COMMAND_IP_CONFIGURATION',
        0x009B: 'COMMAND_ASSOCIATION_CONFIGURATION',
        0x009C: 'COMMAND_SENSOR_ALARM',
        0x009D: 'COMMAND_SILENCE_ALARM',
        0x009E: 'COMMAND_SENSOR_CONFIGURATION',
        0x00EF: 'COMMAND_MARK',
        0x00F0: 'COMMAND_NON_INTEROPERABLE',

#janitoo
        0x1000: 'COMMAND_DHCPD',
        0x1001: 'COMMAND_DHCPC',
        0x1040: 'COMMAND_UPDATE',
        0x1050: 'COMMAND_CONTROLLER',
        0x1051: 'COMMAND_NETWORK_CONTROLLER',
        0x1060: 'COMMAND_NDDE',
        0x1010: 'COMMAND_EVENT_ACTIVATION',
        0x1011: 'COMMAND_EVENT_ACTUATOR_CONF',
        0x1012: 'COMMAND_EVENT_CONTROLLER_CONF',
        0x1020: 'COMMAND_SCENARIO_ACTIVATION',
        0x1021: 'COMMAND_SCENARIO_ACTUATOR_CONF',
        0x1022: 'COMMAND_SCENARIO_CONTROLLER_CONF',
        0x1030: 'COMMAND_WEB_CONTROLLER',
        0x1031: 'COMMAND_WEB_RESOURCE',
        0x1032: 'COMMAND_DOC_RESOURCE',
        0x10A0: 'COMMAND_JMI',
        0x10B0: 'COMMAND_FSM',

#roomba
        0x2000: 'COMMAND_ROOMBA_VACUUM',
        0x2001: 'COMMAND_ROOMBA_DRIVE',

#samsung
        0x2100: 'COMMAND_AV_CHANNEL',
        0x2101: 'COMMAND_AV_VOLUME',
        0x2102: 'COMMAND_AV_SOURCE',

#camera
        0x2200: 'COMMAND_CAMERA_PREVIEW',
        0x2201: 'COMMAND_CAMERA_PHOTO',
        0x2202: 'COMMAND_CAMERA_VIDEO',
        0x2203: 'COMMAND_CAMERA_STREAM',

#datalog
        0x2800: 'COMMAND_LOG',

#
        0x3000: 'COMMAND_BUTTON_BINARY',
        0x3001: 'COMMAND_BUTTON_MULTILEVEL',
        0x3002: 'COMMAND_BUTTON_ALL',
        0x3010: 'COMMAND_NOTIFY',

#motor
        0x3100: 'COMMAND_MOTOR',

#shutter
        0x3150: 'COMMAND_SHUTTER_BINARY',
        0x3151: 'COMMAND_SHUTTER_MULTILEVEL',
        0x3152: 'COMMAND_SHUTTER_ALL',
#bell
        0x3155: 'COMMAND_BELL',

#screen
        0x3200: 'COMMAND_SCREEN_DRAW',
        0x3201: 'COMMAND_SCREEN_MESSAGE',
        0x3202: 'COMMAND_SCREEN_CLEAR',
        0x3203: 'COMMAND_BLINK',
        0x3204: 'COMMAND_UPDOWN',

#System command
        0x5000: 'COMMAND_DISCOVERY'
    }

GENRE_DESC = {
    0x01 : {'label':'Basic', 'doc':"The 'level' as controlled by basic commands."},
    0x02 : {'label':'User', 'doc':"Values an ordinary user would be interested in."},
    0x03 : {'label':'Config', 'doc':"Device-specific configuration parameters."},
    0x04 : {'label':'System', 'doc':"Values of significance only to users who understand the Janitoo protocol"},
    0x05 : {'label':'Command', 'doc':"Send a complex command to the controller. Used for advanced configuration"},
    }

VALUE_DESC = {
    0x01 : {'label':'Bool', 'doc':"Boolean, true or false"},
    0x02 : {'label':'Byte', 'doc':"8-bit unsigned value"},
    0x03 : {'label':'Decimal', 'doc':"Represents a non-integer value as a string, to avoid floating point accuracy issues."},
    0x04 : {'label':'Int', 'doc':"32-bit signed value"},
    0x05 : {'label':'List', 'doc':"List from which one item can be selected"},
    0x06 : {'label':'Schedule', 'doc':"Complex type used with the Climate Control Schedule command class"},
    0x07 : {'label':'Short', 'doc':"16-bit signed value"},
    0x08 : {'label':'String', 'doc':"Text string"},
    0x09 : {'label':'Button', 'doc':"A write-only value that is the equivalent of pressing a button to send a command to a device"},
    0x10 : {'label':'Raw', 'doc':"Raw byte values"},
    0x14 : {'label':'Password', 'doc':"A password"},
    0x15 : {'label':'Json', 'doc':"A JSON representation of a complex type"},
    0x16 : {'label':'Array', 'doc':"An array repsented as values separated by pipe"},
    0x17 : {'label':'Var', 'doc':"A variable type used by remote values."},
    0x20 : {'label':'HADD', 'doc':"An hadd ie 1111/0000"},
    0x21 : {'label':'IP', 'doc':"An ip adress ie 192.168.1.1"},
    0x30 : {'label':'RGB', 'doc':"RGB color represented as bytes separated by # : bbb#bbb#bbb"},
    }
