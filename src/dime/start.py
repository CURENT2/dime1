#!/usr/bin/python
import time
import threading
import pymatbridge
import Queue
import argparse
import json
import logging
import sys
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

def dispatch(client_id, msg):
    """Perform a sequence of things on the client in a separate thread."""
    if msg['command'] == 'sync':
        connected_clients[client_id]['last_command'] = 'sync'
        # See if the client has anything in its queue
        try:
            message_to_send = connected_clients[client_id]['queue'].get(False)
            if message_to_send['is_code']:
                matlab.run_code(client_id, message_to_send['value'])
            else:
                matlab.set_variable(client_id, message_to_send['var_name'], message_to_send['value'])

        except Queue.Empty:
            matlab.socket.send_multipart([client_id, '', 'OK'])
            logging.debug("{}'s queue is empty".format(connected_clients[client_id]['name']))

    if msg['command'] == 'send':
        connected_clients[client_id]['last_command'] = 'send'
        matlab.get_variable(client_id, msg['args'])

    if msg['command'] == 'broadcast':
        connected_clients[client_id]['last_command'] = 'broadcast'
        matlab.get_variable(client_id, msg['args'])

    if msg['command'] == 'get_devices':
        connected_clients[client_id]['last_command'] = 'get_devices'
        outgoing = {}
        outgoing['response'] = []
        for key in connected_clients:
            outgoing['response'].append(connected_clients[key]['name'])

        outgoing = matlab.json_encode(outgoing)
        matlab.socket.send_multipart([client_id, '', outgoing])

    if msg['command'] == 'run_code':
        matlab.socket.send_multipart([client_id, '', 'OK'])
        connected_clients[client_id]['last_command'] = 'get_devices'
        recipient_name = msg['args']['recipient_name']
        recipient_uid = name_to_uid(recipient_name)
        connected_clients[recipient_uid]['queue'].put({
            'var_name': '',
            'value': msg['args']['code'],
            'is_code': True
            })

    elif msg['command'] == 'response':
        decoded_pymat_response = matlab.json_decode(msg['args'])
        matlab.socket.send_multipart([client_id, '', 'OK'])
        if connected_clients[client_id]['last_command'] == 'broadcast':
            # Push the variable to all other client queues
            for uid in connected_clients:
                if uid == client_id:
                    continue
                var_name = get_name(msg)
                logging.debug("Adding {} to {}'s queue".format(var_name, connected_clients[uid]['name']))
                connected_clients[uid]['queue'].put({
                    'var_name': var_name,
                    'value': decoded_pymat_response['result'],
                    'is_code': False })

        # If we are sending to only one recipient
        elif connected_clients[client_id]['last_command'] == 'send':
            # Push the variable to the recipient
            recipient_name = msg['meta']['recipient_name']
            var_name = get_name(msg)
            for uid in connected_clients:
                if connected_clients[uid]['name'] == recipient_name:
                    connected_clients[uid]['queue'].put({
                        'var_name': var_name,
                        'value': decoded_pymat_response['result'],
                        'is_code': False
                        })
                    logging.debug("Adding {} to {}'s queue".format(var_name, connected_clients[uid]['name']))

        else:
            pass
        connected_clients[client_id]['last_command'] = 'response'

# Gets the variable name from a response message
def get_name(response):
    if 'meta' in response:
        if 'var_name' in response['meta']:
            return response['meta']['var_name']

    # Return a default variable name if not found
    return 'temp'

# Converts name to uid!!
def name_to_uid(name):
    for key in connected_clients:
        if connected_clients[key]['name'] == name:
            return key

    return ''

# Checks to see if the name is duplicate
def name_is_duplicate(name):
    """Check if this name is duplicate amongst connected clients."""
    for key in connected_clients:
        if connected_clients[key]['name'] == name:
            return True

    return False

# Detaches a client from the server
def detach(uid):
    matlab.socket.send_multipart([uid, '', 'OK'])
    logging.debug("Exit signal received from a client")
    if (uid in connected_clients):
        del connected_clients[uid]

if __name__ == '__main__':
    #Check for address specification in command line
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', default=False, help='Run in debug mode', action='store_true')
    parser.add_argument('address', nargs='?', default='ipc:///tmp/dime', help='Input the server address here')
    args = parser.parse_args()

    address = args.address

    # Initialize logger
    log_level = logging.DEBUG if args.debug else logging.ERROR
    logging.basicConfig(stream=sys.stdout, level=log_level, format='%(asctime)s : %(message)s')

    matlab = Matlab()
    matlab.start(True, True, address) # Don't start a new instance and let matlab connect
    socket = matlab.socket # This is a simple ZMQ socket but from the matlab object
    print "Serving on {}".format(address)

    while True:
        msg = socket.recv_multipart()
        uid = msg[0]
        decoded_message = msg[2] # Default
        try: # to decode the message as a JSON object using the PyMatEncoder
            decoded_message = matlab.json_decode(msg[2])
        except:
            # Check for exit signal
            if decoded_message == 'exit':
                detach(uid)
            else:
                response = create_response(False, response_messages['NOT_DECODABLE'])
                socket.send_multipart([uid, '', response])
                logging.debug("Message <msg> not decodable")#MOA::what?
                continue

        # No command, no work!
        if 'command' not in decoded_message:
            response = create_response(False, response_messages['NO_COMMAND'])
            socket.send_multipart([uid, '', response])
            logging.debug("Error: no command specified")
            continue

        if uid in connected_clients:
            thread = Thread(target=dispatch, args=(uid, decoded_message,))
            thread.start()
        else:
            if decoded_message['command'] == 'connect':
                if 'args' not in decoded_message or 'name' not in decoded_message['args']:
                    response = create_response(False, response_messages['INVALID_ARGUMENTS'])
                    socket.send_multipart([uid, '', response])
                    logging.debug("Invalid arguments")
                    continue

                # If name is duplicate then replace uid with new one
                if name_is_duplicate(decoded_message['args']['name']):
                    old_uid = name_to_uid(decoded_message['args']['name'])
                    connected_clients[uid] = connected_clients[old_uid]
                    del connected_clients[old_uid]
                    socket.send_multipart([uid, '', 'OK'])
                else: # Then this is a completely new client connecting
                    connected_clients[uid] = {}
                    connected_clients[uid]['name'] = decoded_message['args']['name']
                    connected_clients[uid]['queue'] = Queue.Queue()
                    connected_clients[uid]['last_command'] = ''

                    socket.send_multipart([uid, '', 'OK'])
                    logging.debug("New client with name {} now connected".format(decoded_message['args']['name']))
            else:
                response = create_response(False, response_messages['NOT_CONNECTED'])
                socket.send_multipart([uid, '', response])
