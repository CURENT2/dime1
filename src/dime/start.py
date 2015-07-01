#!/usr/bin/python
import time
import threading
import pymatbridge
import Queue
import argparse
import json
from threading import Thread
from pymatbridge import Matlab

connected_clients = {}

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
            #LOG:DEBUG print "{}'s queue is empty".format(connected_clients[client_id]['name'])
            matlab.socket.send_multipart([client_id, '', 'COMPLETE'])

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
            var_name = get_name(msg)
            #LOG DEBUG print "Adding {} to {}'s queue".format(var_name, connected_clients[uid]['name'])
            push_to_clients(client_id, {
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
                    #LOG_DEBUG print "Adding {} to {}'s queue".format(var_name, connected_clients[uid]['name'])

        else:
            pass
        connected_clients[client_id]['last_command'] = 'response'

# Push variable to client queues
def push_to_clients(own_uid, obj):
    for uid in connected_clients:
        if uid == own_uid:
            continue
        connected_clients[uid]['queue'].put(obj)

def get_name(response):
    """Gets the variable name from a response message"""
    if 'meta' in response:
        if 'var_name' in response['meta']:
            return response['meta']['var_name']

    # Return a default variable name if not found
    return 'temp'

def name_to_uid(name):
    """Converts name to uid!!"""
    for key in connected_clients:
        if connected_clients[key]['name'] == name:
            return key

    return ''

def name_is_duplicate(name):
    """Check if this name is duplicate amongst connected clients."""
    for key in connected_clients:
        if connected_clients[key]['name'] == name:
            return True

    return False

def detach(uid):
    """Detaches a client from the server"""
    matlab.socket.send_multipart([uid, '', 'OK'])
    # LOG:DEBUG print "Exit signal received from a client"
    if (uid in connected_clients):
        del connected_clients[uid]

if __name__ == '__main__':
    #Check for address specification in command line
    parser = argparse.ArgumentParser()
    parser.add_argument('address', nargs='?', default='ipc:///tmp/dime', help='input the server address here')
    args = parser.parse_args()
    address = args.address
    print "Serving on {}".format(address)

    matlab = Matlab()
    matlab.start(True, True, address) # Don't start a new instance and let matlab connect
    socket = matlab.socket # This is a simple ZMQ socket but from the matlab object

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
                socket.send_multipart([uid, '', 'MESSAGE NOT DECODABLE'])
                #LOG:DEBUG Message <msg> not decodable
                continue

        # No command, no work!
        if 'command' not in decoded_message:
            socket.send_multipart([uid, '', 'NO COMMAND SPECIFIED'])
            # LOG:ERROR
            continue

        if uid in connected_clients:
            thread = Thread(target=dispatch, args=(uid, decoded_message,))
            thread.start()
        else:
            if decoded_message['command'] == 'connect':
                if 'args' not in decoded_message or 'name' not in decoded_message['args']:
                    socket.send_multipart([uid, '', 'INVALID ARGUMENTS'])
                    # LOG:ERROR
                    continue

                # If name is duplicate then replace uid with new one
                if name_is_duplicate(decoded_message['args']['name']):
                    old_uid = name_to_uid(decoded_message['args']['name'])
                    connected_clients[uid] = connected_clients[old_uid]
                    del connected_clients[old_uid]
                    socket.send_multipart([uid, '', 'CONNECTED'])
                else: # Then this is a completely new client connecting
                    connected_clients[uid] = {}
                    connected_clients[uid]['name'] = decoded_message['args']['name']
                    connected_clients[uid]['type'] = 'matlab' # Default type
                    if 'type' in decoded_message['args']:
                        connected_clients[uid]['type'] = decoded_message['args']['type']
                    connected_clients[uid]['queue'] = Queue.Queue()
                    connected_clients[uid]['last_command'] = ''

                    socket.send_multipart([uid, '', 'CONNECTED'])
                    #LOG:DEBUG print "New client with name {} now connected"\
                        # .format(decoded_message['args']['name'])
            else:
                socket.send_multipart([uid, '', 'CONNECT FIRST'])
