#! /usr/bin/env python3
# -*- coding:utf-8 -*-
# -*- python -*-
#pylint: disable=C0301,W0703,C0411,C0413,R0201

"""Main applicacion of the supervisor web control"""

from datetime import datetime
import json
import logging
import queue
import threading
import time

import zmq

import arguments
import common as k
import config

import webserver
from supervisoractor import SupervisorActor

FMT_TSTAMP = lambda ts: datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

class Session:
    """Session class"""

    def __init__(self, session_id):
        """Initialize session object"""
        self.session_id = session_id
        now = time.time()
        self.startup = now
        self.last_heartbeat = now

    def register_heartbeat(self):
        """Register a heartbeat event"""
        self.last_heartbeat = time.time()

    def is_active(self, time_reference):
        """Verifies if session is active"""
        elapsed_time = time_reference - self.last_heartbeat
        periods = elapsed_time // k.SESSION_CHECK_PERIOD
        # have we missed maximum number of heartbeat?
        return k.MAX_MISSED_CHECKS > periods

    def deactivate(self):
        """Deactivate a session by setting the heartbeat to 0"""
        self.last_heartbeat = 0


class SuperMon:
    """Aplication main class"""

    def __init__(self):
        """Initialization"""
        self.running = False
        self.web_server = webserver.WebServer()
        webserver.APPLICATION = self
        self.startup = time.time()
        self.event_queue = queue.Queue()
        self.main_loop_thread = threading.Thread(target=self.main_loop, daemon=True)
        self.num_active_sessions = 0
        self.active_sessions = {}
        self.sessions_lock = threading.RLock()
        self.actors = []
        server_id = 0
        for config_item in config.SUPERVISORS:
            if self.is_valid_config_item(config_item):
                config_item['server_id'] = server_id
                config_item['event_queue'] = self.event_queue
                logging.debug('Starting actor for server: %s', config_item['server_name'])
                actor = SupervisorActor.start(config_item)
                self.actors.append(actor)
                server_id += 1
            else:
                logging.error('Invalid configuratio at: %s', repr(config_item))
        return

    def diagnostics(self):
        """Return the application diagnostics"""
        sessions = []
        for session in self.active_sessions:
            sessions.append({
                'session_id': session,
                'startup': FMT_TSTAMP(self.active_sessions[session].startup),
                'updated': FMT_TSTAMP(self.active_sessions[session].last_heartbeat)
            })
        result = {
            'startup': FMT_TSTAMP(self.startup),
            'runtime': k.format_secs_to_runtime(time.time() - self.startup),
            'datetime': FMT_TSTAMP(time.time()),
            'num_active_sessions': len(self.active_sessions),
            'sessions': sessions
        }
        return result

    def is_valid_config_item(self, config_item):
        """Validates a config item
        - Must be a dict
        - Must have keys to identify the supervisor
        - If contains a username it must contain a password
        - If contains a password it must contain a username
        """
        result = isinstance(config_item, dict)
        if not result:
            return result
        keys = ['server_name', 'ip_address', 'port']
        for key in keys:
            result = result and key in config_item
        contains_user = 'username' in config_item
        contains_pswd = 'password' in config_item
        result = result and not contains_user ^ contains_pswd
        return result

    def get_index_data(self):
        """Return the information for the index page"""
        result = []
        for actor in self.actors:
            data = actor.ask({'command': k.CMD_GET_INFO})
            result.append(data)
        return {'servers': result}

    def start_monitoring(self):
        """Ask the actors to start monitoring"""
        logging.debug('Starting monitoring')
        message = {'command': k.CMD_START_MONITOR}
        for actor in self.actors:
            actor.ask(message)
        return {'status': k.OK}

    def stop_monitoring(self):
        """Ask the actors to stop monitoring"""
        logging.debug('Stopping monitoring')
        message = {'command': k.CMD_STOP_MONITOR}
        for actor in self.actors:
            actor.ask(message)
        return {'status': k.OK}

    def authenticate_user(self, request):
        """Authenticate the user"""
        for key in request.keys():
            val = request.get(key)
            logging.debug('[%s]:[%s]', key, val)
            request[key] = val
        # TODO:
        # if user is not authenticated return an error:
        #     response = {'result': k.ERROR, 'message': 'Still workin on this...'}
        # else: build the application page
        return self.get_app_page()

    def get_app_page(self):
        """Build the application page response"""
        response = {
            'result': k.OK,
            'template': 'application',
            'data': self.get_index_data(),
        }
        return response

    def session_logout(self, request):
        """Terminate a session"""
        result = {'status': k.OK}
        session_id = request.get('sessionid')
        if not session_id:
            return result
        session = self.active_sessions.get(session_id)
        if not session:
            return result
        with self.sessions_lock:
            # setting the session timeout to zero forces it to be invalid
            # when verifying it
            session.deactivate()
        self.verify_active_sessions()
        return {'status': k.OK}

    def update_session_id(self, session_id):
        """Update an active session"""
        with self.sessions_lock:
            if not session_id in self.active_sessions:
                self.active_sessions[session_id] = Session(session_id)
            else:
                self.active_sessions[session_id].register_heartbeat()
            if self.num_active_sessions == 0:
                self.num_active_sessions = len(self.active_sessions)
                self.start_monitoring()

    def verify_active_sessions(self):
        """Verify active sessions and remove those inactive"""
        time_reference = time.time()
        inactive = []
        with self.sessions_lock:
            for session_id in self.active_sessions:
                # elapsed_time = time_reference - self.active_sessions[session_id]
                # periods = elapsed_time // k.SESSION_CHECK_PERIOD
                # if periods > k.MAX_MISSED_CHECKS:
                if not self.active_sessions[session_id].is_active(time_reference):
                    inactive.append(session_id)
            for session_id in inactive:
                self.active_sessions.pop(session_id, None)
                logging.warning('Inactive session removed: %s', session_id)
            if self.num_active_sessions != len(self.active_sessions):
                if not self.active_sessions:
                    self.stop_monitoring()
                self.num_active_sessions = len(self.active_sessions)


    def main_loop(self):
        """Main loop"""
        logging.debug('Starting the main loop')
        socket_pub = zmq.Context().instance().socket(zmq.PUB)
        socket_pub.bind(k.INTERNAL_ZMQ_EVENT_CNX)
        heartbeat_counter = 0
        time_reference = time.time()
        while self.running:
            # Verify messages from actors
            message = None
            try:
                message = self.event_queue.get(block=True, timeout=1.0)
            except queue.Empty:
                message = None
            else:
                socket_pub.send(json.dumps(message).encode())

            # time for a heartbeat?
            if time.time() - time_reference > k.HEARTBEAT_PERIOD:
                message = {
                    'type': 'heartbeat',
                    'message': '[{}] - {}'.format(heartbeat_counter, k.HEARTBEAT_MESSAGE)
                }
                heartbeat_counter += 1
                heartbeat_counter = heartbeat_counter & 0xFFFFFF
                time_reference = time.time()
            # if message:
                socket_pub.send(json.dumps(message).encode())

                # Verify active sessions
                self.verify_active_sessions()

        socket_pub.setsockopt(zmq.LINGER, 0)
        socket_pub.close()
        logging.debug('Main loop terminated')

    def ui_error(self, message):
        """Create an error dict to send to the UI"""
        result = {
            'status': k.ERROR,
            'message': str(message)
        }
        return result

    def keep_alive(self, request):
        """Update/Create an active session"""
        session_id = request.get('session_id')
        if not session_id:
            logging.error('No session specified')
            return self.ui_error('No session specified')
        # session = self.active_sessions.get(session_id)
        # if not session:
        #     logging.error('No active session %s', session_id)
        #     return self.ui_error('Invalid session received')
        # with self.sessions_lock:
        #     session.register_heartbeat()
        self.update_session_id(session_id)
        return {'status': k.OK}

    def process_command(self, command, request):
        """Toggle a process state (RUNNING <=> STOPPED)"""
        try:
            server_id = int(request.get('server_id', None))
        except Exception as err:
            return self.ui_error(err)
        try:
            process_id = int(request.get('process_id', None))
        except Exception as err:
            return self.ui_error(err)
        # Determine correct command in case of toggle command
        if command == k.CMD_TOGGLE_PROC:
            state = request.get('state')
            command = k.CMD_STOP_PROC if state == 'RUNNING' else k.CMD_START_PROC
        message = {
            'command': command,
            'process_id': process_id
        }
        result = self.actors[server_id].ask(message)
        return result

    def server_command(self, command, request):
        """Execute a server command (start, stop, restart)"""
        try:
            server_id = int(request.get('server_id', None))
        except Exception as err:
            return self.ui_error(err)
        message = {
            'command': command
        }
        result = self.actors[server_id].ask(message)
        return result

    def global_command(self, command, request):
        """Execute a command on all servers and processes"""
        logging.debug('Command to all servers: %s', repr(request))
        message = {
            'command': command
        }
        for actor in self.actors:
            actor.tell(message)
        result = {
            'status': k.OK,
            'message': 'Command sent to all servers'
        }
        return result

    def ask_actor(self, request):
        """Ask a question to a server actor"""
        if not 'server_id' in request:
            return self.ui_error('No server_id specified')
        try:
            server_id = int(request.get('server_id'))
        except Exception as err:
            logging.debug('Exception getting server_id: %s', str(err))
            return self.ui_error('Invalid server_id [{}]'.format(request['server_id']))
        if not 0 <= server_id < len(self.actors):
            return self.ui_error(
                'Server ID [{}] is out of range [0..{}]'.format(server_id, len(self.actors))
            )
        cmd = request.get('cmd')
        if not cmd:
            return self.ui_error('No command specified')
        request['command'] = cmd
        return self.actors[server_id].ask(request)

    # # # def not_ready_yet(self, request):
    # # #     """Temporary response"""
    # # #     result = {
    # # #         'status': k.ERROR,
    # # #         'message': 'Not ready yet: [{}]'.format(repr(request))
    # # #     }
    # # #     return result

    def api_service(self, request):
        """Process an API request"""
        logging.debug('API Service, request: %s', repr(request))
        command = request.get('command')
        if not command:
            result = self.ui_error('No command specified in API request')
        elif command == k.CMD_AUTHENTICATE:
            result = self.authenticate_user(request)
        elif command == k.CMD_LOGOUT:
            result = self.session_logout(request)
        elif command == k.CMD_GET_APP_PAGE:
            result = self.get_app_page()
        elif command == k.CMD_KEEP_ALIVE:
            result = self.keep_alive(request)
        elif command == k.CMD_START_MONITOR:
            result = self.start_monitoring()
        elif command == k.CMD_STOP_MONITOR:
            result = self.stop_monitoring()
        elif command == k.CMD_DIAGNOSTICS:
            result = self.diagnostics()
        elif command == k.CMD_GET_INDEX:
            result = self.get_index_data()
        elif command == k.CMD_ASK_SERVER:
            result = self.ask_actor(request)
        elif command in [k.CMD_RESTART_GLOB, k.CMD_START_GLOB, k.CMD_STOP_GLOB]:
            result = self.global_command(command, request)
        elif command in [k.CMD_RESTART_ALL_PROC, k.CMD_START_ALL_PROC, k.CMD_STOP_ALL_PROC]:
            result = self.server_command(command, request)
        elif command in [k.CMD_START_PROC, k.CMD_STOP_PROC, k.CMD_TOGGLE_PROC]:
            result = self.process_command(command, request)
        else:
            result = self.ui_error('Invalid command received: {}'.format(command))
        logging.debug('API Service, response: %s', repr(result))
        return result

    def run(self):
        """Start the system"""
        self.running = True
        self.web_server.run()
        self.main_loop_thread.start()

    def stop(self):
        """Stop the system"""
        self.running = False
        self.main_loop_thread.join()
        logging.debug('Stopping actors')
        message = {'command': k.CMD_STOP_ACTOR}
        for actor in self.actors:
            actor.tell(message)
        # self.web_server.stop()


def main():
    """Startup"""
    arguments.parse_cmd_line()
    super_mon = SuperMon()
    super_mon.run()
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break
    super_mon.stop()

if __name__ == '__main__':
    main()

# EOF
