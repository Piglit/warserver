#!/usr/bin/python3
"""This is the ArtOffWar game module.
Here the map and the game state is represented.
Other modules communicate with this module to read and to write the game state.
"""

import time
import threading
import random
import copy
from collections import Counter

__author__ 	= "Pithlit"
__version__	= 0.0



class Game:
	"""
	A class for WarServer driven games.
	An object of this class represents the game state.
	This implementation reassembles the original Artemis WarServer.
	There are some fixed activaded per default. Deactivate them via settings.
	There are some options, you can activate vio settings.
	"""

	def __init__(self, settings):
		self.settings = {
			"Game Difficulty Level":	7,	#may also be a fuction with two parameters (coordinates). e.g. lambda x,y:random.randint(5,10)
			"Invaders Per Turn":		20,
			"Invasion Beachheads":		1,
			"Empty Sectors":			7,	#This is more exactly than in the original WarServer.
			"Total Turns":				5,
			"Minutes per Turn":			5,
			"Minutes between Turns (interlude)":	1,
			"Bugfix: Beachheads off by one":	True,	#Probably a bug in the original WarServer.
			"Randomize Beachheads":		False,
			"Neighbour Invading Function":	lambda x,y: [(x,y),(x+1,y),(x-1,y),(x,y+1)],	#in the original WarServer enemies never go to the north.
			"Hidden Sectors cant be Neighbours":	False,	#set to True to calculate enemies distribution from non hidden sectors only. False behaves like the original WarServer.
			"Non Reentrant Sectors":	False,	#if True only one client can enter each sector.
			"Clients have own Maps":	False,
		}
		self.settings.update(settings)

		assert(self.settings["Invasion Beachheads"] <= 8)
		assert(self.settings["Invasion Beachheads"] >= 0)
		if self.settings["Bugfix: Beachheads off by one"]:
			self.beachhead_columns = [3,4,2,5,1,6,0,7]
		else:
			self.beachhead_columns = [4,5,3,6,2,7,1,0]
		if self.settings["Randomize Beachheads"]:
			random.shuffle(self.beachhead_columns)
		self.beachhead_columns = self.beachhead_columns[0:self.settings["Invasion Beachheads"]]
			
		self.map = []
		for col in range(0,8):
			self.map.append([])
			for row in range(0,8):
				diff = self.settings["Game Difficulty Level"]
				if callable(diff):
					diff = diff(col,row)
				sector = {
					"Enemies":			random.randrange(2), #0,
					"Rear_Bases":		random.randrange(4),	#0 to 3
					"Forward_Bases":	random.randrange(2),	#0 to 1
					"Fire_Bases":		0,
					"?":				18,
					"Seed":				random.randrange(16**4),
					"Difficulty":		diff,	
					"??":				4,
					"Hidden":			False,
					"Name":				"Sektor",
					"pending_invaders":	0
				}
				self.map[col].append(sector)
			assert len(self.map[col]) == 8
		assert len(self.map) == 8

		hidden_sector_columns = Counter()
		for i in range(self.settings["Empty Sectors"]):
			hidden_sector_columns[random.randrange(8)] += 1
		for col, num in hidden_sector_columns.most_common():
			for sector in random.sample(self.map[col][1:],min(num,len(self.map[col]))):
				sector["Hidden"] = True

		self.turn = {
			"turn_number":	1,
			"max_turns":	self.settings["Total Turns"],
			"interlude":	False,
			"turn_started":	time.time()
		}
		self.ships = dict()
		self.base_points = 0
		self.scoreboard_kills = Counter()
		self.scoreboard_clears= Counter()
		self.lock = threading.RLock()
		self.notifications = []
		self.timer_thread = threading.Timer(self.settings["Minutes per Turn"]*60, self._next_turn)
		for i in range(6):
			self._enemies_proceed(self.map)
		self.timer_thread.start()
		print("Game Engine started")

	def get_map(self,client=None):
		"""
		Returns the whole map.
		It is used to show the map to Artemis clients or to manage an admiral or GM Screen.
		With client=None the whole map is returned, so the caller decides what information is used.
		If client is a tuple: (ip_address, port) or a string like "admirals_map", 
		this method may decide to restrict information, depending on who is requesting the map.
		"""
		with self.lock:
			return self.map 
			#warning: the caller may change the map. You may prevent this by returning a copy of the map. See deepcopy()

	def get_turn_status(self, client=None):
		"Returns the turn dict with the seconds remaining as float"
		with self.lock:
			turn = self.turn
			remaining = turn["turn_started"] - time.time()
			if turn["interlude"]:
				remaining += self.settings["Minutes between Turns (interlude)"] * 60
			else:
				remaining += self.settings["Minutes per Turn"] * 60
			turn["remaining"] = remaining	#updated only when this is called!
			return turn

	def get_ships(self, client=None):
		with self.lock:
			return self.ships


	def enter_sector(self,x,y,shipname,client):
		"""
		This is called when an Artemis client enters a sector.
		Returns the sector as dict.
		The implementation may decide to send other data then shown on the map.
		You may also alter the shipname here to avoid collisions.
		You can return None, to forbid that client enters that setor now.
		"""
		with self.lock:
			if client in self.ships:
				self.ships[client] = (shipname,-1,-1,0,0)	#invalidate, since client is not in a sector right now
			if self.settings["Non Reentrant Sectors"]:
				for key in self.ships:
					if self.ships[key][1] == x and self.ships[key][2] == y:
						return None	#Sector Forbidden 
			sector = copy.deepcopy(self.map[x][y])
			sector.update({
				"Enemies":	5,
				"Rear_Bases":	3,
				"Forward_Bases":	2,
				"Fire_Bases":	1,
				"Allies?":	4,
				"Seed":		0x1234,
				"ID":		0x5678,
				"Difficulty":	9,
				"Map_specific?":	8,
				"Ship-Name":	"Tessel",
			})
			if sector.get("Ship-Name") is not None:
				shipname = sector["Ship-Name"]
			#TODO check what stuff is. compare to map dict
			self.ships[client] = (shipname,x,y,sector["ID"],sector["Enemies"])
			self._map_changed()
			return sector

	def clear_sector(self,shipname,id,client):
		"""
		This is called after an Artemis client sends an leave sector packet.
		The client has defeated all enemies in that sector.
		"""
		with self.lock:
			assert client in self.ships
			battle = self.ships[client]
			self.scoreboard_kills[shipname] += battle[4]
			self.ships[client] = (shipname,-1,-1,0,0)
			if self.map[battle[1]][battle[2]]["Enemies"] > 0:
				self.base_points += 1
				self.scoreboard_clears[shipname] += 1
			self.map[battle[1]][battle[2]]["Enemies"] = 0
			self._map_changed()

	def kills_in_sector(self,shipname,id,kills,client):
		"""
		This is called after an Artemis client killed one or more enemies.
		The client still resides in that sector.
		"""
		with self.lock:
			assert client in self.ships
			battle = self.ships[client]
			assert battle[0] == shipname
			assert battle[3] == id
			self.ships[client] = (battle[0], battle[1], battle[2], battle[3], battle[4]-kills)
			self.scoreboard_kills[shipname] += kills

	def disconnect_client(self, client):
		"""When a client disconects, free the sector"""
		with self.lock:
			if client in self.ships:
				self.ships[client] = (shipname,-1,-1,0,0)

	def register_notification(self,event):
		"""
		The caller mat provide an event to the engine, which is set when the map changes.
		The caller must clear his event himself.
		"""
		self.notifications.append(event)

	def _map_changed(self):
		"""Called to notify other modules that the map has changed"""
		for e in self.notifications:
			e.set()

	def _next_turn(self):
		"""proceeds to the next turn"""
		with self.lock:
			self.timer_thread.cancel()	#ignored if this is executed by the timer_thread itself
			self.turn["turn_started"] = time.time()
			if self.turn["interlude"]:
				self.turn["interlude"] = False 
				self.timer_thread = threading.Timer(self.settings["Minutes per Turn"]*60, self._next_turn)
			else:
				self._defeat_bases(self.map)
				self._enemies_proceed(self.map)
				for client in self.ships:
					self.ships[client] = (self.ships[client][0],-1,-1,0,0)	#clear all the shipnames
				self.turn["turn_number"] += 1
				self.turn["interlude"] = True
				self.timer_thread = threading.Timer(self.settings["Minutes between Turns (interlude)"]*60, self._next_turn)
			self.timer_thread.start()
			self._map_changed()	#awakens notify thread. Turn over is sent.

	def _defeat_bases(self,map):
		"""
		Destroys all bases in sectors where enemies are.
		The map given as argument is modified in-place.
		You may call this method with a copy of the games map,
		so you can see what happens without modifying the actual map.
		"""
		with self.lock:
			for column in map:
				for sector in column:
					if sector["Enemies"] > 0:
						sector["Rear_Bases"] = 0
						sector["Forward_Bases"] = 0
						sector["Fire_Bases"] = 0

	def _enemies_proceed(self,map):
		"""
		Enemies enter the map and move around.
		The map given as argument is modified in-place.
		You may call this method with a copy of the games map,
		so you can see what happens without modifying the actual map.
		"""
		with self.lock:
			for col in range(8):
				for row in range(8):
					sector = map[col][row]
					neighbours = self.settings["Neighbour Invading Function"](col,row)
					enemies = sector["Enemies"] // len(neighbours)
					for t in copy.copy(neighbours):
						x,y = t
						if x < 0 or x > 7 or y < 0 or y > 7:
							neighbours.remove(t)
						elif map[x][y]["Hidden"]:
							neighbours.remove(t)
					if self.settings["Hidden Sectors cant be Neighbours"]:
						enemies = sector["Enemies"] // len(neighbours)
					for t in neighbours:
						x,y = t
						map[x][y]["pending_invaders"] += enemies
						sector["Enemies"] -= enemies
			for col in range(8):
				for row in range(8):
					map[col][row]["Enemies"] += map[col][row]["pending_invaders"]
					map[col][row]["pending_invaders"] = 0
		

class DefaultGame(Game):
	def get_map(who):
		pass

	def get_sector(x,y,who):
		#dummy sector
		sector = {
			"Enemies":	5,
			"Bases 1":	3,
			"Bases 2":	2,
			"Bases 3":	1,
			"Allies?":	4,
			"Seed":		0x1234,
			"ID":		0x5678,
			"Difficulty":	9,
			"Map_specific?":	8,
			"Ship-Name":	"Tessel",
		}
		return sector

game=Game({})
