#!/usr/bin/python3
import configparser
import argparse
import pickle
import sys

import engine
import artemis_connector

try:
	import pyro_connector
except ImportError:
	PYRO = False
else:
	PYRO = True



def single_argument_load():
	if len(sys.argv) == 2:
		#handles drag n drop file
		arg = sys.argv[1]
		if not arg.startswith("-"):
			#TODO write to readme: sav and cfg files must not start with -
			if arg.endswith(".sav"):
				start_game_from_save(arg) 
			if arg.endswith(".cfg"):
				start_game_with_config(arg) 
	return False


def multiple_argument_load(args):
	if args.load:
		start_game_from_save(args.load)
	else:
		start_game_with_config(args.config)

def start_game_from_save(filename):
	with open(filename, "rb") as file:
		engine.game=pickle.load(file)
	print("loading saved game " + filename)
	engine.game._start_from_loaded_game()


def start_game_with_config(filename):
	config = configparser.ConfigParser()
	with open(filename, "r") as file:
		config.read_file(file)
	settings = {}
	for key in config["int"]:
		settings[key] = config["int"].getint(key)
	for key in config["float"]:
		settings[key] = config["float"].getfloat(key)
	for key in config["bool"]:
		settings[key] = config["bool"].getboolean(key)
	print("starting new game with configuration from '" + filename + "'")
	engine.game=engine.Game(settings)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Starts the Artemis WarServer.') 
	parser.add_argument('--config', '-c', type=str, default='default.cfg', help='Load config file') 
	parser.add_argument('--load', '-l', type=str, help='Load saved game') 
	parser.add_argument('--ip', type=str, help='your ip address or hostname, where clients can connect to the server') 
	parser.add_argument('--nameserver', type=str, help='hostname or ip address, where a pyro naming server can be found or should be started (if the address belongs to this computer)')
	args = parser.parse_args()

	if not single_argument_load():
		multiple_argument_load(args)
		#both throws an exception if files can not be found
	artemis_connector.start_server()
	#json_connector.test()	
	if PYRO: 
		print(80*'-')
		pyro_connector.start_pyro_server(ip=args.ip, host=args.nameserver)
		print(80*'-')
		print("You may start the admiral or game-master client on this or some other machine in your network.")
	else:
		print("Warning: Pyro connector could not be loaded.")

	print("Ready to play!")
