#!/usr/bin/python
import time
import pprint
import threading
import pymatbridge
import Queue
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
        if decoded_msg['args'] != '':
            matlab.get_variable(client_id, decoded_msg['args'])
        else:
            # Run some code and send a variable
            if connected_clients[client_id]['name'] == 'simulator':
                #matlab.run_code(client_id, 'g = randn')
                matlab.set_variable(client_id, 'g', 83)
            else:
                # See if the clients have anything in their queues
                try:
                    message_to_send = connected_clients[client_id]['queue'].get(False)
                    # The first value in message_to_send is the variable's name
                    matlab.set_variable(client_id, message_to_send[0], message_to_send[1])
                    print "Sending message to ", connected_clients[client_id]['name']
                except Queue.Empty:
                    print "Nothing to send to ", connected_clients[client_id]['name']
                    matlab.socket.send_multipart([client_id, '', 'OK'])

    if decoded_msg['command'] == 'send':
        connected_clients[client_id]['last_command'] = 'send'
        matlab.get_variable(client_id, decoded_msg['args'])

    if decoded_msg['command'] == 'broadcast':
        connected_clients[client_id]['last_command'] = 'broadcast'
        matlab.get_variable(client_id, decoded_msg['args'])

    elif decoded_msg['command'] == 'response':
        decoded_pymat_response = matlab.json_decode(decoded_msg['args'])
        matlab.socket.send_multipart([client_id, '', 'OK'])
        print decoded_pymat_response['result']
        if connected_clients[client_id]['last_command'] == 'broadcast':
            # Push the variable to all other client queues
            for uid in connected_clients:
                if uid == client_id:
                    continue
                print "Putting it in", connected_clients[uid]['name']
                var_name = get_name(decoded_msg)
                connected_clients[uid]['queue'].put((var_name, decoded_pymat_response['result']))

        # If we are sending to only one recipient
        elif connected_clients[client_id]['last_command'] == 'send':
            # Push the variable to the recipient
            recipient_name = decoded_msg['meta']['recipient_name']
            var_name = get_name(decoded_msg)
            for uid in connected_clients:
                if connected_clients[uid]['name'] == recipient_name:
                    connected_clients[uid]['queue'].put((var_name, decoded_pymat_response['result']))

        else:
            pass
        connected_clients[client_id]['last_command'] = 'response'

def get_name(response):
    print response['meta']
    if 'meta' in response:
        if 'var_name' in response['meta']:
            return response['meta']['var_name']

    # Return a default variable name if non found
    return 'temp'

def name_is_duplicate(name):
    """Check if this name is duplicate amongst connected clients."""
    for key in connected_clients:
        if connected_clients[key] == name: # changed from msg[2] to name
            return True

    return False

def print_connected():
    """Prints client_id and name for each connected client."""
    print "Clients include: "
    for key in connected_clients:
        print "id: {} name: {}".format(key, connected_clients[key])

if __name__ == '__main__':
    matlab = Matlab()
    matlab.start(True, True) # Don't start a new instance and let matlab connect
    socket = matlab.socket

    while True:
        msg = socket.recv_multipart()
        uid = msg[0]
        print "The following message was received: "
        print msg
        if (uid in connected_clients):
            thread = Thread(target=dispatch, args=(uid, msg[2],))
            thread.start()
        else:
            if name_is_duplicate(msg[2]) == False:
                connected_clients[uid] = {}
                connected_clients[uid]['name'] = msg[2]
                connected_clients[uid]['queue'] = Queue.Queue()
                connected_clients[uid]['last_command'] = ''
                socket.send_multipart([uid, '', 'CONNECTED'])
            else:
                # Send a no message if we have a duplicate name
                socket.send_multipart([uid, '', 'DUPLICATE_NAME_ERROR'])

        time.sleep(0.1)
