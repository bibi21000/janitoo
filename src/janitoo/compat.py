# -*- coding: utf-8 -*-
"""
    janitoo.compat
    ~~~~~~~~~~~~~~

"""

_license__ = """
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


from six.moves import range as range_type, zip as izip
from six import PY2, PY3, text_type, string_types
import codecs
import sys
import operator
import functools
import warnings

_identity = lambda x: x

if PY2:

    def to_bytes(x, charset=sys.getdefaultencoding(), errors='strict'):
        if x is None:
            return None
        if isinstance(x, (bytes, bytearray, buffer)):
            return bytes(x)
        if isinstance(x, unicode):
            return x.encode(charset, errors)
        raise TypeError('Expected bytes')

    def to_native(x, charset=sys.getdefaultencoding(), errors='strict'):
        if x is None or isinstance(x, string_types):
            return x
        return x.encode(charset, errors)

    def to_str(x, charset=sys.getdefaultencoding(), errors='strict'):
        return x

    import ConfigParser as configparser
    from configparser import RawConfigParser, NoOptionError, NoSectionError

    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from SimpleHTTPServer import SimpleHTTPRequestHandler

    from SocketServer import ThreadingMixIn
    
    from urllib import unquote

else:

    def to_bytes(x, charset=sys.getdefaultencoding(), errors='strict'):
        if x is None:
            return None
        if isinstance(x, (bytes, bytearray, memoryview)):  # noqa
            return bytes(x)
        if isinstance(x, string_types):
            return x.encode(charset, errors)
        raise TypeError('Expected bytes')

    def to_native(x, charset=sys.getdefaultencoding(), errors='strict'):
        if x is None or isinstance(x, string_types):
            return x
        return x.decode(charset, errors)

    def to_str(x, charset=sys.getdefaultencoding(), errors='strict'):
        if x is None or isinstance(x, string_types):
            return x
        return x.decode(charset, errors)

    import configparser
    from configparser import RawConfigParser, NoOptionError, NoSectionError

    from http.server import HTTPServer, BaseHTTPRequestHandler
    from http.server import SimpleHTTPRequestHandler

    from socketserver import ThreadingMixIn

    from urllib.parse import unquote

def to_unicode(x, charset=sys.getdefaultencoding(), errors='strict',
               allow_none_charset=False):
    if x is None:
        return None
    if not isinstance(x, bytes):
        return text_type(x)
    if charset is None and allow_none_charset:
        return x
    return x.decode(charset, errors)
