import zmq
import json
import collections
import numpy
from pymatbridge import Matlab
import pprint as pp

class Dime:
    def __init__(self, name, address):
        """Initializes a Dime client with a name and an address to connect to

        Parameters
        ----------
        name: str
            Name of the client (human-readable)
        address: str
            Protocol type, IP Address, and Port number of the server to connect to
        """
        self.workspace = {} # Receives all variables coming from sync
        self.matlab = Matlab()
        self.name = name
        self.address = address

    def start(self):
        """Start the python client and connect it to the server.

        Returns
        -------
        Result of connection attempt: true or false
        """

        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.address)
        outgoing = {'command': 'connect', 'name': self.name}
        self.socket.send(json.dumps(outgoing))
        if self.socket.recv() == 'OK':
            return True
        else:
            return False

    def exit(self):
        """Tells the server that the client is disconnecting and disconnects the socket."""
        outgoing = {'command': 'exit', 'name': self.name}
        self.socket.send(json.dumps(outgoing))
        self.socket.disconnect(self.address)

    def sync(self, append=False, append_func=None):
    	"""Receives variables from the client's queue on the server.

        Parameters
        ----------
        append: bool
            Determines if the value should be appended to the variable in the
            workspace
        append_func: function
            The function that does the appending. The function must receive two
            objects, concatenate them and return another object. If not
            provided, it will automatically concatenate based on numpy.hstack's
            logic

        Returns
        -------
        If the queue is empty, it returns False. Otherwise, it returns
        the name of the variable that is getting updated
        """

        outgoing = {'command': 'sync', 'name': self.name}
        self.socket.send(json.dumps(outgoing))
        msg = self.socket.recv()
        pp.pprint(msg)
        try:
            msg = self.matlab.json_decode(msg)
            if append == True and msg['func_args'][1] in self.workspace:
                if append_func == None:
                    append_func = self.simple_append
                self.workspace[msg['func_args'][1]] = append_func(self.workspace[msg['func_args'][1]], msg['func_args'][2])
            else:
                self.workspace[msg['func_args'][1]] = msg['func_args'][2]

            return msg['func_args'][1]
        except:
            return False

    def simple_append(self, data1, data2):
        if type(data1) is not numpy.ndarray:
            data1 = numpy.asarray([[data1]])

        if type(data2) is not numpy.ndarray:
            data2 = numpy.asarray([[data2]])

        return numpy.hstack((data1, data2))

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
        outgoing = {'command': 'response', 'name': self.name, 'meta': {'var_name': var_name}, 'args': self.matlab.json_encode(response)}
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

        outgoing = {'command': 'send', 'name': self.name, 'args': var_name}
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

        outgoing = {'command': 'broadcast', 'name': self.name, 'args': var_name}
        self.socket.send(json.dumps(outgoing))

        # Emulate the Matlab API by Receiving the pick up command
        self.socket.recv()

        outgoing = self.create_send_variable_message(var_name, value)
        self.socket.send(json.dumps(outgoing))
        self.socket.recv() # Receive OK

    def get_devices(self):
        """Asks the server for a list of all the devices currently connected."""
        outgoing = {'command': 'get_devices', 'name': self.name}
        self.socket.send(json.dumps(outgoing))
        msg = json.loads(self.socket.recv())
        return msg['response']
