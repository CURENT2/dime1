#!/usr/bin/python
import time
import threading
import pymatbridge
import Queue
import argparse
import json
import logging
import sys
import zmq
from threading import Thread
from pymatbridge import Matlab

connected_clients = {}

response_messages = {
    'INVALID_SYNTAX': {'code': 400, 'message': 'Invalid syntax'},
    'NO_COMMAND': {'code': 401, 'message': 'No command specified'},
    'NOT_DECODABLE': {'code': 402, 'message': 'Message was not decodable'},
    'NOT_CONNECTED': {'code': 403, 'message': 'Not connected. Connect first.'},
    'INVALID_ARGUMENTS': {'code': 404, 'message': 'Invalid arguments specified'},
    # OK is not here and is sent as a single string for speed
}

def create_response(success, msg):
    return json.dumps({'success': success, 'args': msg})

def worker_routine(worker_url, context = None):
    """Handle client requests in a workers thread"""

    context = context or zmq.Context.instance()
    matlab = Matlab()
    matlab.start(run_matlab_instance=False, act_as_server=True, address=address, context=context) # Don't start a new instance and let matlab connect
    socket = matlab.socket # This is a simple ZMQ socket but from the matlab object

    while True:
        msg = socket.recv()
        decoded_message = msg # Default
        try: # to decode the message as a JSON object using the PyMatEncoder
            decoded_message = matlab.json_decode(msg)
        except:
            # The message is not decodable
            response = create_response(False, response_messages['NOT_DECODABLE'])
            socket.send(response)
            logging.debug("Message {} not decodable".format(msg))#MOA::what?
            continue

        # No command, no work!
        if 'command' not in decoded_message:
            response = create_response(False, response_messages['NO_COMMAND'])
            socket.send(response)
            logging.debug("Error: no command specified")
            continue

        # Get the name of the client and tell them to connect if it's not provided
        name = ''
        if 'name' not in decoded_message:
            response = create_response(False, response_messages['NOT_CONNECTED'])
            socket.send(response)
            continue;
        else:
            name = decoded_message['name']

        # COMMAND:CONNECT
        if decoded_message['command'] == 'connect':
            if 'name' not in decoded_message:
                response = create_response(False, response_messages['INVALID_ARGUMENTS'])
                socket.send(response)
                logging.debug("Invalid arguments")
                continue

            # If name is duplicate then replace uid with new one
            name = decoded_message['name']
            if name_is_duplicate(name):
                logging.debug("New client hijacked old client with name {}".format(name))
                socket.send('OK')
            else: # Then this is a completely new client connecting
                connected_clients[name] = {}
                connected_clients[name]['queue'] = Queue.Queue()
                connected_clients[name]['last_command'] = ''

                socket.send('OK')
                logging.debug("New client with name {} now connected".format(name))
            continue

        # COMMAND:EXIT
        if decoded_message['command'] == 'exit':
            detach(socket, decoded_message['name'])
            continue

        # COMMAND:SYNC
        if decoded_message['command'] == 'sync':
            connected_clients[name]['last_command'] = 'sync'
            # See if the client has anything in its queue
            try:
                message_to_send = connected_clients[name]['queue'].get(False)
                if message_to_send['is_code']:
                    matlab.run_code(message_to_send['value'])
                else:
                    matlab.set_variable(message_to_send['var_name'], message_to_send['value'])
            except Queue.Empty:
                logging.debug("{}'s queue is empty".format(name))
                matlab.socket.send('OK')

        # COMMAND:SEND
        if decoded_message['command'] == 'send':
            connected_clients[name]['last_command'] = 'send'
            matlab.get_variable(decoded_message['args'])

        # COMMAND:BROADCAST
        if decoded_message['command'] == 'broadcast':
            connected_clients[name]['last_command'] = 'broadcast'
            matlab.get_variable(decoded_message['args'])

        # COMMAND:GET_DEVICES
        if decoded_message['command'] == 'get_devices':
            connected_clients[name]['last_command'] = 'get_devices'
            outgoing = {}
            outgoing['response'] = []
            for key in connected_clients:
                outgoing['response'].append(key)

            outgoing = matlab.json_encode(outgoing)
            matlab.socket.send(outgoing)

        # COMMAND:RUN_CODE MOA::Needs testing
        if decoded_message['command'] == 'run_code':
            connected_clients[name]['last_command'] = 'get_devices'
            recipient_name = decoded_message['args']['recipient_name']
            connected_clients[recipient_name]['queue'].put({
                'var_name': '',
                'value': decoded_message['args']['code'],
                'is_code': True
                })
            matlab.socket.send('OK')

        # COMMAND:RESPONSE
        elif decoded_message['command'] == 'response':
            decoded_pymat_response = matlab.json_decode(decoded_message['args'])
            if connected_clients[name]['last_command'] == 'broadcast':
                # Push the variable to all other client queues
                for client_name in connected_clients:
                    if client_name == name:
                        continue
                    var_name = get_name(decoded_message)
                    #logging.debug("Adding {} to {}'s queue".format(var_name, connected_clients[uid]['name']))
                    # logging.debug("Number of elements in {}'s queue is {}".format(connected_clients[uid]['name'], connected_clients[uid]['queue'].qsize()))
                    connected_clients[client_name]['queue'].put({
                        'var_name': var_name,
                        'value': decoded_pymat_response['result'],
                        'is_code': False })

            # If we are sending to only one recipient
            elif connected_clients[name]['last_command'] == 'send':
                # Push the variable to the recipient
                recipient_name = decoded_message['meta']['recipient_name']
                var_name = get_name(decoded_message)
                for client_name in connected_clients:
                    if client_name == recipient_name:
                        connected_clients[client_name]['queue'].put({
                            'var_name': var_name,
                            'value': decoded_pymat_response['result'],
                            'is_code': False
                            })
                        logging.debug("Adding {} to {}'s queue".format(var_name, client_name))

            else:
                pass
            connected_clients[name]['last_command'] = 'response'
            matlab.socket.send('OK')

