#!/usr/bin/python3

"""This is the Artemis Connector module.
It manages all the network connections to and from Artemis Game Servers (Clients).
An Artemis Game Server can connect to this program with "Join Galactical War Server".
This module consists of the udp socket server, request handlers and worker threads.

There are three instances for the communication with the artemis client:
1 Response-thread: When a client sends a request, the response thread handles and answeres to it.
1 Notify-thread: When the game state changes (and every 5 seconds),
	the notify thread sends the updates to all clients.
n Heartbeat-threads: each one sends a heartbeat package to his client every 0.5 seconds.
"""

#FIXME Bug: client connects and disconnects. Reconnect may fail!

import copy
import socketserver
import threading
import struct
import time
from warnings import warn

import engine

__author__ = "Pithlit"
__version__	= 1.1

#This code is executed the first time this module is imported.
HOST, PORT = "", 3000	#Listen on all available interfaces on port 3000
SERVER_START_TIME = time.time()

PACKAGE_TYPES = {
				0x82ff:	"Client-hello",
				0x83ff:	"Server-hello",
				0x84ff:	"Client-bye",
				0x85ff:	"Heartbeat",
				0x8aff:	"?+Heartbeat",
				0x44ff:	"Error",
				0x01ff:	"Heartbeat-Ack",
				0x8600:	"Sector",
				0x0700:	"Data",
				0x0100:	"Sector-Ack",
}

PACKAGE_TYPES_ENCODE = dict()
for key in PACKAGE_TYPES:
	PACKAGE_TYPES_ENCODE[PACKAGE_TYPES[key]] = key

PACKAGE_SUBTYPES = {
				0x0400:	"Sector-Enter",
				0x0800:	"Sector-Leave",
				0x0c00:	"Sector-Kill",
				0x0500:	"Data-Map",
				0x0600:	"Data-Sector",
				0x0700:	"Data-Ships",
				0x0900:	"Data-Turn",
				0x0b00:	"Data-Turn-Over",
				0x0d00:	"Data-Ship-Name",
}
PACKAGE_SUBTYPES_ENCODE = dict()
for key in PACKAGE_SUBTYPES:
	PACKAGE_SUBTYPES_ENCODE[PACKAGE_SUBTYPES[key]] = key

CONNECTIONS = dict()
CONNECTIONS_LOCK = threading.RLock()
MAP_CHANGED_EVENT = threading.Event()


def heartbeat(ip, port):
	"""
	This function is executed by each heartbeat-thread.
	It sends a heartbeat package evert 0.5 seconds.
	"""
	client = (ip, port)
	heartbeat_number = 0
	with CONNECTIONS_LOCK:
		con = CONNECTIONS.get(client)	#reference
		socket = con["socket"]			#reference
		connection_number = con["connection_number"]	#copy
		terminate = con["terminate"]	#reference
	while not terminate.wait(timeout=0.5):	#sleeps for 0.5 sec before returning False.
		heartbeat_number = (heartbeat_number + 1) % 16**4
		socket.sendto(compose_heartbeat(connection_number, heartbeat_number), client)
	socket.close()

def notify():
	"""
	This function is executed by the notify thread.
	It sends the map to all connected clients every 6 seconds or when flag is set
	"""
	is_interlude = False #used to send turn over package
	while True:
		MAP_CHANGED_EVENT.wait(timeout=6)
		MAP_CHANGED_EVENT.clear()
		#get whole map once
		game_map = engine.game.get_map(client=("All-Artemis-Clients"))
		assert len(game_map) == 8
		orig_map_col = []
		for i in range(8):
			orig_map_col.append(compose_map_col(i, game_map[i]))
		unfinished_packages = []
		turn_status = engine.game.get_turn_status(client=("All-Artemis-Clients"))
		if turn_status["interlude"] != is_interlude:
			#send turn over package
			is_interlude = not is_interlude
			unfinished_packages.append(compose_turn_over())
		unfinished_packages.append(compose_turn_status(turn_status))
		unfinished_packages.append(compose_ships(engine.game.get_ships(client=("All-Artemis-Clients"))))

		with CONNECTIONS_LOCK:
			for client in CONNECTIONS:
				socket = CONNECTIONS[client]["socket"]
				updates = engine.game.get_modified_map(client)
				updated_cols = {}
				for package in unfinished_packages:
					try:
						socket.sendto(compose_data(client, package), client)
					except Exception as exception:
						print(exception)
				for x, y, k, v in sorted(updates):
					if x not in updated_cols:
						updated_cols[x] = copy.deepcopy(game_map[x])
					if isinstance(v, (int, float)):
						updated_cols[x][y][k] += v
					else:
						updated_cols[x][y][k] = v

				for i in range(8):
					try:
						if i in updated_cols:
							socket.sendto(compose_data(client, compose_map_col(i, updated_cols[i])), client)
						else:
							socket.sendto(compose_data(client, orig_map_col[i]), client)
					except Exception as exception:
						print(exception)



