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
                matlab.run_code(client_id, 'g = randn')
            else:
                # See if the clients have anything in their queues
                try:
                    message_to_send = connected_clients[client_id]['queue'].get(False)
                    matlab.run_code(client_id, 'g = ' + str(message_to_send))
                    print "Sending", str(message_to_send)
                except Queue.Empty:
                    print "Nothing to send to ", connected_clients[client_id]['name']
                    matlab.socket.send_multipart([client_id, '', 'OK'])

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
                connected_clients[uid]['queue'].put(decoded_pymat_response['result'])

        else:
            pass
        connected_clients[client_id]['last_command'] = 'response'


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
