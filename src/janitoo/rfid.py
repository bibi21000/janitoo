# -*- coding: utf-8 -*-
"""The RFID format for Janitoo

https://github.com/adafruit/Adafruit_Python_PN532/blob/master/examples/mcpi_write.py
https://www.itead.cc/blog/to-drive-itead-pn532-nfc-module-with-raspberry-pi

We got almost 64 blocks of 16 bytes on the card.
It seems that we could authenticate and read one block at a time.

2 choices :

 - we use each block separatly :

        rfid[0] : the version
        rfid[1] : 0
        rfid[2] : type
        rfid[3] : subtype
        rfid[4] : control
        rfid[5] : 0
        rfid[6:..] : specific

    but :
        - how to know how many tags are available on the card

 - we use the first block as a block allocation table :

  - type, subtype -> block

We can mix many subtypes (ie admin + access) combining bits

The specific part wil be a token which allow :
 - to check againt a pki that the token is valid for this card, this type and subtype.
 - to allow specific thinks : ie when presence is sleeping and watchdog, se should activate presence detector on outiside zone.
 -
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
import os

INVALID = 0b00000000
INVALID_BLOCK = [ INVALID, INVALID, INVALID, INVALID ]

TYPES = {
    0b10000000 : {
        'uid' : 'security',
        'subtypes' : {
            0b10000000 : 'access',
            0b01000000 : 'admin',
        }
    },
    0b01000000 : {
        'uid' : 'learning',
        'subtypes' : {
            0b10000000 : 'voice',
        }
    },
    0b11000000 : {
        'uid' : 'presence',
        'subtypes' : {
            0b10000000 : 'watchdog',
            0b01000000 : 'occupied',
            0b00100000 : 'sleeping',
            0b00010000 : 'hibernate',
            0b00001000 : 'vacancy',
            0b00000100 : 'simulation',
        }
    },
}

def decode_rfid_block(rfid_bytes):
    """ Try to decode a bytearray in a Janitoo RFID block
        :returns: A block
    """
    block = RFIDBlock()
    return block.from_bytes(rfid_bytes)

def decode_rfid_tag(reader):
    """ Try to decode RFID blocks on an RFID tag
    """
    block = RFIDTag()
    return block.from_reader(reader)

class RFIDBlock00(object):
    """ A RFID card version 0
    We should allow multiple version format.
    """

    def __init__(self, **kwargs):
        """
        """
        self.factory = {}
        self.version = kwargs.pop('version', INVALID)
        self.current_version = kwargs.pop('current_version', INVALID)
        self.key_type = kwargs.pop('key_type', INVALID)
        self.key_subtype = kwargs.pop('key_subtype', INVALID)
        self.message = kwargs.pop('message', bytearray(10))

    def to_bytes(self, upgrade=False):
        """Convert message to a byte array
        If uograde is True, the message is udpdated to current version.
        """
        version = self.version
        if upgrade:
            version = self.current_version
        if version in self.factory:
            return self.factory[version]['to_bytes'](upgrade=upgrade)
        return None

    def from_bytes(self, data):
        """Import data from a byte array
        """
        if data is None:
            return None
        version = self.get_version(data)
        if version is not None:
            return self.factory[version]['from_bytes'](data)
        return None

    def get_version(self, data):
        """Extract version from a byte array
        """
        vers = data[0]
        if vers in self.factory:
            return vers
        return None

class RFIDBlock01(RFIDBlock00):
    """ An RFID card version 1
    """

    def __init__(self, **kwargs):
        """
        """
        version = kwargs.pop('version', 0b00000001)
        current_version = kwargs.pop('current_version', 0b00000001)
        RFIDBlock00.__init__(self, version=version, current_version=current_version, **kwargs)
        self.factory[0b00000001] = {
            'to_bytes':self._to_bytes_1,
            'from_bytes':self._from_bytes_1,
        }

    def _to_bytes_1(self, upgrade=False):
        """Convert data to a byte array to be stored on rfid card
        """
        data = bytearray(16)
        data[0] = 0b00000001
        data[1] = INVALID
        data[2] = self.key_type
        data[3] = self.key_subtype
        data[4] = INVALID
        data[5] = INVALID
        data[6:] = self.message
        return data

    def _control_1(self, header):
        """Control that header is conform to version 1
        """
        if header[0] != 0b00000001:
            return False

        if header[1] != INVALID:
            return False

        if header[2] not in TYPES:
            return False

        if header[3] not in TYPES[header[2]]['subtypes']:
            return False

        if header[4] != INVALID:
            return False

        if header[5] != INVALID:
            return False
        return True

    def _from_bytes_1(self, data):
        """Import data from a byte array stored on card
        """
        if self._control_1(data):
            self.version = 0b00000001
            self.key_type = data[2]
            self.key_subtype = data[3]
            self.message = data[6:]
            return self
        return None

class RFIDBlock(RFIDBlock01):
    """ A RFID block
    This is the interface to be use by developpers
    """
    pass

class RFIDTag(object):
    """ A RFID tag
    Can contain up to 64 blocks.

    The reader and writer callbacks :

    def writer(blockid, blockdata):

        - should return True if everything isk ok

    def reader(blockid):

        - return bytesarray or None if no (more) data

    """

    def __init__(self, **kwargs):
        """
        """
        self.blocks = kwargs.pop('blocks', [])

    def to_writer(self, writer, upgrade=False):
        """Send the tag to the writer
        """
        idx=0
        for block in self.blocks:
            if writer(idx, block.to_bytes(upgrade=upgrade)):
                idx += 1
            else:
                break

    def erase(self, writer, full=False):
        """Format the tag for Janitoo
        if full, erase all blocks
        """
        writer(0, INVALID_BLOCK)
        self.blocks = []

    def from_reader(self, reader):
        """Retrieve tag from reader
        """
        gotit = True
        idx=0
        while gotit:
            data = reader(idx)
            block = decode_rfid_block(data)
            if block is None:
                gotit = False
            else:
                self.blocks.append(block)
                idx += 1
        return self