def register_connection(client, socket, connection_number):
	"""A Client just connected to the server.
	Now we start a thread to please him.
	The thread and the information it communicates with us are stored
	in the global CONNECTIONS dict.
	Each client-port combination may only be connected onec at the same time.
	"""
	connection = dict()
	with CONNECTIONS_LOCK:
		if client in CONNECTIONS:
			connection = CONNECTIONS[client]
		else:
			CONNECTIONS[client] = connection

	if connection_number is None:
		connection_number = 0
	else:
		#FIXME experimental, not tested yet
		connection_number += 1
	connection["connection_number"] = connection_number
	connection["data_number"] = 1
	connection["last_sector_numbers"] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
	connection["terminate"] = threading.Event()
	connection["socket"] = socket.dup()
	thread = threading.Thread(target=heartbeat, args=(client))
	connection["thread"] = thread
	return connection_number, thread

def unregister_connection(client):
	"""A Client disconedted from the server"""
	with CONNECTIONS_LOCK:
		if client in CONNECTIONS:
			con = CONNECTIONS.pop(client)
		else:
			return
	con["terminate"].set()

def check_sector_replay(client, sector_number):
	"""Checks the package counter.
		Returns False, if the package already arrived, but ack was lost.
		Such packages must be ignored.
	"""
	with CONNECTIONS_LOCK:
		if CONNECTIONS[client]["last_sector_numbers"][sector_number%10] < sector_number:
			CONNECTIONS[client]["last_sector_numbers"][sector_number%10] = sector_number
			return True
		elif (sector_number < 10 and
			  CONNECTIONS[client]["last_sector_numbers"][sector_number%10] > 0xffff-10):
			CONNECTIONS[client]["last_sector_numbers"][sector_number%10] = sector_number
			return True
		else:
			return False

class ArtemisUDPHandler(socketserver.DatagramRequestHandler):
	"""
	The RequestHandler class for our server.
	It is instantiated once per connection to the server, and must
	override the handle() method to implement communication to the client.
	"""

	def handle(self):
		"""
		self.request consists of a pair of data and client socket, and since
		there is no connection the client address must be given explicitly
		when sending data back via sendto().
		"""
		data = self.request[0]
		socket = self.request[1]
		client = self.client_address
		for package in dissect(data):
			if package["type"] == "Client-hello":
				number, thread = register_connection(client, socket, package.get("connection_number"))
				socket.sendto(compose_hello(number, package), client)
				thread.start()
				MAP_CHANGED_EVENT.set()
			if package["type"] == "Error":
				unregister_connection(client)
			elif client in CONNECTIONS:	#no lock
				if package["type"] == "Client-bye":
					socket.sendto(ack("Heartbeat-Ack", package), client)
					unregister_connection(client)
				elif package["type"] == "Heartbeat" or package["type"] == "?+Heartbeat":
					#answer with ack
					socket.sendto(ack("Heartbeat-Ack", package), client)
				elif package["type"] == "Heartbeat-Ack":
					pass
				elif package["type"] == "Sector":
					socket.sendto(ack("Sector-Ack", package), client)
					if package["subtype"] == "Sector-Enter":
						sector = engine.game.enter_sector(package["X"], package["Y"], package["Ship-Name"], client)
						if sector is not None:
							if "Ship-Name" in sector and sector["Ship-Name"] != package["Ship-Name"]:
								socket.sendto(compose_data(client, compose_shipname(sector["Ship-Name"])), client)
								package["Ship-Name"] = sector["Ship-Name"]
							socket.sendto(compose_data(client, compose_map_sector(sector)), client)
					elif package["subtype"] == "Sector-Leave":
						engine.game.clear_sector(package["Ship-Name"], package["ID"], client)
					elif package["subtype"] == "Sector-Kill":
						if check_sector_replay(client, package["Number"]):
							engine.game.kills_in_sector(package["Ship-Name"], package["ID"], package["Kills"], client)
			else:
				warn("client not in CONNECTIONS list. Waiting for client to reconnect.")


#Here follows package assambley

