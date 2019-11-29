#! /usr/bin/env python3
# -*- coding:utf-8 -*-
# -*- python -*-

"""Supervisor config file"""

SUPERVISORS = [
    {
        'server_name': 'localhost',
        'ip_address': '127.0.0.1',
        'port': 9001
    },
    # {
    #     'server_name': 'server-5.51',
    #     'ip_address': '10.190.5.51',
    #     'port': 9001
    # },
    {
        'server_name': 'Raspberry Pi - 1',
        'ip_address': '10.0.0.100',
        'port': 9001,
        'username': 'user',
        'password': '123'
    },
]
