import zmq
import json

class Dime:
    def __init__(self):
        # TODO: Make this watchable
        self.workspace = {}

    def start(self, name, address):
        self.address = address
        self.context = zmq.Context.instance()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(address)
        outgoing = {'command': 'connect', 'args': {'name': name, 'type': 'python'}}
        self.socket.send(json.dumps(outgoing))
        return self.socket.recv()

    def exit(self):
        self.socket.send('exit')
        self.socket.disconnect(self.address)

    def sync(self):
        outgoing = {'command': 'sync'}
        self.socket.send(json.dumps(outgoing))
        msg = json.loads(self.socket.recv())
        self.workspace[msg['var_name']] = msg['value']

    # TODO
    def send_var():
        pass

    # TODO
    def broadcast():
        pass

    def get_devices(self):
        outgoing = {'command': 'get_devices'}
        self.socket.send(json.dumps(outgoing))
        msg = json.loads(self.socket.recv())
        return msg['response']