def ack(subtype, orig_package):
	"""creates an ack package to ack heartbeats or sectors"""
	package_type = PACKAGE_TYPES_ENCODE[subtype]
	assert PACKAGE_TYPES[package_type] == subtype
	flags = orig_package["flags_connection_number"]	#no time
	number = orig_package["Number"]
	package_time = orig_package["preamble_time"]
	package = struct.pack(">HHHHH", flags, package_type,
						  number, number, package_time)	#yes, number two times
	return package

def compose_preamble(connection_number: int, local_time: bool,
					 package_type: str, package_number) -> bytes:
	"""Every package starts with this preamble"""
	connection_number = connection_number % 8
	flags = (connection_number << 12)
	package_type = PACKAGE_TYPES_ENCODE[package_type]
	if local_time:
		flags |= 0x8000
		local_time = int((time.time()-SERVER_START_TIME) * 1000)%0x10000
		return struct.pack(">HHHH", flags, local_time, package_type, package_number)
	else:
		return struct.pack(">HHHH", flags, package_type, 0, package_number)

def compose_heartbeat(con_number, pack_number):
	"""called by heartbeat threads"""
	return compose_preamble(con_number, True, "Heartbeat", pack_number)

def compose_hello(number, orig_package):
	"""called when a client connects to the server"""
	preamble = compose_preamble(number, True, "Server-hello", 1)
	number = number % 8
	number = number | number << 4
	payload = struct.pack('>'+('H'*20), 0x0000, number, 0x0000, *orig_package["payload-1-echo"],
						  0, 0, 0, 0, *orig_package["payload-3-echo"])
	return preamble + payload

def compose_data(client, payload):
	"""create a data package"""
	with CONNECTIONS_LOCK:
		con = CONNECTIONS[client]
		con_number = con["connection_number"]
		data_number = con["data_number"]
		con["data_number"] += 1
	preamble = compose_preamble(con_number, False, "Data", data_number)
	return preamble + struct.pack(">H", len(payload)) + payload

def compose_map_col(index, column_data):
	"""creates a package that contains information of one column of the map"""
	subtype = PACKAGE_SUBTYPES_ENCODE["Data-Map"]
	sectors = struct.pack(">Hb", subtype, index)
	for sector_data in column_data:
		sector = struct.pack("<bbbHbbH", sector_data["Rear_Bases"],
							 sector_data["Forward_Bases"], sector_data["Fire_Bases"],
							 sector_data["Enemies"], sector_data["Hidden"] or sector_data["fog"],
							 sector_data["Terrain"], len(sector_data["Name"])) + bytes(sector_data["Name"], "utf-8")
		sectors += sector
	return sectors

def compose_map_sector(sector_data):
	"""creates a sector for a client to play"""
	subtype = struct.pack(">H", PACKAGE_SUBTYPES_ENCODE["Data-Sector"])
	return subtype + struct.pack("<HbbbbHxxHxxbxxxb", sector_data["Enemies"],
								 sector_data["Rear_Bases"], sector_data["Forward_Bases"],
								 sector_data["Fire_Bases"], sector_data["??"],
								 sector_data["Seed"], sector_data["ID"],
								 sector_data["Difficulty"], sector_data["Terrain"])

def compose_ships(ships: dict):
	"""creates a list of ship descriptions"""
	#ship: (shipname, x, y, sector["ID"], sector["Enemies"])
	package = struct.pack(">H", PACKAGE_SUBTYPES_ENCODE["Data-Ships"])
	for s in ships:
		ship = ships[s]
		package += struct.pack("<bbbH", 1, ship[1], ship[2], len(ship[0]))
		package += bytes(ship[0], "utf-8")
	package += struct.pack(">b", 0)
	return package

def compose_turn_status(turn):
	"""creates the turn status package"""
	subtype = struct.pack(">H", PACKAGE_SUBTYPES_ENCODE["Data-Turn"])
	return subtype + struct.pack("<iiii", int(turn["remaining"]), turn["turn_number"],
								 turn["max_turns"], int(turn["interlude"]))

def compose_turn_over():
	"""creates a turn over package that stops the simulation for the client"""
	return struct.pack(">H", PACKAGE_SUBTYPES_ENCODE["Data-Turn-Over"])

def compose_shipname(name):
	"""creates a package that changes the shps name"""
	subtype = PACKAGE_SUBTYPES_ENCODE["Data-Ship-Name"]
	return struct.pack(">H", subtype) + struct.pack("<H", len(name)) + bytes(name, "utf-8")


#Here follows package dissassembly

