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
# from xml.etree.ElementTree import XML

from gevent import monkey
monkey.patch_all()
# import requests
# import zmq

import pykka

################################################################
# Constants, configuration, etc
################################################################
SUPERV_PORT = 9001                  # supervisord RPC port
# WATCHMAN_PORT_OFFSET = 1            # Offset to watchman port
# VALID_INSTANCE_NAME_PREFIX = 'CMIA' # Only instances which name starts with

UDP_BUFFER_SIZE = 512
UDP_TIMEOUT = 5

ERROR = 'error'
OK = 'ok'

WORKER_ACTOR_COUNT = 1

CMD_IDENT_SUPERV = 'ident_superv'
CMD_DO_SCAN = 'do_scan'
CMD_SCAN_DONE = 'scan_done'
CMD_TERMINATE = 'terminate'

# COLLECTORS_INFO = [
#     {
#         'ip_addr': '10.190.6.162',
#         'collect_port': '55094',
#         'api_port': '8088',
#         'api_url': 'http://{}:{}/api/servidores',
#     },
#     {
#         'ip_addr': '10.190.6.51',
#         'collect_port': '55094',
#         'api_port': '8080',
#         'api_url': 'http://{}:{}/api/servidores',
#     },
# ]

PROD_PARAMS = {
    # 'subnets': ['10.190.6.{}', '10.190.0.{}', '192.168.2.{}', '192.168.246.{}'],
    # 'subnets': ['10.190.6.{}'],
    'subnets': ['192.168.8.{}'],
    'ip_addrs': list(range(1, 255)),
    # 'ports': ['5{}{}00'.format(k, l) for k in [4, 5, 6, 7] for l in range(10)],
    'num_actors': 128,
    'dbug_level': logging.INFO,
    # 'collectors_info': COLLECTORS_INFO,
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

    # def scan_port(self, params):
    #     """Scan a hosts port"""
    #     t_ini = time.time()
    #     ip_addr = params.get('ip_addr')
    #     port = int(params.get('port')) + WATCHMAN_PORT_OFFSET

    #     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #     sock.settimeout(UDP_TIMEOUT)
    #     try:
    #         sock.connect((ip_addr, port))
    #     except Exception as err:
    #         del sock
    #         err_msg = 'Exception openning socket: [%s]' % err
    #         logging.error(err_msg)
    #         return {
    #             **params,
    #             'status': ERROR,
    #             'reason': err_msg
    #         }

    #     request = '<reporta />'
    #     response = None
    #     err_msg = 'Not specified'
    #     while True:
    #         sock.send(request.encode())
    #         logging.debug("Waiting for response in %s seconds", str(UDP_TIMEOUT))
    #         try:
    #             response = sock.recv(UDP_BUFFER_SIZE).decode()
    #             break
    #         except ConnectionError:
    #             err_msg = 'ConnectionError on [%s:%s]' % (ip_addr, port)
    #             break
    #         except socket.timeout:
    #             if (time.time() - t_ini) > 10:
    #                 err_msg = 'No response from [%s:%s]' % (ip_addr, port)
    #                 break
    #         except Exception as err:
    #             err_msg = 'Exception %s on [%s:%s]' % (err, ip_addr, port)
    #             break
    #     # Close the port
    #     sock.shutdown(socket.SHUT_RDWR)
    #     sock.close()
    #     del sock
    #     if response:
    #         return {
    #             **params,
    #             'status': OK,
    #             'response': response,
    #             'runtime': time.time() - t_ini
    #         }
    #     logging.debug(err_msg)
    #     return {
    #         **params,
    #         'status': ERROR,
    #         'reason': err_msg
    #     }

    # def analyze_response(self, response):
    #     """Analyze the watchman response"""
    #     status = response.get('status')
    #     if status != OK:
    #         return response
    #     try:
    #         parsed = XML(response.get('response'))
    #         try:
    #             instance_id = parsed.find('./identificadorUnico').text
    #         except AttributeError:
    #             instance_id = parsed.find('./numeroSecuencial').text
    #             instance_id = '{}:{}'.format(response.get('ip_addr'), response.get('port'))
    #         logging.info(
    #             'Instance [%s] identified at %s:%s',
    #             instance_id,
    #             response.get('ip_addr'),
    #             response.get('port')
    #         )
    #         if 'response' in response:
    #             del response['response']
    #         return {
    #             **response,
    #             'instance_id': instance_id
    #         }
    #     except Exception as err:
    #         logging.error('No instance identified in %s [%s]', response, err)
    #     return None

    # def do_scan(self, message):
    #     """ Do the scan """
    #     result = self.analyze_response(self.scan_port(message))
    #     # Replace command to main actor
    #     result['cmd'] = CMD_SCAN_DONE
    #     if self.main_scanner_actor:
    #         self.main_scanner_actor.tell(result)
    #     else:
    #         logging.info('Scan result: %s', repr(result))

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
# Instance information updater
################################################################

# class Updater():
#     """Updates the collector"""

#     def __init__(self, instances, collectors_info):
#         """Initialize the Updater"""
#         self.instances = instances
#         self.collectors_info = collectors_info
#         self.hosts_info = {}

#     def get_hostnames(self):
#         """Get the hostname from the collector"""
#         logging.debug('Getting hostnames from the collector')
#         response = None
#         for collector_info in self.collectors_info:
#             request = collector_info.get('api_url').format(
#                 collector_info.get('ip_addr'),
#                 collector_info.get('api_port')
#             )
#             try:
#                 response = requests.get(request)
#                 if response.status_code == requests.codes.ok:
#                     if response.json().get('status') == OK:
#                         break
#                     logging.debug('Got collector respose status %s', response.status_code)
#                 else:
#                     logging.debug('Got HTTP respose status %s', response.status_code)
#                 logging.debug('Did not received an OK response')
#             except Exception as err:
#                 logging.debug('Exception getting hosts: %s', err)
#         if not response:
#             raise Exception('Could not get hostnames')
#         for host in response.json().get('result'):
#             self.hosts_info[host.get('direccion_ip')] = {
#                 'hostname': host.get('nombre'),
#                 'instancias': [],
#                 'direcciones_ip': [host.get('direccion_ip')]
#             }

#     def process_instances(self):
#         """Asign instances to hosts"""
#         for instance in self.instances:
#             if not instance.get('instance_id').upper().startswith(VALID_INSTANCE_NAME_PREFIX):
#                 continue
#             ip_addr = instance.get('ip_addr')
#             if not ip_addr in self.hosts_info:
#                 octets = ip_addr.split('.')
#                 name = 'srv-{}-{}'.format(octets[2], octets[3])
#                 self.hosts_info[ip_addr] = {
#                     'hostname': name,
#                     'instancias': [],
#                     'direcciones_ip': [ip_addr],
#                 }
#                 logging.debug('Identified new host %s on %s', name, ip_addr)
#             self.hosts_info[ip_addr]['instancias'].append({
#                 'id_instancia': instance.get('instance_id'),
#                 'puerto': instance.get('port')
#             })

#     def update_collectors(self):
#         """Update the collectors"""
#         logging.debug('Updating collectors')
#         context = zmq.Context()
#         for collector in self.collectors_info:

#             for host_info in self.hosts_info.values():
#                 # Skip hosts with no instances
#                 if not host_info['instancias']:
#                     continue
#                 connection = 'tcp://{}:{}'.format(collector.get('ip_addr'), collector.get('collect_port'))
#                 message = json.dumps(host_info)
#                 logging.debug('Sending message to collector %s', message)
#                 sock = context.socket(zmq.REQ)
#                 sock.connect(connection)
#                 sock.send_string(message)

#                 t_ini = time.time()
#                 ack = None
#                 while True:
#                     try:
#                         ack = sock.recv_string(zmq.DONTWAIT)
#                     except zmq.Again:
#                         time.sleep(1)
#                         if time.time() - t_ini > 10:
#                             logging.info('No ACK received from collector %s', collector.get('ip_addr'))
#                             break
#                         # print('*', end='')
#                         # sys.stdout.flush()
#                     else:
#                         logging.info('Collector %s sent ACK [%s]', collector.get('ip_addr'), ack)
#                         break
#                 sock.setsockopt(zmq.LINGER, 0)
#                 sock.close()
#                 del sock

#     def execute(self):
#         """Process the update of the collector"""
#         try:
#             self.get_hostnames()
#         except Exception as err:
#             logging.error('Exception getting hostnames: %s', err)
#             return
#         self.process_instances()
#         self.update_collectors()


################################################################
# Main app
################################################################

# def create_report(detected_instances):
#     """Create the report of detected instances"""
#     result = []
#     logging.info('-' * 60)
#     for instance in detected_instances:
#         line = '{:<12} {:>6} {}'.format(
#             instance.get('ip_addr'),
#             instance.get('port'),
#             instance.get('instance_id')
#         )
#         logging.info(line)
#         if instance.get('instance_id').upper().startswith(VALID_INSTANCE_NAME_PREFIX):
#             result.append({
#                 'ip_addr': instance.get('ip_addr'),
#                 'port': instance.get('port'),
#                 'instance_id': instance.get('instance_id')
#             })
#     return result

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

    # # Scan for instances
    # num_requests = 0
    # for ip_addr in supervisor_ips:
    #     for port in params['ports']:
    #         logging.debug('>>> SCANNING %s:%s', ip_addr, port)
    #         num_requests += 1
    #         main_scanner_actor.tell({
    #             'cmd': CMD_DO_SCAN,
    #             'ip_addr': ip_addr,
    #             'port': port,
    #             'id': random_id(),
    #         })

    # logging.info('Scanning %d ports', num_requests)

    # # Wait until all instances have been identified
    # detected_instances = []
    # while num_requests > 0:
    #     result = report_queue.get()
    #     logging.debug('>>> %s', result)
    #     status = result.get('status')
    #     if status and status == OK:
    #         detected_instances.append(result)
    #     num_requests -= 1

    # instances = create_report(detected_instances)

    # # Update the collectors
    # updater = Updater(instances, params.get('collectors_info'))
    # updater.execute()

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
