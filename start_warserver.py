#!/usr/bin/env python3
import argparse
from core import game_state, engine_turns, artemis_connector

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='Starts the Artemis WarServer.') 
	parser.add_argument('--load', '-l', type=open, metavar='FILE', help='Load saved game or scenario from file') 
	parser.add_argument('--headless', action='store_true', help='run without a gui')
	args = parser.parse_args()

	print("starting warserver")
	game = game_state.create_game(args.load)
	if not args.headless:
		import client.startmenu
		client.startmenu.start(game)
	else:
		print("starting warserver in headless mode")
		engine_turns.init_turns()
	print(game)
	artemis_connector.start_server()
		


