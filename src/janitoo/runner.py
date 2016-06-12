# -*- coding: utf-8 -*-

"""The runner

Start a worker or a broker as a daemon.

Must be updated to work with multiple workers.

What do we need :

* the user ou userid
* the log file
* the error output
* the standard output
* the pid file
* the working directory

Based on the runner of python-daemon :

* Copyright © 2009–2010 Ben Finney <ben+python@benfinney.id.au>
* Copyright © 2007–2008 Robert Niederreiter, Jens Klein
* Copyright © 2003 Clark Evans
* Copyright © 2002 Noah Spurrier
* Copyright © 2001 Jürgen Hermann

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
__copyright__ = "Copyright © 2012-2013-2014-2015 Sébastien GALLET aka bibi21000"
__author__ = 'Sébastien GALLET aka bibi21000'
__email__ = 'bibi21000@gmail.com'

# Set default logging handler to avoid "No handler found" warnings.
import logging
logger = logging.getLogger(__name__)
import sys
import os
import os.path
import signal
import errno
import time
from daemon.pidfile import TimeoutPIDLockFile
from daemon import DaemonContext
import pwd
import socket
import argparse
#We must NOT subsitute % in value for alembic (database section)
from ConfigParser import RawConfigParser as ConfigParser

class RunnerError(Exception):
    """ Abstract base class for errors. """

class RunnerInvalidActionError(ValueError, RunnerError):
    """ Raised when specified action is invalid. """

class RunnerStartFailureError(RuntimeError, RunnerError):
    """ Raised when failure starting. """

class RunnerStopFailureError(RuntimeError, RunnerError):
    """ Raised when failure stopping. """

class Runner(object):
    """ Controller for a callable running in a separate background process.

    The first command-line argument is the action to take:

    * 'start': Become a daemon and call `app.run()`.
    * 'stop': Exit the daemon process specified in the PID file.
    * 'restart': Stop, then start.
    * 'status': Show the status of the process.

    """

    start_message = "started with pid %d"
    status_message_running = "process is running (%d)"
    status_message_not_running = "process is not running"

    def __init__(self, only_front=False):
        """ Set up the parameters of a new runner.

            The `app` argument must have the following attributes:

            * `stdin_path`, `stdout_path`, `stderr_path`: Filesystem
              paths to open and replace the existing `sys.stdin`,
              `sys.stdout`, `sys.stderr`.

            * `pidfile_path`: Absolute filesystem path to a file that
              will be used as the PID file for the daemon. If
              ``None``, no PID file will be used.

            * `pidfile_timeout`: Used as the default acquisition
              timeout value supplied to the runner's PID lock file.

        """
        self.options = {}
        self.pidfile_timeout = 6.0
        self.stdout_path = None
        self.stderr_path = None
        self.pidfile_path = None
        self.userid = None
        self.args = None
        self.parse_args(only_front=only_front)
        self.pidfile = None
        self.pidfile_path = os.path.join(self.options['pid_dir'], self.options['service'] + ".pid")
        self.pidfile = make_pidlockfile(
            self.pidfile_path, self.pidfile_timeout)
        if self.pidfile.is_locked() and not is_pidfile_stale(self.pidfile) \
          and self.action == 'start':
            print("Process already running. Exiting.")
            sys.exit(1)
        if (not self.pidfile.is_locked() or is_pidfile_stale(self.pidfile)) \
          and (self.action == 'stop' or self.action == 'kill'):
            print("Process not running. Exiting.")
            sys.exit(1)

    def app_run(self):
        """
        The running process of the application
        """
        raise RunnerInvalidActionError("Action: %(action)r is not implemented" % vars(self))

    def app_shutdown(self):
        """
        The shutdown process of the application
        """
        raise RunnerInvalidActionError("Action: %(action)r is not implemented" % vars(self))

    def _usage_exit(self, args):
        """ Emit a usage message, then exit.
        """
        usage_exit_code = 2
        message = "usage: use --help to get help" % vars()
        emit_message(message)
        sys.exit(usage_exit_code)

    def parse_args(self, only_front = False):
        """ Parse command-line arguments.
        """
        args = jnt_parse_args(only_front=only_front)
        self.options = vars(args)
        self.action = args.command
        self.args = args
        self.stdout_path = os.path.join(self.options['log_dir'], self.options['service'] + "_out.log")
        self.stderr_path = os.path.join(self.options['log_dir'], self.options['service'] + "_err.log")
        self.pidfile_path = os.path.join(self.options['pid_dir'], self.options['service'] + ".pid")
        if self.options['user'] and self.options['user'] != "":
            self.userid = pwd.getpwnam(self.options['user']).pw_uid
            if self.userid != os.getuid():
                #print self.userid
                os.setuid(self.userid)
        try:
            os.makedirs(self.options['pid_dir'])
            os.makedirs(self.options['home_dir'])
            os.makedirs(self.options['conf_dir'])
            os.makedirs(self.options['log_dir'])
        except OSError as exc: # Python >2.5
            if exc.errno == errno.EEXIST:
                pass
            else: raise
        if self.action not in self.action_funcs:
            self._usage_exit(args)

    def _start(self):
        """ Open the daemon context and run the application.
        """
        self.daemon_context = DaemonContext()
        self.daemon_context.pidfile = self.pidfile
        #self.daemon_context.stdin = open(stdin_path, 'r')
        self.daemon_context.stdout = open(self.stdout_path, 'w+')
        self.daemon_context.stderr = open(self.stderr_path, 'w+', buffering=0)
        if is_pidfile_stale(self.pidfile):
            self.pidfile.break_lock()
        #print "Here"
        try:
            self.daemon_context.open()
        except TimeoutPIDLockFile.AlreadyLocked:
            pidfile_path = self.pidfile.path
            raise RunnerStartFailureError(
                "PID file %(pidfile_path)r already locked" % vars())
        #print "Here 2"
        message = self.start_message % os.getpid()
        logger.info(message)
        #~ emit_message(message, self.daemon_context.stdout)
        self.app_run()

    def _front(self):
        """ Open the daemon context and run the application.
        """
        if is_pidfile_stale(self.pidfile):
            self.pidfile.break_lock()
        self.pidfile.__enter__()
        message = self.start_message %  os.getpid()
        logger.info(message)
        #~ emit_message(message, sys.stdout)
        try:
            self.app_run()
        except KeyboardInterrupt:
            pass
        finally:
            if self.pidfile:
                try:
                    self.pidfile.__exit__(None, None, None)
                except Exception:
                    pass
        self.app_shutdown()

    def _terminate_daemon_process(self):
        """ Terminate the daemon process specified in the current PID file.
            """
        pid = self.pidfile.read_pid()
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as exc:
            raise RunnerStopFailureError(
                "Failed to terminate %(pid)d: %(exc)s" % vars())

    def _kill_daemon_process(self):
        """ Terminate the daemon process specified in the current PID file.
            """
        pid = self.pidfile.read_pid()
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError, exc:
            raise RunnerStopFailureError(
                "Failed to kill %(pid)d: %(exc)s" % vars())

    def _stop(self):
        """ Exit the daemon process specified in the current PID file.
            """
        if self.pidfile.is_locked():
            if is_pidfile_stale(self.pidfile):
                self.pidfile.break_lock()
            else:
                self._terminate_daemon_process()

    def _kill(self):
        """Kill the daemon process specified in the current PID file.
        """
        if not self.pidfile.is_locked():
            pidfile_path = self.pidfile.path
            raise RunnerStopFailureError(
                "PID file %(pidfile_path)r not locked" % vars())

        if is_pidfile_stale(self.pidfile):
            self.pidfile.break_lock()
        else:
            self._kill_daemon_process()

    def _status(self):
        """Show the status of the process.
        """
        if not self.pidfile.is_locked() or is_pidfile_stale(self.pidfile):
            emit_message(self.status_message_not_running)
        else:
            emit_message(self.status_message_running % self.pidfile.read_pid())

    def _restart(self):
        """Stop, then start.
        """
        self._stop()
        time.sleep(self.pidfile_timeout)
        self._start()

    def _reload(self):
        """Reload application configuration.
        """
        pid = self.pidfile.read_pid()
        try:
            os.kill(pid, signal.SIGHUP)
        except OSError as exc:
            raise RunnerStopFailureError(
                "Failed to reload %(pid)d: %(exc)s" % vars())

    def _flush(self):
        """Flush data to disk via SIGUSR1 signal
        """
        pid = self.pidfile.read_pid()
        try:
            os.kill(pid, signal.SIGUSR1)
        except OSError as exc:
            raise RunnerStopFailureError(
                "Failed to flush %(pid)d: %(exc)s" % vars())

    action_funcs = {
        'start': _start,
        'stop': _stop,
        'restart': _restart,
        'reload': _reload,
        'kill': _kill,
        'status': _status,
        'flush': _flush,
        'front': _front,
        }

    def _get_action_func(self):
        """Return the function for the specified action.

        Raises ``RunnerInvalidActionError`` if the action is
        unknown.

        """
        try:
            func = self.action_funcs[self.action]
        except KeyError:
            raise RunnerInvalidActionError(
                "Unknown action: %(action)r" % vars(self))
        return func

    def do_action(self):
        """Perform the requested action.
        """
        func = self._get_action_func()
        func(self)

def emit_message(message, stream=None):
    """Emit a message to the specified stream (default `sys.stderr`).
    """
    if stream is None:
        stream = sys.stderr
    stream.write("%(message)s\n" % vars())
    stream.flush()

def make_pidlockfile(path, acquire_timeout):
    """Make a PIDLockFile instance with the given filesystem path.
    """
    if not isinstance(path, basestring):
        error = ValueError("Not a filesystem path: %(path)r" % vars())
        raise error
    if not os.path.isabs(path):
        error = ValueError("Not an absolute path: %(path)r" % vars())
        raise error
    lockfile = TimeoutPIDLockFile(path, acquire_timeout)
    return lockfile

def is_pidfile_stale(pidfile):
    """Determine whether a PID file is stale.

    Return ``True`` (“stale”) if the contents of the PID file are
    valid but do not match the PID of a currently-running process;
    otherwise return ``False``.
    """
    result = False
    pidfile_pid = pidfile.read_pid()
    if pidfile_pid is not None:
        try:
            os.kill(pidfile_pid, signal.SIG_DFL)
        except OSError, exc:
            if exc.errno == errno.ESRCH:
                # The specified PID does not exist
                result = True
    return result

def jnt_parse_args(only_front = False):
    """Default argument parser
    """
    conf_parser = argparse.ArgumentParser(
        # Turn off help, so we print all options in response to -h
            add_help=False
            )
    conf_parser.add_argument("-c", "--conf_file",
                             help="The configuration file", metavar="FILE")
    args, remaining_argv = conf_parser.parse_known_args()
    defaults = {
        "hostname" : socket.gethostname(),
        "service" : "jnt_generic",
        "user" : "janitoo",
        "log_dir" : "/tmp/jnt_logs",
        "home_dir" : "/tmp/jnt_home",
        "cache_dir" : "/tmp/jnt_cache",
        "pid_dir" : "/tmp/jnt_run",
        "conf_dir" : "/tmp/jnt_conf",
        "broker_ip" : "127.0.0.1",
        "broker_port" : "1883",
        "broker_user" : "",
        "broker_password" : "",
        }
    conf_file = None
    if args.conf_file:
        conf_file = args.conf_file
        config = ConfigParser()
        config.read([args.conf_file])
        if not os.path.isfile(args.conf_file):
            raise IOError("Can't find configuration file %s"%(args.conf_file))
        defaults = dict(config.items("system"))
        defaults['conf_file'] = conf_file
        if 'hostname' not in defaults or defaults['hostname'] is None:
            defaults['hostname'] = socket.gethostname()
    if conf_file is None:
        conf_file = os.path.expanduser("~/.janitoorc")
        config = ConfigParser()
        config.read([conf_file])
        if os.path.isfile(conf_file):
            defaults = dict(config.items("system"))
            defaults['conf_file'] = conf_file
            if 'hostname' not in defaults or defaults['hostname'] is None:
                defaults['hostname'] = socket.gethostname()
    # Don't surpress add_help here so it will handle -h
    parser = argparse.ArgumentParser(
        # Inherit options from config_parser
        parents=[conf_parser],
        # print script description with -h/--help
        description=__doc__,
        # Don't mess with format of description
        formatter_class=argparse.RawDescriptionHelpFormatter,
        )
    helpCommand = """
        start      start the service
        stop       stop the service
        restart    restart the service
        reload     reload the service
        kill       kill the service
        status     status of the service
        flush      flush data to disk
        front      don't run as daemon
    """
    if only_front:
        parser.add_argument('command', nargs='?',
                            choices=('front'),
                            default='front',
                            help=helpCommand)
    else:
        parser.add_argument('command', nargs='?',
                            choices=('start', 'stop', 'restart', 'reload', 'flush', 'kill', 'status', 'front'),
                            help=helpCommand)
    parser.set_defaults(**defaults)
    #parser.add_argument("--conf_file", help="the hostname used by the service. Leave blank to auto-configure.")
    parser.add_argument("--hostname", help="the hostname used by the service. Leave blank to auto-configure.")
    parser.add_argument("--service", help="the service name")
    parser.add_argument("--user", help="the user used to launch the service")
    parser.add_argument("--log_dir", help="the log directory")
    parser.add_argument("--pid_dir", help="the pid directory")
    parser.add_argument("--cache_dir", help="the cache directory")
    parser.add_argument("--home_dir", help="the home directory")
    parser.add_argument("--conf_dir", help="the conf directory")
    parser.add_argument("--broker_ip", help="the ip of the broker")
    parser.add_argument("--broker_port", help="the port of the broker")
    parser.add_argument("--broker_user", help="the user of the broker")
    parser.add_argument("--broker_password", help="the password of the broker")
    args = parser.parse_args(remaining_argv)
    return args

