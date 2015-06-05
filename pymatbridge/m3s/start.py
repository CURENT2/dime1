#!/usr/bin/python
import time
import pprint
import threading
import pymatbridge
from threading import Thread
from pymatbridge import Matlab

connected_clients = {}

# Perform a sequence of things on the client in a separate thread
def dispatch(client_id, msg):
    print "People connected: "
    for key in connected_clients:
        print connected_clients[key]

    decoded_msg = matlab.json_decode(msg)
    if 'command' not in decoded_msg:
        # panic for now!
        return
    if decoded_msg['command'] == 'sync':
        if decoded_msg['args'] != '':
            matlab.get_variable(client_id, decoded_msg['args'])
        else:
            # Run some code and send a variable
            matlab.run_code(client_id, 'g = randn')

    elif decoded_msg['command'] == 'response':
        decoded_pymat_response = matlab.json_decode(decoded_msg['args'])
        matlab.socket.send_multipart([client_id, '', 'OK'])
        print decoded_pymat_response['result']

# Check if this name is duplicate amongst connected clients
def name_is_duplicate(name):
    for key in connected_clients:
        if connected_clients[key] == msg[2]:
            return True

    return False

if __name__ == '__main__':
    matlab = Matlab()
    matlab.start(True, True) # Don't start a new instance and let matlab connect
    socket = matlab.socket

    while True:
        msg = socket.recv_multipart()
        if (msg[0] in connected_clients):
            thread = Thread(target=dispatch, args=(msg[0], msg[2],))
            thread.start()
        else:
            socket.send_multipart([msg[0], '', 'CONNECTED'])
            if name_is_duplicate(msg[2]) == False:
                connected_clients[msg[0]] = msg[2]
            else:
                # Send a no message
                pass

        time.sleep(0.1)
