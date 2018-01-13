#!/usr/bin/python3
import configparser
import argparse
import pickle

import engine
import artemis_connector
import pyro_connector



if __name__ == "__main__":
	config = configparser.ConfigParser()
	parser = argparse.ArgumentParser(description='Starts the Artemis WarServer.') 
	parser.add_argument('--config', '-c', type=open, default='default.cfg', help='Load config file') 
	parser.add_argument('--load', '-l', type=argparse.FileType("rb"), help='Load saved game') 
	parser.add_argument('--ip', type=str, help='your ip address or hostname, where clients can connect to the server') 
	parser.add_argument('--nameserver', type=str, help='hostname or ip address, where a pyro naming server can be found or should be started (if the address belongs to this computer)')
	args = parser.parse_args()
	#if throws an exception if files can not be found

	config.read_file(args.config)
	settings = {}
	for key in config["int"]:
		settings[key] = config["int"].getint(key)
	for key in config["float"]:
		settings[key] = config["float"].getfloat(key)
	for key in config["bool"]:
		settings[key] = config["bool"].getboolean(key)

	if args.load:
		engine.game=pickle.load(args.load)
		engine.game._start_from_loaded_game()
	else:
		print("This is the python Artemis warserver.")
		print("Configuration loaded from file "+str(args.config.name))
		engine.game=engine.Game(settings)	
		#engine.start_game=(config['original'])	
	artemis_connector.start_server()
	#json_connector.test()	
	print(80*'-')
	pyro_connector.start_pyro_server(ip=args.ip, host=args.nameserver)
	print(80*'-')
	print("You may start the admiral or game-master client on this or some other machine in your network.")



