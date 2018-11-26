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

#######################################
from gevent.pywsgi import WSGIServer
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler
#######################################

import zmq

# import bottle
from bottle import (request,response, Bottle, abort,
                    template, TEMPLATES, static_file,
                    GeventServer, run)

import arguments
import common as k

#######################################
# Global
#######################################
APPLICATION = None
B64STR = lambda ui: base64.b64encode(bytes(ui, 'utf-8')).decode()
app = Bottle()


#######################################
# bottle routes
#######################################
# Index/default route
@app.route('/')
@app.route('/index.html')
def index():
    """Index page route"""
    if APPLICATION:
        tmpl = 'index'
        data = APPLICATION.get_index_data()
    else:
        tmpl = 'index-poc'
        data = {
            'servers': [
                {'server_name': 'server-01'},
                {'server_name': 'server-02'},
                {'server_name': 'server-03'},
                {'server_name': 'server-04'},
                {'server_name': 'server-05'},
            ]
        }
    return template(tmpl, data=data)

#######################################
# Static routes
@app.route('/clrtemplatecache')
def clrtemplatecache():
    """Clear the templates cache in bottle.py"""
    TEMPLATES.clear()
    return {'status': k.OK}

@app.route('/favicon.ico')
def favicon_ico():
    """The default icon to keep browsers happy"""
    return static_file('favicon.ico', root='static/images')

@app.route('/static/<filepath:path>')
def server_static(filepath):
    """Static files"""
    return static_file(filepath, root='static')

@app.route('/posttest')
def post_test():
    """Post test"""
    return template('posttest')

#######################################
# API service route
#######################################
@app.route('/api', method=['GET', 'POST'])
def api_post():
    """Application API access"""
    req = {}
    if request.json:
        logging.debug('api: json web request')
        req = request.json
    else:
        for key in request.params.keys():
            val = request.params.get(key)
            logging.debug('[%s]:[%s]', key, val)
            req[key] = val

    logging.debug('api.request:[%s]', repr(req))
    if APPLICATION:
        resp = APPLICATION.api_service(req)
    else:
        resp = {'status': k.OK}
    logging.debug('api.response:[%s]', repr(resp))
    response.content_type = 'application/json'
    return resp

########################################
# Server Side Events
@app.route('/stream/<session_id>')
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
        response.content_type = 'text/event-stream'
        response.cache_control = 'no-cache'

        # Set client-side auto-reconnect timeout, ms.
        yield 'retry: 100\n\n'
        time_reference = time.time()
        while session_is_active:
            try:
                message = socket_sub.recv(zmq.DONTWAIT)
            except zmq.ZMQError:
                time.sleep(0.01)
            else:
                ui_message = message.decode().replace('\n', '')
                logging.debug('SSE message to [%s]:[%s]', session_id, ui_message)
                try:
                    yield 'data: {0}\n\n'.format(ui_message)
                    time_reference = time.time()
                except Exception as err:
                    logging.debug('SSE exception to %s: %s', session_id, err)
            # # # # Is the client still connected?
            # # # time_now = time.time()
            # # # if time_now - time_reference > k.HEARTBEAT_PERIOD * 1.1:
            # # #     logging.debug('SSE TIMEOUT')
            # # # # Is this session still active?
            # # # if APPLICATION:
            # # #     if not session_id in APPLICATION.active_sessions:
            # # #         logging.debug('Session no longer active: %s', session_id)
            # # #         session_is_active = False
    except Exception as err:
        logging.error('Exception processing stream: %s', err)
    finally:
        socket_sub.setsockopt(zmq.LINGER, 0)
        socket_sub.close()
    logging.debug('Disconnecting SSE from session %s', session_id)
    return

########################################
# Web sockets
@app.route('/websocket/<session_id>')
def handle_websocket(session_id):
    """Web socket entry point"""
    wsock = request.environ.get('wsgi.websocket')
    if not wsock:
        abort(400, 'Expected WebSocket request.')

    socket_sub = zmq.Context().instance().socket(zmq.SUB)
    socket_sub.connect(k.INTERNAL_ZMQ_EVENT_CNX)
    # Subscribe to the messages to UI
    socket_sub.setsockopt(zmq.SUBSCRIBE, ''.encode())

    if APPLICATION:
        APPLICATION.update_session_id(session_id)

    # Client welcome message
    message = wsock.receive()
    wsock.send('Your welcome message was: %r' % message)

    while True:
        try:
            message = socket_sub.recv(zmq.DONTWAIT)
            ui_message = message.decode().replace('\n', '')
            logging.debug('WS message to [%s]:[%s]', session_id, ui_message)
            # message = wsock.receive()
            wsock.send(ui_message)
        except zmq.ZMQError:
            time.sleep(0.01)
        except WebSocketError as err:
            logging.debug('WebSocket error: %s', err)
            break

    logging.debug('Terminating websocket session: %s', session_id)
    socket_sub.setsockopt(zmq.LINGER, 0)
    socket_sub.close()
    return

# Clase del servidor web
class WebServer(object):
    """Servidor Web"""

    def __init__(self):
        """Iniciacion"""
        self.bottle_thread = None
        self.server = None
        return

    def run(self):
        """Magic"""
        logging.debug('Starting the web server')
        if 'http_port' in k.PARAMS:
            http_port = k.PARAMS['http_port']
        else:
            http_port = k.HTTP_PORT

        # # # kwargs = dict(host='0.0.0.0', port=http_port, server=GeventServer)
        # # # self.bottle_thread = threading.Thread(target=run, kwargs=kwargs)
        # # # self.bottle_thread.daemon = True
        # # # self.bottle_thread.start()

        self.server = WSGIServer(("0.0.0.0", http_port), app, handler_class=WebSocketHandler)
        # server.serve_forever()
        self.bottle_thread = threading.Thread(target=self.server.serve_forever())
        self.bottle_thread.daemon = True
        logging.debug('Starting web server')
        try:
            self.bottle_thread.start()
        except Exception as err:
            logging.error('Web server error: %s', err)

        # # # logging.debug('Web server started')
        return

    def stop(self):
        """Stops the execution"""
        logging.debug('Requesting web server to STOP')
        # # self.server.stop()
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
