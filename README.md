# warserver
an inofficial reimplementation of the Artemis SBS Warserver.

DEPENDENCIES
python3
java (optional, needed for the graphical user interface)
pyro (python-pyro) (optional, needed for the command line interface)


USEAGE
There are two ways to run the warserver:
a) with java gui (recomended)
b) headless with python cli (for hackers)

a) run java INSERT NAME HERE.
Configure the WarServer as you wish.
Press "Start WarServer".
The WarServer is running now and waiting for connections.

To start the interface, start the java client TODO NAME OF THE COMMAND on any computer inside your network.
Enter the IP-Address of the WarServer.
On the WarServer screen add the permission level.

b)
If you want to connect interactive python clients, run:
python -m Pyro4.naming
before starting the WarServer.

run warserver.py
The configuration of the WarServer is loaded from settings.cfg.
The WarServer is running now and waiting for connections.

To connect a python client, call:
game=Pyro4.Proxy('PYRONAME:warserver_game_master')
from your python client.

If you want to use an interactive shell as client, enter:
ipython -i -c "import Pyro4; game=Pyro4.Proxy('PYRONAME:warserver_game_master')"
Now you can call the methods of the game object to interact with the WarServer.
To show available commands, enter dir(game). Ignore methods that start with _.


CONNECT ARTEMIS

Start Artemis on any computer inside your network.
Press "Start Server".
Press "Join War Server".
Enter the IP-Address or URL of the machine running the WarServer.
Press "Connect To War Server".

Now Artemis clients can connect to the Artemis Server.
They must enter the IP-Address of the Artemis Server, not the Address of the WarServer.



