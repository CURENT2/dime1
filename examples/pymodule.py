from dime import dime
import argparse
import numpy as np
import logging
import time


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
logger.addHandler(ch)


class DimeModule(object):
    def __init__(self, name, server):
        self.name = name  # module name
        self.server = server  # dime server address
        self.dimec = dime.Dime(name, server)  # dime client instance

        ##### variables in starts #####
        self._sysparam = None  # `SysParam` from simulator
        self._sysname = None  # `SysName`
        self._idxvgs = None  # `Idxvgs` from simulator
        self._varheader = None  # `Varheader`
        self._varvgs = None  # `Varvgs` from simulator, updated every time step
        ##### variables in ends #####

        self._varout = {'t': 0, 'vars': np.array([])} # dict of variables to be sent out

        self._has_sim = False  # flag whether simulator is online
        self._sync_delay = 0.01  # time delay between each `dimec.sync` call

        # initialization structure to simulator. Do not modify. Modify self.idx and call `self.make_init`
        self._init = {"param": ["Bus", "Line"],
                      "vgsvaridx": [],
                      }

        self._interval = 0  # the sampling time interval, 0 = default to simulator step

        # inherited class shall override the following
        self._idx_request = np.array([])  # the indices of variables to be received from simulator
        self._idx_module = {}
        self._header = []  # names of the variables this module produces

    def connect(self):
        logger.info("Module {}, connecting to {}".format(self.name, self.server))
        if self.dimec.start():
            logger.info("Module connected.")

    def disconnect(self):
        logger.info("Module {}, disconnecting".format(self.name))
        self.dimec.exit()

    def process(self, t, data):
        """
        Data processing function
        """
        pass

    def config(self):
        """
        Configure the variable indices and sampling interval
        """
        pass

    def check_sim(self):
        """
        Check if simulator is connected
        """
        self._has_sim = ('sim' in self.dimec.get_devices())
        return self._has_sim

    def run(self):
        self.config()
        self.connect()
        while True:
            if not self.check_sim():
                # logger.info("sim not connected")
                pass

            var_name = self.dimec.sync()
            if var_name is not False:
                var_value = self.dimec.workspace[var_name]

                # process received data
                if var_name == "SysParam":
                    self.process_sysparam(var_value)

                elif var_name == "SysName":
                    self.process_sysname(var_value)

                elif var_name == "Idxvgs":
                    self.process_idxvgs(var_value)

                elif var_name == "Varheader":
                    self.process_varheader(var_value)

                elif var_name == "DONE":
                    self.reset()

                elif var_name == "Varvgs":
                    self.process_varvgs(var_value)

                    # send out variable data
                    # it is assumed here that the module only sends data each time
                    # it receives data from simulator
                    self.make_data()
                    self.send_data()

            time.sleep(self._sync_delay)

    def make_initializer(self):
        """
        Create initialization structure for this module
        """
        self._init["varvgsidx"] = np.array(self._idx_request)

    def process_sysparam(self, data):
        """
        Process `SysParam` received from simulator
        """
        self._sysparam = data

        self.dimec.send_var("sim", "{}".format(self.name), self._init)

    def process_sysname(self, data):
        """
        Process `SysName` received from simulator
        """
        self._sysname = data

    def process_idxvgs(self, data):
        """
        Process `Idxvgs` received from simulator
        """
        self._idxvgs = data

    def process_varheader(self, data):
        """
        Process `Varheader` received from simulator
        """
        self._varheader = data

    def process_varvgs(self, data):
        """
        Process `varvgs` received from simulator
        """
        self._varvgs = data
        logger.info("got data, t={:.4f}".format(self._varvgs['t']))

    def send_data(self):
        """
        Send data to destination by calling `self.dimec.send_var`
        """
        self.dimec.send_var("geovis", "{}_vars".format(self.name), self._varout)
        logger.info("sent data, t={:.4f}".format(self._varout['t']))

    def make_data(self):
        """
        Prepare NMD-based stability assessment data and return as an array
        """
        pass

    def reset(self):
        """
        Reset the internal states after a DONE signal is received
        """
        self._sysparam = None
        self._idxvgs = None
        self._varheader = None
        self._varvgs = None

        self._has_sim = False


class NMD_TSA(DimeModule):
    """
    Dime streaming client for non-linear model decoupling-based transient stability assessment

    Most modifications should take place in this class by overloading the base class functions
    """
    def __init__(self, name, server):
        super().__init__(name, server)

        self._idx_request = [1, 2, 3, 4, 5]
        self._header = ["Margin"]

    def make_data(self):
        super().make_data()
        if self._varvgs:
            self._varout['t'] = self._varvgs['t']
            self._varout['vars'] = np.array([1000])   # replace this with actual data

def main():
    """
    Entry function
    """
    args = cli()
    dimec = NMD_TSA(args.name, args.server)
    try:
        dimec.run()

    except KeyboardInterrupt:
        dimec.disconnect()


def cli():
    """
    Command line argument parse
    """
    parser = argparse.ArgumentParser(description="Example DiME client")
    parser.add_argument('name', help='client name')
    parser.add_argument('--server', help='dime server address',
                        default='ipc:///tmp/dime')
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()