# Gets the variable name from a response message
def get_name(response):
    if 'meta' in response:
        if 'var_name' in response['meta']:
            return response['meta']['var_name']

    # Return a default variable name if not found
    return 'temp'

# Checks to see if the name is duplicate
def name_is_duplicate(name):
    """Check if this name is duplicate amongst connected clients."""
    return name in connected_clients

# Detaches a client from the server
def detach(socket, name):
    socket.send('OK')
    logging.debug("Exit signal received from a client")
    if (name in connected_clients):
        del connected_clients[name]

if __name__ == '__main__':
    #Check for address specification in command line
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', default=False, help='Run in debug mode', action='store_true')
    parser.add_argument('address', nargs='?', default='ipc:///tmp/dime', help='Input the server address here')
    parser.add_argument('--workers', default=5, help='The number of worker threads')
    args = parser.parse_args()

    # Initialize logger
    log_level = logging.DEBUG if args.debug else logging.ERROR
    logging.basicConfig(stream=sys.stdout, level=log_level, format='%(asctime)s : %(message)s')

    # Number of worker threads
    n_worker_threads = int(args.workers)

    address = args.address
    worker_address = 'inproc://dime/workers' # Inner address for DEALER-WORKER communications
    context = zmq.Context.instance()

    # Create router socket to talk to clients
    clients_socket = context.socket(zmq.ROUTER)
    clients_socket.bind(address)

    # Create dealer socket to talk to workers
    workers_socket = context.socket(zmq.DEALER)
    workers_socket.bind(worker_address)

    print "Serving on {} with {} worker threads".format(address, n_worker_threads)

    for i in range(n_worker_threads):
        thread = threading.Thread(target=worker_routine, args=(worker_address,))
        thread.daemon = True
        thread.start()

    # Make a device for routing from clients to workers
    try:
        zmq.device(zmq.QUEUE, clients_socket, workers_socket)
    except (KeyboardInterrupt, SystemExit):
        clients_socket.close()
        workers_socket.close()

        # Terminating the context would cause errors in the sockets but not stop them
        # context.term()
        sys.exit()
