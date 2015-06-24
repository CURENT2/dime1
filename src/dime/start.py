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
    decoded_msg = matlab.json_decode(msg)
    if 'command' not in decoded_msg:
        # panic for now!
        return
    if decoded_msg['command'] == 'sync':
        connected_clients[client_id]['last_command'] = 'sync'
        # See if the clients have anything in their queues
        if connected_clients[client_id]['queue'].empty():
            print "{}'s queue is empty".format(
                connected_clients[client_id]['name'])
            matlab.socket.send_multipart([client_id, '', 'COMPLETE'])
        else:
            message_to_send=connected_clients[client_id]['queue'].get(False)
            # The first value in message_to_send is the variable's name
            matlab.set_variable(client_id, message_to_send[0],
                message_to_send[1])
            print "Sending message to ", \
                connected_clients[client_id]['name']

    if decoded_msg['command'] == 'send':
        connected_clients[client_id]['last_command'] = 'send'
        matlab.get_variable(client_id, decoded_msg['args'])

    if decoded_msg['command'] == 'broadcast':
        connected_clients[client_id]['last_command'] = 'broadcast'
        matlab.get_variable(client_id, decoded_msg['args'])

    if decoded_msg['command'] == 'get_devices':
        connected_clients[client_id]['last_command'] = 'get_devices'
        outgoing = {}
        outgoing['response'] = []
        for key in connected_clients:
            outgoing['response'].append(connected_clients[key]['name'])

        outgoing = matlab.json_encode(outgoing)
        matlab.socket.send_multipart([client_id, '', outgoing])

    elif decoded_msg['command'] == 'response':
        decoded_pymat_response = matlab.json_decode(decoded_msg['args'])
        matlab.socket.send_multipart([client_id, '', 'OK'])
        if connected_clients[client_id]['last_command'] == 'broadcast':
            # Push the variable to all other client queues
            for uid in connected_clients:
                if uid == client_id:
                    continue
                var_name = get_name(decoded_msg)
                print "Adding {} to {}'s queue".format(var_name,
                    connected_clients[uid]['name'])
                connected_clients[uid]['queue'].put((var_name,
                    decoded_pymat_response['result']))

        # If we are sending to only one recipient
        elif connected_clients[client_id]['last_command'] == 'send':
            # Push the variable to the recipient
            recipient_name = decoded_msg['meta']['recipient_name']
            var_name = get_name(decoded_msg)
            for uid in connected_clients:
                if connected_clients[uid]['name'] == recipient_name:
                    connected_clients[uid]['queue'].put((var_name,
                        decoded_pymat_response['result']))
                    print "Adding {} to {}'s queue".format(var_name,
                        connected_clients[uid]['name'])

        else:
            pass
        connected_clients[client_id]['last_command'] = 'response'

def get_name(response):
    if 'meta' in response:
        if 'var_name' in response['meta']:
            return response['meta']['var_name']

    # Return a default variable name if not found
    return 'temp'

def name_is_duplicate(name):
    """Check if this name is duplicate amongst connected clients."""
    for key in connected_clients:
        if connected_clients[key]['name'] == name:
            return True

    return False

def print_connected():
    """Prints client_id and name for each connected client."""
    print "Clients include: "
    for key in connected_clients:
        print connected_clients[key]['name']

if __name__ == '__main__':
    #Check for address specification in command line
    parser = argparse.ArgumentParser()
    parser.add_argument('address', nargs='?', default='ipc:///tmp/dime', help='input the server address here')
    args = parser.parse_args()
    address = args.address
    print "Server on the following address: {}".format(address)

    matlab = Matlab()
    matlab.start(True, True, address) # Don't start a new instance and let matlab connect
    socket = matlab.socket

    while True:
        msg = socket.recv_multipart()
        uid = msg[0]
        client_name = msg[2]
        if client_name == 'exit': # Check for exit signal
            matlab.socket.send_multipart([uid, '', 'OK'])
            print "Exit signal received from a client"
            if (uid in connected_clients):
                del connected_clients[uid]
            continue
        if uid in connected_clients:
            thread = Thread(target=dispatch, args=(uid, client_name,))
            thread.start()
        else:
            if name_is_duplicate(client_name) == False:
                connected_clients[uid] = {}
                connected_clients[uid]['name'] = client_name
                connected_clients[uid]['queue'] = Queue.Queue()
                connected_clients[uid]['last_command'] = ''

                if 'python' in client_name:
	            #Scrap the matlab socket and instead make a python one
		    connected_clients[uid]['type'] = 'python'
		    print 'Python detected -- using different socket'
                    continue

		connected_clients[uid]['type'] = 'matlab'
                socket.send_multipart([uid, '', 'CONNECTED'])
                print "New client with name {} now connected"\
                    .format(client_name)
            else:
                # Send a no message if we have a duplicate name
                print "Duplicate name received"
                socket.send_multipart([uid, '', 'DUPLICATE_NAME_ERROR'])
