#! /usr/bin/env python3
# -*- coding:utf-8 -*-
# -*- python -*-
#pylint: disable=C0301,W0703,C0411,C0413

"""Supervisor control"""

from gevent import monkey
monkey.patch_all()

import base64
import logging
import threading
import time

import zmq

import bottle

import arguments
import common as k

#######################################
# Global
#######################################
APPLICATION = None
B64STR = lambda ui: base64.b64encode(bytes(ui, 'utf-8')).decode()
GIT_TAG = 'master'


#######################################
# bottle routes
#######################################
# Index/default route
@bottle.route('/')
@bottle.route('/index.html')
def index():
    """Index page route"""
    if APPLICATION:
        template = 'index'
        data = {
            'git_tag': GIT_TAG,
            'background': 'pattern.gif'
        }
    else:
        template = 'index-poc'
        data = {
            'servers': [
                {'server_name': 'server-01'},
                {'server_name': 'server-02'},
                {'server_name': 'server-03'},
                {'server_name': 'server-04'},
                {'server_name': 'server-05'},
            ]
        }
    return bottle.template(template, data=data)

#######################################
# Static routes
@bottle.route('/clrtemplatecache')
def clrtemplatecache():
    """Clear the templates cache in bottle.py"""
    bottle.TEMPLATES.clear()
    return {'status': k.OK}

@bottle.route('/favicon.ico')
def favicon_ico():
    """The default icon to keep browsers happy"""
    return bottle.static_file('favicon.ico', root='static/images')

@bottle.route('/static/<filepath:path>')
def server_static(filepath):
    """Static files"""
    return bottle.static_file(filepath, root='static')


#######################################
# API service routes
#######################################
def api_service(request):
    """API service request"""
    logging.debug('api.request:[%s]', repr(request))
    if APPLICATION:
        response = APPLICATION.api_service(request)
    else:
        response = {'status': k.OK}
    logging.debug('api.response:[%s]', repr(response))
    if 'template' in response:
        if 'data' in response:
            html = bottle.template(response['template'], data=response['data'])
        else:
            html = bottle.template(response['template'])
        response['html'] = B64STR(html)
    bottle.response.content_type = 'application/json'
    return response

@bottle.route('/api', method='POST')
def api_post():
    """Application API access"""
    request = {}
    if bottle.request.json:
        logging.debug('api: json web request')
        request = bottle.request.json
    else:
        for key in bottle.request.params.keys():
            val = bottle.request.params.get(key)
            logging.debug('[%s]:[%s]', key, val)
            request[key] = val
    response = api_service(request)
    return response

@bottle.route('/api/<command>', method='GET')
def api_command(command):
    """Simple command requested"""
    request = {
        'command': command
    }
    response = api_service(request)
    return response

@bottle.route('/api/<command>/<server_id>', method='GET')
def api_server(command, server_id):
    """Command for a server"""
    request = {
        'command': command,
        'server_id': server_id
    }
    response = api_service(request)
    return response

@bottle.route('/api/<command>/<server_id>/<process_id>', method='GET')
def api_process(command, server_id, process_id):
    """Command for a process"""
    request = {
        'command': command,
        'server_id': server_id,
        'process_id': process_id
    }
    response = api_service(request)
    return response

########################################
# Server Side Events
@bottle.route('/stream/<session_id>')
def stream(session_id):
    """SSE stream"""
    logging.debug('Initiating SSE stream, %s', session_id)
    if APPLICATION:
        APPLICATION.update_session_id(session_id)
    session_is_active = True
    try:
        socket_sub = zmq.Context().instance().socket(zmq.SUB)
        socket_sub.connect(k.INTERNAL_ZMQ_EVENT_CNX)
        # Subscribe to the messages to UI
        socket_sub.setsockopt(zmq.SUBSCRIBE, ''.encode())

        # 'Using server-sent events'
        # https://developer.mozilla.org/en-US/docs/Server-sent_events/Using_server-sent_events
        # 'Stream updates with server-sent events'
        # http://www.html5rocks.com/en/tutorials/eventsource/basics/
        bottle.response.content_type = 'text/event-stream'
        bottle.response.cache_control = 'no-cache'

        # Set client-side auto-reconnect timeout, ms.
        yield 'retry: 100\n\n'
        while session_is_active:
            try:
                message = socket_sub.recv(zmq.DONTWAIT)
            except zmq.ZMQError:
                time.sleep(0.01)
            else:
                ui_message = message.decode().replace('\n', '')
                logging.debug('SSE message to [%s]:[%s]', session_id, ui_message)
                yield 'data: {0}\n\n'.format(ui_message)
            # Is this session still active?
            if APPLICATION:
                if not session_id in APPLICATION.active_sessions:
                    logging.debug('Session no longer active: %s', session_id)
                    session_is_active = False

    except Exception as err:
        logging.error('Exception processing stream: %s', err)
    finally:
        socket_sub.setsockopt(zmq.LINGER, 0)
        socket_sub.close()
    logging.debug('Disconnecting SSE from session %s', session_id)
    return


# Clase del servidor web
class WebServer(object):
    """Servidor Web"""

    def __init__(self):
        """Iniciacion"""
        self.bottle_thread = None
        return

    def run(self):
        """Magic"""
        logging.debug('Iniciando el servidor web')
        if 'http_port' in k.PARAMS:
            http_port = k.PARAMS['http_port']
        else:
            http_port = k.HTTP_PORT
        kwargs = dict(host='0.0.0.0', port=http_port, server=bottle.GeventServer)

        self.bottle_thread = threading.Thread(target=bottle.run, kwargs=kwargs)
        self.bottle_thread.daemon = True
        self.bottle_thread.start()
        logging.debug('Web server started')
        return

    def stop(self):
        """Stops the execution"""
        self.bottle_thread.join()
        return


def main():
    """Stand alone webserver start (testing)"""
    k.init_logging(level=logging.DEBUG)
    arguments.parse_cmd_line()

    web_server = WebServer()
    web_server.run()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    exit()

if __name__ == '__main__':
    main()

# EOF
