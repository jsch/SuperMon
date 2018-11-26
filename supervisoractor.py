#! /usr/bin/env python3
# -*- coding:utf-8 -*-
# -*- python -*-
# pylint: disable=C0301

"""Actor to interact with a supervisor instance"""

import logging
import threading
import time
import xmlrpc.client

import pykka
import common as k


class SupervisorActor(pykka.ThreadingActor):
    """Clase del actor"""

    def __init__(self, config):
        """Inicia el actor"""
        super(SupervisorActor, self).__init__()
        self.server_id = config.get('server_id', -1)
        self.server_name = config.get('server_name')
        self.event_queue = config.get('event_queue', None)
        ip_address = config.get('ip_address')
        port = config.get('port')
        user_name = config.get('user_name')
        password = config.get('password')
        user_pass = ''
        if user_name and password:
            user_pass = '{}@{}:'.format(user_name, password)
        self.connection = 'http://{}{}:{}/RPC2'.format(user_pass, ip_address, port)
        logging.debug('Connection string: %s', self.connection)

        self.server = None
        self.processes = dict()
        self.process_names = list()
        self.timer_thread = None
        self.running = False
        self.monitor_enabled = False
        self.failed = False
        self.error_message = ''
        return

    def init_processes(self):
        """Get all the processes from the server"""
        try:
            processes = self.server.supervisor.getAllProcessInfo()
        except Exception as err:
            logging.error('Exception initializing processes: %s', err)
            self.failed = True
            self.error_message = str(err)
            return
        else:
            self.processes.clear()
            self.process_names = []
            for process in processes:
                process_id = len(self.processes)
                self.processes[process['name']] = process
                self.processes[process['name']]['process_id'] = process_id
                self.process_names.append(process['name'])
                logging.debug('Adding process [%s]', process['name'])
            self.failed = False
            self.error_message = ''
        return

    def publish_event(self, data, type='event'):
        """Publish a change in a process attribute"""
        if self.event_queue:
            event = {
                'type': type,
                'event': data
            }
            self.event_queue.put_nowait(event)
        logging.debug('Publishing event: %s', repr(data))
        return

    def make_change(self, process_name, process_id, key, fr, to):
        """Make a change dict"""
        result = {
            'server_id': self.server_id,
            'server_name': self.server_name,
            'process_name': process_name,
            'process_id': process_id,
            'key': key,
            'from': fr,
            'to': to
        }
        return result

    def make_error(self, error):
        """Make an error dict"""
        result = {
            'server_id': self.server_id,
            'server_name': self.server_name,
            'error': str(error)
        }
        return result

    def check_change(self, a_process, key):
        """Check for changes and publish in case there is one"""
        change = None
        name = a_process['name']
        if a_process.get(key) != self.processes[name].get(key):
            change = self.make_change(
                process_name=name,
                process_id=self.processes[name].get('process_id'),
                key=key,
                fr=self.processes[name].get(key),
                to=a_process.get(key)
            )
            self.processes[name][key] = a_process.get(key)
            self.publish_event(change)
        return change

    def process_changes(self, a_process):
        """Verify changes in a process"""
        changes = []
        # Verify change in state
        change = self.check_change(a_process, 'statename')
        if change:
            changes.append(change)
        # Verify change in PID
        change = self.check_change(a_process, 'pid')
        if change:
            changes.append(change)
        # Update runtime if process is running
        if a_process['statename'] == 'RUNNING':
            runtime = k.format_secs_to_runtime(a_process.get('now') - a_process.get('start'))
        else:
            runtime = ''
        change = self.make_change(
            process_name=a_process.get('name'),
            process_id=self.processes[a_process['name']].get('process_id'),
            key='runtime',
            fr='',
            to=runtime
        )
        self.publish_event(change)
        changes.append(change)
        return changes

    def refresh_a_process_info(self, process_name):
        """Refresh a process info from the server"""
        try:
            a_process = self.server.supervisor.getProcessInfo(process_name)
            changes = self.process_changes(a_process)
        except Exception as err:
            error = self.make_error(err)
            self.publish_event(error, 'error')
            changes = []
        return changes

    def refresh_all_processes_info(self):
        """Refresh all the processes info"""
        changes = []
        if not self.monitor_enabled:
            return changes
        try:
            processes = self.server.supervisor.getAllProcessInfo()
        except Exception as err:
            logging.error('Exception refreshing processes: %s', err)
            error = self.make_error(err)
            self.publish_event(error, type='error')
            self.failed = True
            self.error_message = str(err)
        else:
            for a_process in processes:
                if a_process['name'] in self.processes:
                    changes = changes + self.process_changes(a_process)
                else:
                    # TODO: new process!
                    pass
            self.failed = False
            self.error_message = ''
        return changes

    def get_processes_names(self):
        """Get the processes names"""
        return sorted(self.processes.keys())

    def get_process_info(self, process_name):
        """Get the info for one process"""
        if process_name is None:
            logging.warning('No process name specified')
            return None
        if not process_name in self.processes:
            logging.warning('Invalid rocess name: %s', process_name)
            return None
        runtime = 0
        try:
            statename = self.processes[process_name].get('statename')
            if statename == 'RUNNING':
                runtime = time.time() - self.processes[process_name].get('start', time.time())
        except Exception as err:
            logging.error('Unable to determine runtime: %s', err)
        result = {
            'pid': self.processes[process_name].get('pid'),
            'name': self.processes[process_name].get('name'),
            'statename': self.processes[process_name].get('statename'),
            'runtime': '' if runtime == 0 else k.format_secs_to_runtime(runtime),
            'process_id': self.processes[process_name].get('process_id')
        }
        return result

    def get_all_processes_info(self):
        """Get the info of all processes"""
        result = dict()
        for process_name in self.get_processes_names():
            result[process_name] = self.get_process_info(process_name)
        return result

    def get_info(self):
        """Get all the actor's info"""
        result = {
            'server_id': self.server_id,
            'server_name': self.server_name,
            'processes': self.get_all_processes_info(),
            'failed': self.failed,
            'error_message': self.error_message
        }
        return result

    def start_stop_process(self, message):
        """Start or stop a process depending on the command received"""
        command = message.get('command', '*')
        process_id = int(message.get('process_id'))
        process_name = self.process_names[process_id]
        logging.debug('Actor::%s:%s:%d:%s', self.server_name, command, process_id, process_name)
        try:
            if command == k.CMD_START_PROC:
                rpc_result = self.server.supervisor.startProcess(process_name)
            else:
                rpc_result = self.server.supervisor.stopProcess(process_name)
        except Exception as err:
            self.refresh_a_process_info(process_name)
            err_message = str(err).replace('<', '').replace('>', '')
            logging.error('Error starting/stopping a process: %s', err_message)
            result = {
                'status': k.ERROR,
                'message': err_message
            }
        else:
            self.refresh_a_process_info(process_name)
            logging.debug('Actor::Start/Stop result: %s', repr(rpc_result))
            if not rpc_result:
                result = {
                    'status': k.ERROR,
                    'message': 'Error process {}'.format(process_name)
                }
            else:
                result = {
                    'status': k.OK,
                    'message': 'Process {} changed to state {}'.format(
                        process_name, self.processes[process_name]['statename']
                    )
                }
        return result

    def start_all_processes(self):
        """Start all the processes"""
        try:
            self.server.supervisor.startAllProcesses()
            result = {
                'status': k.OK,
                'message': 'All processes started'
            }
        except Exception as err:
            error = self.make_error(err)
            self.publish_event(error, 'error')
        self.refresh_all_processes_info()
        return result

    def stop_all_processes(self):
        """Start all the processes"""
        try:
            self.server.supervisor.stopAllProcesses()
            result = {
                'status': k.OK,
                'message': 'All processes started'
            }
        except Exception as err:
            error = self.make_error(err)
            self.publish_event(error, 'error')
        self.refresh_all_processes_info()
        return result

    def restart_all_processes(self):
        """Restart all the processes"""
        try:
            self.server.supervisor.stopAllProcesses()
            self.server.supervisor.startAllProcesses()
            result = {
                'status': k.OK,
                'message': 'All processes started'
            }
        except Exception as err:
            error = self.make_error(err)
            self.publish_event(error, 'error')
        self.refresh_all_processes_info()
        return result

    def start_monitor(self):
        """Start the monitoring"""
        self.monitor_enabled = True
        message = 'Actor {} started monitoring'.format(self.server_name)
        logging.debug(message)
        self.refresh_all_processes_info()
        result = {
            'status': k.OK,
            'message': message
        }
        return result

    def stop_monitor(self):
        """Stop the monitoring by disabling the flag"""
        self.monitor_enabled = False
        message = 'Actor {} stopped monitoring'.format(self.server_name)
        logging.debug(message)
        result = {
            'status': k.OK,
            'message': message
        }
        return result

    def on_start(self):
        """Create the connection to the server"""
        self.running = True
        self.server = xmlrpc.client.ServerProxy(self.connection)
        self.init_processes()
        self.timer_thread = threading.Thread(target=self.timer, daemon=True)
        self.timer_thread.start()
        return

    def on_stop(self):
        """Stopping the actor"""
        logging.debug('Stopping actor %s', self.server_name)
        self.running = False
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.join()
        return

    def on_failure(self, exception_type, exception_value, traceback):
        """Exception catcher
        optional cleanup code in same context as on_receive()"""
        logging.error('>>>ActorNotificaciones>>>on_failure>>>')
        logging.error('>>> exception_type: %s', exception_type)
        logging.error('>>>exception_value: %s', exception_value)
        logging.error('>>>      traceback: %s', traceback)
        logging.error('<<ActorNotificaciones<<<on_failure<<<')
        return

    def on_receive(self, message):
        """message handling code for a plain actor"""
        command = message.get('command')
        result = None
        if command is None:
            logging.error('No command specified')
        elif command == k.CMD_STOP_ACTOR:
            self.stop()
        elif command == k.CMD_START_MONITOR:
            self.start_monitor()
        elif command == k.CMD_STOP_MONITOR:
            self.stop_monitor()
        elif command == k.CMD_GET_PROCESSES_NAMES:
            result = self.get_processes_names()
        elif command == k.CMD_GET_PROCESS_INFO:
            result = self.get_process_info(message.get('process_name'))
        elif command == k.CMD_GET_ALL_PROCESSES_INFO:
            result = self.get_all_processes_info()
        elif command == k.CMD_REFRESH_ALL_PROCESSES_INFO:
            result = self.refresh_all_processes_info()
        elif command == k.CMD_GET_INFO:
            result = self.get_info()
        elif command == k.CMD_TIMER:
            result = self.refresh_all_processes_info()
        elif command in [k.CMD_STOP_PROC, k.CMD_START_PROC]:
            result = self.start_stop_process(message)
        elif command == k.CMD_RESTART_ALL_PROC:
            result = self.restart_all_processes()
        elif command == k.CMD_START_ALL_PROC:
            result = self.start_all_processes()
        elif command == k.CMD_STOP_ALL_PROC:
            result = self.stop_all_processes()
        else:
            err_message = 'Invalid command received: {}'.format(command)
            result = {
                'status': k.ERROR,
                'message': err_message
            }
            logging.error('Actor [%s]: %s', self.server_name, err_message)
        return result

    def timer(self):
        """Timer thread
        This thread is executed every second and after k.PARAMS['refresh_period']
        seconds it triggers a timer to the actor to refresh the processes states
        in the supervisor
        """
        logging.debug('Actor timer started for server %s', self.server_name)
        ticks = 0
        while self.running:
            time.sleep(1.0)
            ticks += 1
            if ticks > k.PARAMS['refresh_period'] and self.running:
                self.actor_ref.tell({'command': k.CMD_TIMER})
                ticks = 0
        #
        logging.debug('Actor timer ended for server %s', self.server_name)
        return

    # # # def a_method(self, ...):
    # # #     ... # My regular method to be used through an ActorProxy



# EOF
