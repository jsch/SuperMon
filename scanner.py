#! /usr/bin/env python3

"""Instance Scanner"""

# pylint: disable=C0301,W0703
# ,C0111,C0103,W0703,R0201

# import json
import logging
import queue
import random
import socket
import sys
import time
import xmlrpc.client

from gevent import monkey
monkey.patch_all()

import pykka

################################################################
# Constants, configuration, etc
################################################################
SUPERV_PORT = 9001                  # supervisord RPC port

UDP_BUFFER_SIZE = 512
UDP_TIMEOUT = 5

ERROR = 'error'
OK = 'ok'

WORKER_ACTOR_COUNT = 1

CMD_IDENT_SUPERV = 'ident_superv'
CMD_DO_SCAN = 'do_scan'
CMD_SCAN_DONE = 'scan_done'
CMD_TERMINATE = 'terminate'

PROD_PARAMS = {
    'subnets': ['192.168.8.{}'],
    'ip_addrs': list(range(1, 255)),
    'num_actors': 128,
    'dbug_level': logging.INFO,
}


################################################################
# Misceleous functions
################################################################

def config_logger(level=logging.DEBUG, stream=sys.stdout):
    """Configure the logging facility"""
    logging.basicConfig(
        level=level,
        stream=stream,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S")

HEX_CHARS = '0123456789ABCDEF'
def random_id(id_len=16):
    """Create a random id"""
    res = ""
    for _ in range(id_len):
        res += HEX_CHARS[int(random.randint(0, len(HEX_CHARS) - 1))]
    return res

################################################################
# Instance detection actor
################################################################

class ScannerWorkerActor(pykka.ThreadingActor):
    """Scanner Worker Actor"""

    def __init__(self, main_scanner_actor=None):
        """Initialize the actor instance"""
        super(ScannerWorkerActor, self).__init__()
        self.main_scanner_actor = main_scanner_actor

    def ident_superv(self, message):
        """Identify a supervisor on an IP addr"""
        ip_addr = message.get('ip_addr')
        result = {
            'status': ERROR,
            'reason': 'No supervisor detected on {}'.format(ip_addr)
        }

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            sock.connect((ip_addr, SUPERV_PORT))
            sock.shutdown(socket.SHUT_RDWR)
            connection = 'http://{}:{}/RPC2'.format(ip_addr, SUPERV_PORT)
            logging.debug('Checking supervisor on %s', connection)
            server = xmlrpc.client.ServerProxy(connection)
            try:
                state = server.supervisor.getState()
                if state.get('statename', 'UNKNOWN') == 'RUNNING':
                    reason = 'supervisor found on {}'.format(ip_addr)
                    logging.debug(reason)
                    result = {
                        'status': OK,
                        'reason': reason
                    }
            except Exception as err:
                logging.debug('Exception [%s] identifying supervisor', err)
        except Exception as err:
            # Port error
            # logging.error('Port error [%s]', err)
            pass
        sock.close()
        del sock
        message['cmd'] = CMD_SCAN_DONE
        if self.main_scanner_actor:
            self.main_scanner_actor.tell({**message, **result})
        else:
            logging.info('Ident supervisor result: %s', repr(message))

    def on_receive(self, message):
        """process a message"""
        cmd = message.get('cmd', None)
        if not message:
            logging.error('Worker received a message with no command: %s', repr(message))
            return 'ERROR'
        if cmd == CMD_IDENT_SUPERV:
            self.ident_superv(message)
            return 'IDENT_SUPERV {}'.format(message.get('ip_addr', '????'))
        # if cmd == CMD_DO_SCAN:
        #     self.do_scan(message)
        #     return 'SCAN {}'.format(message.get('id'))
        if cmd == CMD_TERMINATE:
            self.stop()
            return 'STOPPED'
        logging.error('Worker received an invalid command: %s', cmd)
        return 'ERROR'

################################################################
# Main scanner actor
################################################################

class MainScannerActor(pykka.ThreadingActor):
    """Main Scanner Actor"""

    def __init__(self,
                 actor_count=WORKER_ACTOR_COUNT,    # How many workers to use
                 report_queue=None):                # Report queue
        """Initialize the main scanner actor"""
        super(MainScannerActor, self).__init__()
        logging.debug('Initializing the MainScannerActor with %s work actors', actor_count)
        self.report_queue = report_queue
        self.num_requests = 0
        self.actor_count = actor_count
        self.actors_list = []
        self.working_actors = []
        self.available_actors = queue.Queue()
        self.requests_queue = queue.Queue()

        # Create the working actors
        for _ in range(self.actor_count):
            actor = ScannerWorkerActor.start(self.actor_ref)
            self.actors_list.append(actor)
            self.available_actors.put(actor)
        logging.debug('MainScannerActor initialized')

    def do_scan(self, message):
        """ Start a scan """
        scan_id = message.get('id', None)
        if not scan_id:
            logging.error('Start scan with no ID [%s]', repr(message))
            return
        self.requests_queue.put(message)
        self.num_requests += 1

    def scan_done(self, message):
        """ Scan done"""
        scan_id = message.get('id', None)
        actor = message.get('actor', None)
        if not scan_id or not actor:
            logging.error('Scan done, bot no scan_id or actor in message')
            return
        message.pop('actor')
        self.available_actors.put(actor)
        self.working_actors.remove(actor)
        if self.report_queue:
            self.report_queue.put(message)

    def terminate(self):
        """Terminate"""
        for actor in self.actors_list:
            actor.tell({'cmd': CMD_TERMINATE})
            for _ in range(50):
                if not actor.is_alive():
                    break
                time.sleep(0.1)
        self.stop()

    def on_receive(self, message):
        """process an incomming message"""
        cmd = message.get('cmd', None)
        if not cmd:
            logging.error('Main received a message with no command: %s', repr(message))
        else:
            logging.debug('Main actor got command %s', cmd)
            if cmd in [CMD_DO_SCAN, CMD_IDENT_SUPERV]:
                self.do_scan(message)
            elif cmd == CMD_SCAN_DONE:
                self.scan_done(message)
            elif cmd == CMD_TERMINATE:
                self.terminate()
            else:
                logging.error('Main received an invalid command: %s', cmd)

        # Dispatcher
        if not self.requests_queue.empty() and not self.available_actors.empty():
            actor = self.available_actors.get()
            request = self.requests_queue.get()
            logging.debug('Dispatching request [%s]', repr(request))
            request = {'actor': actor, **request}
            self.working_actors.append(actor)
            actor.tell(request)

################################################################
# Main app
################################################################

def print_supervisors(supervisor_ips):
    """List all the available supervisors"""
    for supervisor_ip in supervisor_ips:
        logging.info(supervisor_ip)

def get_supervisors_ips(params=None):
    """ Scanner main function """
    if not params:
        params = PROD_PARAMS

    config_logger(level=params['dbug_level'])
    logging.info('Main started')

    # Main actor
    report_queue = queue.Queue()
    main_scanner_actor = MainScannerActor.start(
        actor_count=params['num_actors'],
        report_queue=report_queue
    )

    # identify hosts with supervisors
    supervisor_ips = []
    num_requests = 0
    for subnet in params['subnets']:
        for ip_addr in params.get('ip_addrs'):
            num_requests += 1
            message = {
                'cmd': CMD_IDENT_SUPERV,
                'ip_addr': subnet.format(ip_addr),
                'id': random_id(),
            }
            main_scanner_actor.tell(message)

    # Wait for the supervisors to be identified
    while num_requests > 0:
        result = report_queue.get()
        logging.debug('>>> %s', result)
        status = result.get('status')
        if status and status == OK:
            supervisor_ips.append(result.get('ip_addr'))
        num_requests -= 1
    sorted_supervisor_ips = []
    if len(supervisor_ips) == 0:
        logging.error('No supervisors found')
    else:
        sorted_supervisor_ips = sorted(supervisor_ips, key=lambda item: socket.inet_aton(item))
        print_supervisors(sorted_supervisor_ips)


    # We're done!
    logging.info('Done, waiting for actors to shutdown')
    main_scanner_actor.tell({'cmd': CMD_TERMINATE})
    time.sleep(2)
    pykka.ActorRegistry.stop_all()
    logging.info('DONE')

    return sorted_supervisor_ips

if __name__ == '__main__':
    get_supervisors_ips()

# EOF
