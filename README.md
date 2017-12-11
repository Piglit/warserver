# warserver
an inofficial reimplementation of the Artemis SBS Warserver.

DEPENDENCIES
python3
pyro (python-pyro)

USEAGE
python -m Pyro4.naming
this starts a pyro nameserver, so you can connect admiral and game-master interfaces to the warserver

python warserver.py
this will start the warserver. Now you can connect your Artemis server to it (click 'Connect to WarServer' in server menu and enter the ip-address of the machine running the warserver)

now start the gui you like (not implemented yet)
you may also connect from another python script or ipython:
Pyro4.Proxy("PYRONAME:warserver_admiral")
Pyro4.Proxy("PYRONAME:warserver_game_master")

EXAMPLEs:
game = Pyro4.Proxy("PYRONAME:warserver_admiral")
game.get_game_state()

returns the game state

dir(game)

lists all methods you can call. Ignore the private ones (they start with _)
