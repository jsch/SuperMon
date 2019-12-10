#! /usr/bin/env python3
# -*- coding:utf-8 -*-
# -*- python -*-
#pylint: disable=C0301,W0703

"""Command line argument parser"""

import argparse
import logging
import sys

import common as k


def parse_cmd_line():
    """Parse the command line :)"""
    parser = argparse.ArgumentParser(description='Supervisor web controller')
    parser.add_argument(
        '-p', action='store',
        dest='http_port',
        default=k.HTTP_PORT,
        help='Application HTTP port (default: {})'.format(k.HTTP_PORT)
    )
    parser.add_argument(
        '-r', action='store',
        dest='refresh_period',
        default=k.REFRESH_PERIOD,
        help='Status refresh period in secs (default: {})'.format(k.REFRESH_PERIOD)
    )
    parser.add_argument(
        '-A', action='store_true',
        dest='print_args_and_exit',
        default=False,
        help='Print arguments and exit'
    )
    parser.add_argument(
        '-L', action='store_true',
        dest='use_login',
        default=k.USE_LOGIN,
        help='Enable login mode'
    )

    grp_log = parser.add_mutually_exclusive_group()
    grp_log.add_argument(
        '-D', action='store_true',
        dest='debug_level',
        default=False,
        help='Debug logging level')
    grp_log.add_argument(
        '-I', action='store_true',
        dest='info_level',
        default=False,
        help='Info logging level')
    grp_log.add_argument(
        '-W', action='store_true',
        dest='warning_level',
        default=False,
        help='Warning logging level')
    grp_log.add_argument(
        '-E', action='store_true',
        dest='error_level',
        default=False,
        help='Error logging level')

    # Parse the arguments and update the app parameters
    args = parser.parse_args()
    k.PARAMS['http_port'] = args.http_port
    try:
        k.PARAMS['refresh_period'] = int(args.refresh_period)
    except:
        k.PARAMS['refresh_period'] = k.REFRESH_PERIOD
        logging.error('Invalid refresh period [%s], using default value', args.refresh_period)
    k.PARAMS['use_login'] = args.use_login

    # Identify the logging level
    if args.debug_level:
        level = logging.DEBUG
    elif args.info_level:
        level = logging.INFO
    elif args.warning_level:
        level = logging.WARNING
    elif args.error_level:
        level = logging.ERROR
    else:
        level = logging.INFO
    k.init_logging(level)

    print('=' * 30)
    print('      http_port: {}'.format(k.PARAMS['http_port']))
    print(' refresh_period: {}'.format(k.PARAMS['refresh_period']))
    print('      Use login: {}'.format(k.PARAMS['use_login']))
    print('=' * 30)

    if args.print_args_and_exit:
        sys.exit()
    return
