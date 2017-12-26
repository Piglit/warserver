#!/usr/bin/python3
import configparser
import argparse

import engine

import artemis_connector
import pyro_connector
import json_connector

if __name__ == "__main__":
	config = configparser.ConfigParser()
	parser = argparse.ArgumentParser(description='Starts the Artemis WarServer.') 
	parser.add_argument('--config', '-c', type=open, default='default.cfg', help='Load config file') 
	args = parser.parse_args()
	#if throws an exception if files can not be found

	config.read_file(args.config)

	print("This is the headless python Artemis warserver.")
	print("Configuration loaded from file "+str(args.config.name))
	engine.game=engine.Game(config['server'])	
	#engine.start_game=(config['original'])	
	artemis_connector.start_server()
	json_connector.test()	
	#pyro_connector.start_pyro_server()
#now start all the staff that needs an game object.




