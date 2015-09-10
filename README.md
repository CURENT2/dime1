### DiME is a Distributed Matlab Environment that helps with the communication between a simulator and multiple modules. DiME uses some codes from the Python-Matlab-Bridge project from [https://github.com/arokem/python-matlab-bridge/](https://github.com/arokem/python-matlab-bridge/)

## Installation

`DiME` communicates with Matlab using zeromq. So before installing
pymatbridge you must have [zmq](http://zeromq.org/intro:get-the-software)
library and [pyzmq](http://zeromq.org/bindings:python) installed on your
machine. These can be installed using

```python
$ pip install pyzmq
```
You will also need  [NumPy](http://www.numpy.org/), which can be installed
using:

```python
$ pip install numpy
```

Finally, if you want to handle sparse arrays, you will need to install
[Scipy](http://scipy.org/). This can also be installed from PyPI, or using
distributions such as [Anaconda](https://store.continuum.io/cshop/anaconda/) or
[Enthought Canopy](https://store.enthought.com/downloads/)


## Usage
- Run `json_startup`
- Go to `./src/dime/` and run `start.py`
- If serving on an address other than ipc:///tmp/dime, specify the address as a command line argument.
- Run a matlab instance and add the DiME repository to its path.
```matlab
addpath(genpath('<Path to the project directory>'))
```
- Run `dime.start('<name of matlab session>', '<optional server address>')` in Matlab. For example if intended as a simulator, on tpc://127.0.0.1:8080 run:
```matlab
dime.start('simulator', 'tpc://127.0.0.1:8080')
```
or if it's a module called control_module1 running on the default address (ipc:///tmp/dime), you would write:
```matlab
dime.start('control_module1')
```

## Methods
These are the Matlab side methods that are provided for sending and receiving information from the server. Note that send_var and broadcast can send any number of variables.
```matlab
% Sends a variable to a specific module
dime.send_var('<recipient name>', '<name of variable to send>', '< name of second variable to send>', '<...>')
```

```matlab
% Sends a variable to all connected modules
dime.broadcast('<name of variable to send>', '<...>')
```

```matlab
% Checks to see if there are any messages from the server and receives up to
% max_msg messages. If not specified, max_msg defaults to 3.
dime.sync()
dime.sync(max_msg)
```

```matlab
% Returns the names of all the connected clients
dime.get_devices()
```

```matlab
% Exits and ends the session with the server
dime.exit()
```

## Building the pymatbridge messenger from source

The installation of `pymatbridge` includes a binary of a mex function to communicate between
Python and Matlab using the [0MQ](http://zeromq.org/) messaging library. This should work
without any need for compilation on most computers. However, in some cases, you might want
to build the pymatbridge messenger from source. To do so, you will need to follow the instructions below:

### Install zmq library
Please refer to the [official guide](http://zeromq.org/intro:get-the-software) on how to
build and install zmq. On Ubuntu, it is as simple as `sudo apt-get install libzmq3-dev`.
On Windows, suggest using the following method:
- Install [MSYS2](http://sourceforge.net/projects/msys2/)
- Run `$ pacman -S make`
- From the zmq source directory, run: `$ sh configure --prefix=$(pwd) --build=x86_64-w64-mingw32`
- Run `$ make`.

After zmq is installed, make sure you can find the location where
libzmq is installed. The library extension name and default location on different systems
are listed below.

| Platform      | library name  | Default locations                 |
| ------------- | ------------- | --------------------------------- |
| MacOS         | libzmq.dylib	| /usr/lib or /usr/local/lib        |
| Linux         | libzmq.so.3	  | /usr/lib or /usr/local/lib        |
| Windows       | libzmq.dll    | C:\Program Files\ZeroMQ 3.2.4\bin |

If you specified a prefix when installing zmq, the library file should be located at the
same prefix location.

The pymatbridge MEX extension needs to be able to locate the zmq library. If it's in a
standard location, you may not need to do anything; if not, there are two ways to
accomplish this:

#### Using the dynamic loader path

One option is to set an environment variable which will point the loader to the right
directory.

On MacOS, you can do this by adding the following line to your .bash_profile (or similar
file for your shell):

	export DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH:<Path to your zmq lib directory>

On Linux, add the following line to your .bash_profile (or similar file for your shell):

	export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:<Path to your zmq lib directory>

On Windows, add the install location of libzmq.dll to the PATH environment variable.
On Windows 7+, typing "environment variables" into the start menu will bring up the
apporpriate Control Panel links.

#### Pointing the binary at the right place

Another option is to modify the MEX binary to point to the right location. This is
preferable in that it doesn't change loader behavior for other libraries than just
the pymatbridge messenger.

On MacOS, you can do this from the root of the pymatbridge code with:

	install_name_tool -change /usr/local/lib/libzmq.3.dylib <Path to your zmq lib directory>/libzmq.3.dylib messenger/maci64/messenger.mexmaci64

On Linux, you can add it to the RPATH:

        patchelf --set-rpath <Path to your zmq lib directory> messenger/mexa64/messenger.mexa64

### Install pyzmq
After step 1 is finished, please grab the latest version of
[pyzmq](http://zeromq.org/bindings:python) and follow the instructions on the official
page. Note that pymatbridge is developed with pyzmq 14.0.0 and older versions might not
be supported. If you have an old version of pyzmq, please update it.

### Future work
Adding the notion of channels. Case in point: Adding an event channel that sends events of the network and is separate from the normal data queue.

[1]: https://pypi.python.org/pypi/pymatbridge
