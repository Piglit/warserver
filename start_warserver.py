#!/usr/bin/env python3
import argparse
from core import game_state, engine_turns, engine_artemis, engine_rpc, artemis_connector 
try:
	from core import pyro_connector
	PYRO = True
except ImportError:
	PYRO = False 

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='Starts the Artemis WarServer.') 
	parser.add_argument('--load', '-l', type=open, metavar='FILE', help='Load saved game or scenario from file') 
	#parser.add_argument('--headless', action='store_true', help='run without a gui')
	parser.add_argument('--pyro_nameserver', type=str, help='connect to an existing pyto nameserver')
	args = parser.parse_args()

	print("starting warserver")
	game = game_state.create_game(args.load)
	if False :#not args.headless:
		import client.startmenu
		client.startmenu.start(game)
	else:
		print("starting warserver in headless mode")
		engine_turns.init_turns()
	#print(game)
	artemis_connector.start_server()
	if PYRO:
		if args.pyro_nameserver:
			pyro_connector.start_server(args.pyro_nameserver)
		else:
			pyro_connector.start_server()		
	else:
		print("module Pyro4 not found. Running without Pyro server")

	print("everything is up and running")
