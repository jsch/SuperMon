#! /usr/bin/env python3
# -*- coding:utf-8 -*-
# -*- python -*-
# pylint: disable=C0301
"""Supervidor actor tests"""

import time
import logging
from pprint import pformat

import config
import common as k

from supervisoractor import SupervisorActor

def main():
    """test only"""
    k.init_logging(level=logging.DEBUG)
    # Refresh the status every 5 seconds for testing
    k.PARAMS['refresh_period'] = 5
    supervisor_actor = SupervisorActor.start(config.SUPERVISORS[0])
    processes_names = supervisor_actor.ask(
        {'command': k.ACTOR_CMD_GET_PROCESSES_NAMES}
    )
    logging.debug('Processes names:\n%s', pformat(processes_names))
    process_info = supervisor_actor.ask(
        {
            'command': k.ACTOR_CMD_GET_PROCESS_INFO,
            'process_name': processes_names[0]
        }
    )
    logging.debug('---Process info for %s ---', processes_names[0])
    logging.debug('\n%s', pformat(process_info))

    logging.debug('---All processes info---')
    logging.debug('\n%s', pformat(supervisor_actor.ask(
        {'command': k.ACTOR_CMD_GET_ALL_PROCESSES_INFO}
    )))
    time.sleep(30)
    supervisor_actor.stop()

if __name__ == '__main__':
    main()

# EOF
