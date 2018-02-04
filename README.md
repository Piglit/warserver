# warserver
an inofficial reimplementation of the Artemis SBS Warserver.


## RUNNING THE WARSERVER ON UNIX SYSTEMS
This section describes installing, configuring and running the warserver from command line on an Unix-System like Linux or MacOS. For Windows read the section [RUNNING THE WARSERVER ON WINDOWS]

# DEPENDENCIES
First make sure you have installed the dependencies
* python3
* tkinter (python3-tk)
* Pyro4 (python3-pyro4) 

# INSTALLATION
The warserver consists of python scripts and does not need installation.

# USEAGE
The WarServer can be started from command line. 
    call:
	`warserver.py`
    or
	`python warserver.py`
    to start the server. 
    If you run into trouble, change your working directory to `artoffwar/core` where the `warserver.py` file is located.

Now Artemis clients can connect to the server.  
The warserver itself has no graphical interface, but you can start the admiral screen client, as soon as the server has started.

To start the admiral screen, 
	`admiral.py`
    or
	`python admiral.py`
    located the artoffwar/client folder.

# CONFIGURATION
The settings of the war server can be configured with a configuration file.  
Change the values of this file to adjust the settings.  
The warserver loads artoffwar/core/default.cfg per default.  
To load some other configuration file, call:
	`warserver.py --config <FILENAME>`


# SAVING AND LOADING
The warserver creates an autosave file at the end of every turn.  
    To load an save file, run:
	`warserver.py --load <FILENAME>`
    The default savegame folder is SaveGamesWarServer in the program folder.


# ADVANCED NETWORKING OPTIONS
To enable custom python clients (e.g. the admiral screen client) to connect to the warserver, pyro is used.
Without configuration the warserver start a pyro naming server and connects itself to it. Clients will look for that naming server in your network and use it to connect themself to the warserver.
If there is already a pyro naming server inside your network, that responds to broadcast requests (like the one the warserever starts), the warserver will not start an own naming server, but instead connect to the existing one.
If there is a pyro naming server inside your network, that does not respond to broadcast requests, you may still use that one, by providing its hostname to the warserver:
	`warserver.py --pyro_host <HOSTNAME or IP>`
If you do not want the warserver to start a pyro naming server inside your network that responds to broadcast requests, start the warserver with the hostname it should listen to:
	`warserver.py --pyro_host <THIS MACHINES HOSTNAME or IP>`
Notice that your clients may not be able to find the naming server without further configuration.
If you do not want a pyro naming server in your network at all, you should start it with localhost:
	`warserver.py --pyro_host localhost`
The naming server will now only listen to requests from your machine and has there is no access from the network to it at all. Notice that only clients on your machine will be able to connect to the server.

To run your pyro naming server call:
	`python -m Pyro4.naming`
This will fasten the startup process of the warserver, since the lookup for a naming server does not need to time out. Notice that this naming server will listen on localhost, without further configuration.

Further information about pyro can be found here:
https://pythonhosted.org/Pyro4/

tl;dr:
If you want your admiral screen on the same machine the warserver runs, call:
	`warserver.py --pyro_host localhost`
If you want to run the admiral screen on another machine, simply call:
	`warserver.py`
	

# IMPLEMENTING CUSTOM CLIENTS
You may implement your own client to control the warserver.
To connect a python client to the warserver, call:
	`game=Pyro4.Proxy('PYRONAME:warserver_game_master')`
from your python client. Now you have access to the methods that are implemented in artoffwar/core/pyro_connector.py. 
If you want to use an interactive shell as client, enter:
	`ipython -i -c "import Pyro4; game=Pyro4.Proxy('PYRONAME:warserver_game_master')"`
Now you can call the methods of the game object to interact with the WarServer.
To show available commands, enter dir(game). Ignore methods that start with _.


# CONNECT ARTEMIS
Start Artemis on any computer inside your network.
Press "Start Server".
Press "Join War Server".
Enter the IP-Address or URL of the machine running the WarServer.
Press "Connect To War Server".

Now Artemis clients can connect to the Artemis Server.
They must enter the IP-Address of the Artemis Server, not the Address of the WarServer.


## RUNNING THE WARSERVER ON WINDOWS
# WINDOWS INSTALLATION FOR DUMMIES
First you need to install the dependencies:

python3
you can get it from https://www.python.org/downloads/ 
Download the latest Version of Python 3.
If unsure, select the "Windows x86-64 executable installer".
Run the installer. Make sure to select "Add Python to PATH" in the installer dialog.
For troubleshooting visit: https://docs.python.org/3.3/using/windows.html
