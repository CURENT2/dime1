#!/usr/bin/python
import time
import threading
import pymatbridge
import Queue
import argparse
from threading import Thread
from pymatbridge import Matlab

connected_clients = {}

def dispatch(client_id, msg):
    """Perform a sequence of things on the client in a separate thread."""
    if msg['command'] == 'sync':
        connected_clients[client_id]['last_command'] = 'sync'
        # See if the clients have anything in their queues
        if connected_clients[client_id]['queue'].empty():
            #LOG:DEBUG print "{}'s queue is empty".format(connected_clients[client_id]['name'])
            matlab.socket.send_multipart([client_id, '', 'COMPLETE'])
        else:
            message_to_send=connected_clients[client_id]['queue'].get(False)
            # The first value in message_to_send is the variable's name
            matlab.set_variable(client_id, message_to_send[0],
                message_to_send[1])
            #LOG:DEBUG print "Sending message to ", connected_clients[client_id]['name']

    if msg['command'] == 'send':
        connected_clients[client_id]['last_command'] = 'send'
        matlab.get_variable(client_id, msg['args'])

    if msg['command'] == 'broadcast':
        print "broadcast came"
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

    elif msg['command'] == 'response':
        decoded_pymat_response = matlab.json_decode(msg['args'])
        matlab.socket.send_multipart([client_id, '', 'OK'])
        if connected_clients[client_id]['last_command'] == 'broadcast':
            print "sending for broadcast"
            # Push the variable to all other client queues
            for uid in connected_clients:
                if uid == client_id:
                    continue
                var_name = get_name(msg)
                #LOG DEBUG print "Adding {} to {}'s queue".format(var_name, connected_clients[uid]['name'])
                connected_clients[uid]['queue'].put((var_name,
                    decoded_pymat_response['result']))

        # If we are sending to only one recipient
        elif connected_clients[client_id]['last_command'] == 'send':
            # Push the variable to the recipient
            recipient_name = msg['meta']['recipient_name']
            var_name = get_name(msg)
            for uid in connected_clients:
                if connected_clients[uid]['name'] == recipient_name:
                    connected_clients[uid]['queue'].put((var_name,
                        decoded_pymat_response['result']))
                    #LOG_DEBUG print "Adding {} to {}'s queue".format(var_name, connected_clients[uid]['name'])

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
                # If name is duplicate then replace uid with new one
                if name_is_duplicate(decoded_message['args']['name']):
                    old_uid = name_to_uid(decoded_message['args']['name'])
                    connected_clients[uid] = connected_clients[old_uid]
                    del connected_clients[old_uid]
                    socket.send_multipart([uid, '', 'CONNECTED'])
                else:
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
