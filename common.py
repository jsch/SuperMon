#! /usr/bin/env python3
# -*- coding:utf-8 -*-
# -*- python -*-

"""Application common constants, functions"""

from datetime import datetime, timedelta
import logging
import sys

# Default HTTP port
HTTP_PORT = 8080

# Status refresh period in seconds
REFRESH_PERIOD = 60

# Application parameters
PARAMS = {
    'http_port': HTTP_PORT,
    'refresh_period': REFRESH_PERIOD
}

# Status
OK = 'ok'
ERROR = 'error'

# Heartbeat message and period in seconds
HEARTBEAT_MESSAGE = 'HEART_<3_BEAT'
HEARTBEAT_PERIOD = 10
INTERNAL_ZMQ_EVENT_CNX = 'inproc://internal-event'

# Active session check period (in seconds)
SESSION_CHECK_PERIOD = 10
MAX_MISSED_CHECKS = 3

##
# API and supervisor actors commands
CMD_KEEP_ALIVE = 'keep_alive'
CMD_DIAGNOSTICS = 'diag'
CMD_ASK_SERVER = 'ask'
CMD_GET_INDEX = 'get_index'

CMD_GET_PROCESSES_NAMES = 'get_processes_names'
CMD_GET_PROCESS_INFO = 'get_process_info'
CMD_GET_ALL_PROCESSES_INFO = 'get_all_processes_info'
CMD_REFRESH_ALL_PROCESSES_INFO = 'refresh_all_processes_info'
CMD_GET_INFO = 'get_info'
CMD_TIMER = 'timer'
CMD_STOP_ACTOR = 'stop_actor'
CMD_START_MONITOR = 'start_monitor'
CMD_STOP_MONITOR = 'stop_monitor'

CMD_RESTART_GLOB = 'restart_glob'
CMD_START_GLOB = 'start_glob'
CMD_STOP_GLOB = 'stop_glob'

CMD_RESTART_ALL_PROC = 'restart_all_proc'
CMD_START_ALL_PROC = 'start_all_proc'
CMD_STOP_ALL_PROC = 'stop_all_proc'

CMD_TOGGLE_PROC = 'toggle_proc'
CMD_START_PROC = 'start_proc'
CMD_STOP_PROC = 'stop_proc'

##
# Common functions
def init_logging(level=logging.INFO):
    """Initialize logging"""
    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")
    return

def format_secs_to_runtime(ts):
    """Formats a timestamp to days HH:MM:SS"""
    sec = timedelta(seconds=ts)
    dt = datetime(1, 1, 1) + sec
    result = '{} days, {}:{:02d}:{:02d}'.format(sec.days, dt.hour, dt.minute, dt.second)
    return result

# EOF