def dissect(data):
	"""
	Dissects an Artemis package.
	Returns a list of dicts, containing meaningful information of that package.
	Raises an exception if a packet could not be dissected.
	"""
	#We do no error checking here, since we use exceptions
	preamble = dict()
	flags = int.from_bytes(data[0:2], byteorder="big")
	preamble["flags"] = flags
	preamble["flags_time"] = flags_time = flags & 0x8000
	preamble["flags_connection_number"] = flags & 0x7000
	preamble["flags_unknown"] = flags & 0xfff
	if flags_time != 0:
		preamble["preamble_time"] = int.from_bytes(data[2:4], byteorder="big")
		data = data[4:]
	else:
		data = data[2:]
	retlist = []
	#from now on data begins here
	while data:	# while len(data) > 0
		package = dict()
		subtype = PACKAGE_TYPES[int.from_bytes(data[:2], byteorder="big")]	#raises KeyError
		package["type"] = subtype
		if subtype == "Data":
			if int.from_bytes(data[2:4]) != 0:
				raise ValueError
			package["Number"] = int.from_bytes(data[4:6], byteorder="big")
			data = data[6:]
		else:
			package["Number"] = int.from_bytes(data[2:4], byteorder="big")
			data = data[4:]

		#from now on data begins here
		if subtype == "Client-hello":

#			package["payload"] = list(map(lambda t: t[0], struct.iter_unpack("<H", data)))
#			print(package["payload"])

			if int.from_bytes(data[0:2], byteorder="big") != 0:
				raise ValueError
			if int.from_bytes(data[2:4], byteorder="big") != 0xFFFF:
				package["connection_number"] = int.from_bytes(data[2:4], byteorder="big")
			if int.from_bytes(data[4:6], byteorder="big") != 0:
				raise ValueError

			package["payload-1-echo"] = list(map(lambda t: t[0], struct.iter_unpack(">H", data[6:18])))
			package["payload-2"] = list(map(lambda t: t[0], struct.iter_unpack(">H", data[18:26])))
			package["payload-3-echo"] = list(map(lambda t: t[0], struct.iter_unpack(">H", data[26:40])))
			if int.from_bytes(data[40:], byteorder="big") != 0:
				raise ValueError
			#Dont know what all this means yet.
			data = []
		elif subtype == "Client-bye":
			if int.from_bytes(data[0:], byteorder="big") != 0:
				raise ValueError
			data = []
		elif subtype == "Error":
			if int.from_bytes(data[0:], byteorder="big") != 0:
				raise ValueError
			data = []
		elif subtype == "Heartbeat":
			pass
		elif subtype == "?+Heartbeat":
			package["payload-as-uint16-list"] = list(struct.unpack(">HHHH", data[0:8]))
			data = data[8:]
		elif subtype == "Heartbeat-Ack":
			if int.from_bytes(data[0:2], byteorder="big") != package["Number"]:
				raise ValueError
			package["acked-time"] = int.from_bytes(data[2:4], byteorder="big")
			data = data[4:]
		elif subtype == "Sector":
			#length = int.from_bytes(data[0:2], byteorder="big")
			subsubtype = PACKAGE_SUBTYPES[int.from_bytes(data[2:4], byteorder="big")]	#raises KeyError
			package["subtype"] = subsubtype
			data = data[4:]
			if subsubtype == "Sector-Enter":
				package["X"] = int(data[0])
				package["Y"] = int(data[1])
				data = data[2:]
			elif subsubtype == "Sector-Leave":
				package["ID"] = int.from_bytes(data[0:2], byteorder="little")
				if int.from_bytes(data[2:4], byteorder="big") != 0:
					raise ValueError
				data = data[4:]
			elif subsubtype == "Sector-Kill":
				package["ID"] = int.from_bytes(data[0:2], byteorder="little")
				if int.from_bytes(data[2:4], byteorder="big") != 0:
					raise ValueError
				package["Kills"] = int.from_bytes(data[4:8], byteorder="little")
				data = data[8:]
			else:
				warn("WTF?")
			strlen = int.from_bytes(data[0:2], byteorder="big")
			package["Ship-Name"] = data[2:strlen+2].decode(encoding="utf-8")
			data = data[strlen+2:]
		package.update(preamble)
		retlist.append(package)
	return retlist


SERVER = socketserver.UDPServer((HOST, PORT), ArtemisUDPHandler)	#Blocking.
#There is also ThreadingUDPServer that creates a new thread for each Request


def start_server():
	"""initializes and start this module"""
	engine.game.register_notification(MAP_CHANGED_EVENT)
	threading.Thread(target=notify).start()
	threading.Thread(target=SERVER.serve_forever).start()
	print("Server is listening for Artemis clients.")
	print("Choose 'Join War Server' in the Artemis server menu.")
