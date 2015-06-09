#/usr/bin/python
import time
import pprint
import threading
import pymatbridge
from threading import Thread
from pymatbridge import Matlab

connected_clients = {}

def dispatch(client_id, msg):
    """Perform a sequence of things on the client in a separate thread."""
    
    print_connected()

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
        print "The following message was received: "
        print msg
        if (msg[0] in connected_clients):
            thread = Thread(target=dispatch, args=(msg[0], msg[2],))
            thread.start()
        else:
            if name_is_duplicate(msg[2]) == False:
                connected_clients[msg[0]] = msg[2]
                socket.send_multipart([msg[0], '', 'CONNECTED'])
                print_connected()
            else:
                # Send a no message
                print "Duplicate name added"
                socket.send_multipart([msg[0], '', 'DUPLICATE_NAME_ERROR'])
                print_connected()

        time.sleep(0.1)
