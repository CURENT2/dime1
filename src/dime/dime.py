import zmq
import json
import collections
from pymatbridge import Matlab

class Dime:
    def __init__(self):
        self.workspace = {} # Receives all variables coming from sync
        self.matlab = Matlab()

    def start(self, name, address):
        self.address = address
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(address)
        outgoing = {'command': 'connect', 'args': {'name': name}}
        self.socket.send(json.dumps(outgoing))
        if self.socket.recv() == 'OK':
            return True
        else:
            return False

    def exit(self):
        self.socket.send('exit')
        self.socket.disconnect(self.address)

    def sync(self):
        outgoing = {'command': 'sync'}
        self.socket.send(json.dumps(outgoing))
        msg = self.socket.recv()
        try:
            msg = self.matlab.json_decode(msg)
            self.workspace[msg['func_args'][1]] = msg['func_args'][2]
            return True
        except:
            return False

    # Create a message similar to the Matlab API's messages for sending variables
    def create_send_variable_message(self, var_name, value):
        # Create the message as if it was made by the Matlab API
        response = {'content': {'stdout': '', 'figures': [], 'datadir': '/tmp MatlabData/'}, 'result': value, 'success': True}
        outgoing = {'command': 'response', 'meta': {'var_name': var_name}, 'args': self.matlab.json_encode(response)}
        return outgoing

    # Send a variable to a specific client
    def send_var(self, recipient_name, var_name, value):
        outgoing = {'command': 'send', 'args': var_name}
        self.socket.send(json.dumps(outgoing))

        # Emulate the Matlab API by Receiving the pick up command
        self.socket.recv()

        outgoing = self.create_send_variable_message(var_name, value)
        outgoing['meta']['recipient_name'] = recipient_name
        self.socket.send(json.dumps(outgoing))
        self.socket.recv() # Receive an OK

    # Broadcast a variable to all clients
    def broadcast(self, var_name, value):
        outgoing = {'command': 'broadcast', 'args': var_name}
        self.socket.send(json.dumps(outgoing))

        # Emulate the Matlab API by Receiving the pick up command
        self.socket.recv()

        outgoing = self.create_send_variable_message(var_name, value)
        self.socket.send(json.dumps(outgoing))
        self.socket.recv() # Receive OK

    def get_devices(self):
        outgoing = {'command': 'get_devices'}
        self.socket.send(json.dumps(outgoing))
        msg = json.loads(self.socket.recv())
        return msg['response']
