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
import gevent

import bottle

import arguments
import common as k

#######################################
# Global
#######################################
APPLICATION = None
B64STR = lambda ui: base64.b64encode(bytes(ui, 'utf-8')).decode()


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
        data = APPLICATION.get_index_data()
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

@bottle.route('/posttest')
def post_test():
    """Post test"""
    return bottle.template('posttest')

#######################################
# API service route
#######################################
@bottle.route('/api', method=['GET', 'POST'])
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

    logging.debug('api.request:[%s]', repr(request))
    if APPLICATION:
        response = APPLICATION.api_service(request)
    else:
        response = {'status': k.OK}
    logging.debug('api.response:[%s]', repr(response))
    bottle.response.content_type = 'application/json'
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

        rfile = bottle.request.environ['wsgi.input'].rfile

        poller = zmq.Poller()
        poller.register(socket_sub, zmq.POLLIN)
        poller.register(rfile, zmq.POLLIN)

        # Set client-side auto-reconnect timeout, ms.
        yield 'retry: 1000\n\n'
        time_reference = time.time()
        while session_is_active:

            events = dict(poller.poll())

            if rfile.fileno() in events:
                # client disconnect!
                logging.debug('Session disconnected: %s', session_id)
                break
            if socket_sub in events:
                try:
                    message = socket_sub.recv(zmq.DONTWAIT)
                except zmq.ZMQError:
                    time.sleep(0.01)
                else:
                    ui_message = message.decode().replace('\n', '')
                    logging.debug('SSE message to [%s]:[%s]', session_id, ui_message)
                    try:
                        yield 'data: {0}\n\n'.format(ui_message)
                        # # # logging.debug('*** SSE after yield ***')
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

def worker(body, rfile, session_id):
    """ An SSE worker....
    @see: https://stackoverflow.com/questions/20110830/responding-to-client-disconnects-using-bottle-and-gevent-wsgi
    """
    if APPLICATION:
        APPLICATION.update_session_id(session_id)
    socket_sub = zmq.Context().instance().socket(zmq.SUB)
    socket_sub.connect(k.INTERNAL_ZMQ_EVENT_CNX)
    # Subscribe to the messages to UI
    socket_sub.setsockopt(zmq.SUBSCRIBE, ''.encode())
    poll = zmq.Poller()
    poll.register(socket_sub)
    poll.register(rfile, zmq.POLLIN)

    while True:
        events = dict(poll.poll())

        if rfile.fileno() in events:
            # client disconnect!
            break

        if socket_sub in events:
            msg = socket_sub.recv().decode().replace('\n', '')
            body.put(msg)

    body.put(StopIteration)

@bottle.route('/stream-wtf/<session_id>')
def poll(session_id):
    rfile = bottle.request.environ['wsgi.input'].rfile
    body = gevent.queue.Queue()
    a_worker = gevent.spawn(worker, body, rfile, session_id)
    return body


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
