import zmq
import json
import collections
from pymatbridge import Matlab

class Dime:
    def __init__(self):
        self.workspace = {} # Receives all variables coming from sync
        self.matlab = Matlab()

    def start(self, name, address):
	"""Start the python client and connect it to the server.

	Parameters
	----------
	name: str
	    Name of the client (human-readable)
	address: str
	    Protocol type, IP Address, and Port number of the server to connect to

	Returns
	-------
	Result of connection attempt: 'true' or 'false'
	"""
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
	"""Tells the server that the client is disconnecting and disconnects the socket."""
        self.socket.send('exit')
        self.socket.disconnect(self.address)

    def sync(self):
	"""Receives variables from the client's queue on the server."""
        outgoing = {'command': 'sync'}
        self.socket.send(json.dumps(outgoing))
        msg = self.socket.recv()
        try:
            msg = self.matlab.json_decode(msg)
            self.workspace[msg['func_args'][1]] = msg['func_args'][2]
            return True
        except:
            return False

    def create_send_variable_message(self, var_name, value):
        """Create a message similar to the Matlab API's messages for sending variables

	Parameters
	----------
	var_name: str
	    Name of the variable to be included in the message
	value: int, str
	    Value of the variable indicated by var_name

	Returns
	-------
	Dictionary with the same fields generated by the MATLAB API
	"""
        response = {'content': {'stdout': '', 'figures': [], 'datadir': '/tmp MatlabData/'}, 'result': value, 'success': True}
        outgoing = {'command': 'response', 'meta': {'var_name': var_name}, 'args': self.matlab.json_encode(response)}
        return outgoing

    def send_var(self, recipient_name, var_name, value):
	"""Send a variable to a specific client

	Parameters
	----------
	recipient_name: str
	    Name of the recipient (connected to the server) that will receive the message
	var_name: str
	    Name of the variable to be sent
	value: str, int
	    Value of the variable to be sent
	"""
        outgoing = {'command': 'send', 'args': var_name}
        self.socket.send(json.dumps(outgoing))

        # Emulate the Matlab API by Receiving the pick up command
        self.socket.recv()

        outgoing = self.create_send_variable_message(var_name, value)
        outgoing['meta']['recipient_name'] = recipient_name
        self.socket.send(json.dumps(outgoing))
        self.socket.recv() # Receive an OK

    def broadcast(self, var_name, value):
	"""Broadcast a variable to all clients.

	Parameters
	----------
	var_name: str
	    Name of the variable to be broadcasted
	value: str, int
	    Value of the variable to be broadcasted
	"""
        outgoing = {'command': 'broadcast', 'args': var_name}
        self.socket.send(json.dumps(outgoing))

        # Emulate the Matlab API by Receiving the pick up command
        self.socket.recv()

        outgoing = self.create_send_variable_message(var_name, value)
        self.socket.send(json.dumps(outgoing))
        self.socket.recv() # Receive OK

    def get_devices(self):
	"""Asks the server for a list of all the devices currently connected."""
        outgoing = {'command': 'get_devices'}
        self.socket.send(json.dumps(outgoing))
        msg = json.loads(self.socket.recv())
        return msg['response']
