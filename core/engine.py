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
import Pyro4
import pickle
import os

__author__ 	= "Pithlit"
__version__	= 0.1

#not used now, but these strings are diplayed in Artemis when you transmit the corresponding numbers
terrain_types = {
	"Sector":					0,		
	"Nebula":			   		1,	
	"Minefield":				2,	
	"Asteroid Belt":			3,	
	"Black Hole Nursery":   	4,	
	"Wildlands":				5,	
	"Crossroads":		   		6,	
}


class Game:
	"""
	A class for WarServer driven games.
	An object of this class represents the game state.
	This implementation reassembles the original Artemis WarServer.
	There are some fixed activaded per default. Deactivate them via settings.
	There are some options, you can activate via settings.
	"""

	def __init__(self, settings):
		self.settings = {
			"game difficulty level":	7,
			"invaders per turn":		20,
			"invasion beachheads":		1,
			"empty sectors":			7,	#This is more exactly than in the original WarServer.
			"total turns":				5,
			"minutes per turn":			5,	#accepts float
			"minutes between turns (interlude)":	1,	#accepts float
			"bugfix beachheads off by one":	True,	#Probably a bug in the original WarServer.
			"randomize beachheads":		False,
			"enemies can go north":		False,#in the original WarServer enemies never go to the north.
			"hidden sectors cant be neighbours":	False,	#set to True to calculate enemies distribution from non hidden sectors only. False behaves like the original WarServer.
			"non reentrant sectors":	False,	#if True only one client can enter each sector.
			"fog of war":				False,
			"last_update":				0.0,	#used internally to push changes to custom clients
		}
		self.settings.update(settings)

		assert(self.settings["invasion beachheads"] <= 8)
		assert(self.settings["invasion beachheads"] >= 0)
		if self.settings["bugfix beachheads off by one"]:
			beachhead_columns = [3,4,2,5,1,6,0,7]
		else:
			beachhead_columns = [4,5,3,6,2,7,1,0]
		if self.settings["randomize beachheads"]:
			random.shuffle(beachhead_columns)
		beachhead_columns = beachhead_columns[0:self.settings["invasion beachheads"]]
	
		self.beachheads = []
		for bc in beachhead_columns:
			self.beachheads.append((bc,0))
			#default beachheads generated by config file are always on the first row
			#Game Master can rearrange them or place them on any sector of the map
		del self.settings["invasion beachheads"]
		del self.settings["randomize beachheads"]
		del self.settings["bugfix beachheads off by one"]
		#these were settings that only matter on startup
		#deleting them removes confusing the gm, when she reads the settings
	
		self.map = []
		for col in range(0,8):
			self.map.append([])
			for row in range(0,8):
				sector = {
					"x":				col,
					"y":				row,
					"Enemies":			0,
					"Rear_Bases":		random.randrange(4),	#0 to 3
					"Forward_Bases":	random.randrange(2),	#0 to 1
					"Fire_Bases":		0,
					"Terrain":			random.randrange(7),	
					"Seed":				random.randrange(16**4),
					"Difficulty_mod":	0,	# self.settings["Game Difficulty Level"] is added to determine the difficulty level. GM may change this value for each sector
					"??":				0,	#TODO
					"Hidden":			False,
					"Name":				"Sector",
					"Beachhead":		(col,row) in self.beachheads,
					"pending_invaders":	0,	#should be only visible to GM
					"blocked":			False, #only visible to GM. prevents entering the sector
					"fog":				True, #if true, this sector must be discovered first, before it can be seen
					"always_enterable":	False, #if true, you can always enter the sector, regardless of enemies or neighbouring sectors or ships inside. However Hidden and blocked still prevent entering.
					"last_update":		0.0,
				}
				self.map[col].append(sector)
			assert len(self.map[col]) == 8
		assert len(self.map) == 8
		self.last_map_change = 0.0

		hidden_sector_columns = Counter()
		for i in range(self.settings["empty sectors"]):
			hidden_sector_columns[random.randrange(8)] += 1
		for col, num in hidden_sector_columns.most_common():
			for sector in random.sample(self.map[col][1:],min(num,len(self.map[col]))):
				sector["Hidden"] = True
		del self.settings["empty sectors"]	#irrelevant from now on

		self.turn = {
			"turn_number":	1,
			"max_turns":	self.settings["total turns"],
			"interlude":	False,
			"turn_started":	time.time(),
			"last_update":	time.time(),
			"remaining":	self.settings["minutes per turn"]*60,
			"time_passed":	0.0,
		}
		del self.settings["total turns"]	#irrelevant from now on

		self.ships = dict()
		self.base_points = 0
		self.scoreboard_kills = Counter()
		self.scoreboard_clears= Counter()
		self.scoreboard_last_update= 0.0

		self.various_last_update = 0.0

		self.events_get_map = {}
		self.events_enter_sector = {}

		self._lock = threading.RLock()
		self._notifications = []
		self._timer_thread = threading.Timer(self.settings["minutes per turn"]*60, self._next_turn)
		self.end_of_last_turn = time.time()
		for i in range(6):
			self._defeat_bases(self.map)
			self._enemies_proceed(self.map)
			self._enemies_spawn(self.map)
		self.reset_fog()
		self._timer_thread.start()
		print("Game Engine started")
	# getter methods

	def get_map(self,client=None):
		"""
		Returns the whole map.
		It is used to show the map to Artemis clients or to manage an admiral or GM Screen.
		With client=None the whole map is returned, so the caller decides what information is used.
		If client is a tuple: (ip_address, port) or a shipname string or a one-tuple like ("Admiral") or ("GM"), 
		this method may decide to restrict information, depending on who is requesting the map.
		"""
		with self._lock:
			map = copy.deepcopy(self.map)
			changes = []
			if ("ALL") in self.events_get_map:
				changes += self.events_get_map(("ALL"))
			if client in self.events_get_map:
				changes += self.events_get_map(client)
			for x,y,k,v in changes:
				if type(v) == int or type(v) == float:
					map[x][y][k] += v
				else: 
					map[x][y][k] = v
			if self.settings["fog of war"]:
				for x in range(0,8):
					for y in range(0,8):
						map[x][y]["Hidden"] = map[x][y]["Hidden"] or map[x][y]["fog"]
			return map


	def get_modified_map(self,client=None):
		"""
		Returns parts of the map, that update the whole map returned be get_map.
		This implementation increases performance for broadcasting maps to Artemis, if there are few individual changes.
		Returns a list of tuples: x,y,key,value
		"""
		with self._lock:
			changes = self.events_get_map.get(client)
			if changes == None:
				changes = self.events_get_map.get(client[0])
			if changes == None:
				name = self.ships.get(client)
				if name is not None:
					changes = self.events_get_map.get(name[0])
			if changes == None:
				changes = []	
			return changes

	def get_sector(self,x,y,client=None):
		with self._lock:
			sector = copy.deepcopy(self.map[x][y])
			changes = []
			if ("ALL") in self.events_get_map:
				changes += self.events_get_map(("ALL"))
			if client in self.events_get_map:
				changes += self.events_get_map(client)
			for _x,_y,k,v in changes:
				if _x == x and _y == y:
					if type(v) == int or type(v) == float:
						sector[k] += v
					else: 
						sector[y][k] = v
			if self.settings["fog of war"]:
				sector["Hidden"] = sector["Hidden"] or sector["fog"]
			return sector


	def get_turn_status(self, client=None):
		"Returns the turn dict with the seconds remaining as float"
		with self._lock:
			turn = self.turn
			t = time.time()
			turn["time_passed"] = t - turn["turn_started"]
			remaining = turn["turn_started"] - t
			if turn["interlude"]:
				remaining += self.settings["minutes between turns (interlude)"] * 60
			else:
				remaining += self.settings["minutes per turn"] * 60
			turn["remaining"] = remaining	#updated only when this is called!
			return turn

	def get_ships(self, client=None):
		with self._lock:
			return self.ships

	def get_base_points(self, client=None):
		with self._lock:
			return self.base_points

	def get_scoreboard(self, client=None):
		with self._lock:
			return (self.scoreboard_clears, self.scoreboard_kills)

	def get_settings(self, client=None):
		with self._lock:
			return self.settings

	def get_beachheads(self, client=None):
		with self._lock:
			return self.beachheads

	def get_events_get_map(self, client=None):
		with self._lock:
			return self.events_get_map

	def get_events_enter_sector(self, client=None):
		with self._lock:
			return self.events_enter_sector

	#setter methods

	def update_sector(self, x, y, key, value):
		"""sets one value of a sector. Used for GM or Admiral."""
		with self._lock:
			assert type(self.map[x][y][key]) == type(value) , "value has the wrong type"
			self.map[x][y][key] = value
			self.map[x][y]["last_update"] = time.time()
			self._map_changed()

	def change_sector(self, x, y, key, diff):
		"""
		changes one value of a sector. Used for GM or Admiral.
		To prevent race conditions change_sector sould be used instead of update_sector from connected clients.
		"""
		with self._lock:
			assert type(self.map[x][y][key]) == type(diff) , "value has the wrong type"
			self.map[x][y][key] += diff
			self.map[x][y]["last_update"] = time.time()
			self._map_changed()

	def change_base_points(self,diff):
		"""changes base points about diff"""
		with self._lock:
			self.base_points += diff
			self.various_last_update = time.time()

	def change_turn_number(self, n):
		with self._lock:
			self.turn["turn_number"] += n
			self.turn["last_update"] = time.time()

	def change_max_turns(self, n):
		with self._lock:
			self.turn["max_turns"] += n
			self.turn["last_update"] = time.time()

	def end_turn(self):
		with self._lock:
			self._next_turn()
			self.turn["last_update"] = time.time()

	def change_turn_time_remaining(self,seconds):
		with self._lock:
			self._timer_thread.cancel()
			self.turn['turn_started'] += seconds
			turn = self.get_turn_status()
			if turn["remaining"] > 0:
				self._timer_thread = threading.Timer(turn["remaining"], self._next_turn)
				self._timer_thread.start()
			else:
				self._next_turn()
			self.turn["last_update"] = time.time()

	def change_setting(self,setting,value):
		with self._lock:
			try:
				assert(type(self.settings[key]) == type(value))
				self.settings[key] += value
				self.settings["last_update"] = time.time()
			except Exception as e:
				print(e)

	def set_setting(self,setting,value):
		with self._lock:
			try:
				assert(type(self.settings[key]) == type(value))
				self.settings[key] == value
				self.settings["last_update"] = time.time()
			except Exception as e:
				print(e)

	def change_scoreboard_kills(self,shipname,value):
		with self._lock:
			self.scoreboard_kills[shipname] += value
			self.scoreboard_last_update = time.time()

	def change_scoreboard_clears(self,shipname,value):
		with self._lock:
			self.scoreboard_clears[shipname] += value
			self.scoreboard_last_update = time.time()

	def add_beachhead(self,x,y):
		#there one beachhead may occure multiple times in this list. this results in a higher amount of enemies in that sector
		with self._lock:
			t = time.time()
			self.various_last_update = t
			self.map[x][y]["Beachhead"] = True
			self.map[x][y]["last_update"] = t
			return self.beachheads.append((x,y))

	def remove_beachhead(self,x,y):
		#removes the first occurence of the beachhead from the list.
		with self._lock:
			if (x,y) in self.beachheads:
				self.beachheads.remove((x,y))
			if (x,y) not in self.beachheads:
				self.map[x][y]["Beachhead"] = False
			t = time.time()
			self.various_last_update = t
			self.map[x][y]["last_update"] = t

	def add_event_map(self,client,x,y,key,value):
		"""
		Add a new rule: 
		The map of the client at the given sector is changed.
		Client is a client-tuple (ip_address, port) or a ip_address or a shipname string or a one-tuple ("Admiral") or ("GM") or ("All-Artemis-Clients") or ("ALL")
		("ALL") matches every client, other one-tuples are applied after that. Individual Artemis clients after both.
		If more than one client-tuple, ip_address or shipname match, only the FIRST ONE in that order is applied!
		x and y are the coordinates of the sector, key is the key in the sector dict.
		value changes the old value: if it is int or float, it is ADDED, otherwise the old value is replaced.
		Be aware, that all rules only change the SHOWN map, not the game state or the battles.
		Artemis clients can enter EVERY sector that is not hidden to them.
		"""
		assert type(x) == int
		assert type(y) == int
		assert x >= 0 and x <= 7
		assert y >= 0 and y <= 7
		with self._lock:
			assert key in self.map[x][y]
			assert type(value) == type(self.map[x][y][key])
			if not client in self.events_get_map:
				self.events_get_map[client] = []
			self.events_get_map[client].append((x,y,key,value))
			self.various_last_update = time.time()
		
	def remove_event_map(self,client,x,y,key,value):
		with self._lock:
			if client not in self.events_get_map:
				return False
			try:
				self.events_get_map[client].remove(x,y,key,value)
				self.various_last_update = time.time()
			except:
				return False
		return True	

	def clear_event_map(self,client):
		with self._lock:
			if client not in self.events_get_map:
				return False
			self.events_get_map[client].clear()
			self.various_last_update = time.time()
		return True

	def add_event_enter(self,client,x,y,key,value):
		"""
		Add a new rule: 
		The battle of the client at the given sector is changed.
		Client is a client-tuple (ip_address, port) or a ip_address or a shipname string or a one-tuple ("All-Artemis-Clients")
		If ("All-Artemis-Clients") is given, it is applied before rules of individual clients
		If more than one client-tuple, ip_address or shipname match, only the FIRST ONE in that order is applied!
		x and y are the coordinates of the sector, key is the key in the sector dict.
		if x or y are negative, the rule is applied to every sector the client enters
		value changes the old value: if it is int or float, it is ADDED, otherwise the old value is replaced.
		Be aware, that all rules only change battles, not the map itself.
		Artemis clients can enter EVERY sector that is not hidden to them.
		"""
		assert type(x) == int
		assert type(y) == int
		assert x <= 7
		assert y <= 7
		if x < 0 or y < 0:
			coordinates = "any"
			x=0
			y=0
		else:
			coordinates = (x,y)
		with self._lock:
			assert key in self.map[x][y]
			assert type(value) == type(self.map[x][y][key])
			if not client in self.events_enter_sector:
				self.events_enter_sector[client] = {}
			if not coordinates in self.events_enter_sector[client]:
				self.events_enter_sector[client][coordinates] = []
			self.events_enter_sector[client][coordinates].append((key,value))
			self.various_last_update = time.time()
		
	def remove_event_enter(self,client,x,y,key,value):
		assert type(x) == int
		assert type(y) == int
		if x < 0 or y < 0:
			coordinates = "any"
		else:
			coordinates = (x,y)

		with self._lock:
			if client not in self.events_enter_sector:
				return False
			try:
				self.events_enter_sector[client][coordinates].remove((key,value))
				self.various_last_update = time.time()
			except:
				return False
		return True	

	def clear_event_enter(self,client):
		with self._lock:
			if client not in self.events_enter_sector:
				return False
			self.events_enter_sector[client].clear()
			self.various_last_update = time.time()
		return True

	#artemis connected interaction

	def enter_sector(self,x,y,shipname,client):
		"""
		This is called when an Artemis client enters a sector.
		Returns the sector as dict.
		The implementation may decide to send other data then shown on the map.
		You may also alter the shipname here to avoid collisions.
		You can return None, to forbid that client enters that setor now.
		"""
		with self._lock:
			if client in self.ships:
				self.ships[client] = (shipname,-1,-1,0,0)	#invalidate, since client is not in a sector right now
				self.various_last_update = time.time()
			sector = copy.deepcopy(self.map[x][y])

			changes = []
			c = self.events_enter_sector.get(("All-Artemis-Clients"))
			if c is not None:
				if "any" in c:
					changes += c["any"]
				if (x,y) in c:
					changes += c[(x,y)]
			c = self.events_enter_sector.get(client)
			if c == None:
				c = self.events_enter_sector.get(client[0])
			if c == None:
				c = self.events_enter_sector.get(shipname)
			if c is not None:
				if "any" in c:
					changes += c["any"]
				if (x,y) in c:
					changes += c[(x,y)]
			for k,v in changes:
				if type(v) == int or type(v) == float:
					sector[k] += v
				else: 
					sector[k] = v

			if sector["blocked"]:
				return None	#Dont enter sectors blocked by GM
			if sector["Hidden"]:
				return None	#Dont enter hidden sectors
			if not sector["always_enterable"]:
				if self.settings["non reentrant sectors"]:
					for key in self.ships:
						if self.ships[key][1] == x and self.ships[key][2] == y:
							return None	#Sector Forbidden 
				if sector["Enemies"] <= 0:
					return None	#Dont enter sectors without enemies
				friendly_neighbours = 0
				for t in self._all_neighbours(x,y):
					t_x,t_y = t
					if t_x < 0 or t_x > 7 or t_y < 0 or t_y > 7:
						continue
					if self.map[t_x][t_y]["Hidden"]:
						continue
					if self.map[t_x][t_y]["Enemies"] == 0:
						friendly_neighbours += 1
				if friendly_neighbours == 0:
					#sectors can't be entered from north with original settings. Is this also true in original WarServer?
					return None
			

			sector.update({
				"ID":			random.randrange(16**4),
#				"Ship-Name":	"Tessöl",
				"Difficulty":	max(1, min(11, self.settings["game difficulty level"] + sector["Difficulty_mod"])),
			})
			if sector.get("Ship-Name") is not None:
				shipname = sector["Ship-Name"]
			self.ships[client] = (shipname,x,y,sector["ID"],sector["Enemies"])
			self._map_changed()
			self.various_last_update = time.time()
		print(sector)
		print(shipname + " entered sector " + chr(x+ord('A')) + str(y+1) +"." )
		return sector

	def clear_sector(self,shipname,id,client):
		"""
		This is called after an Artemis client sends an leave sector packet.
		The client has defeated all enemies in that sector.
		"""
		with self._lock:
			assert client in self.ships
			battle = self.ships[client]
			x = battle[1]
			y = battle[2]
			if x != -1:
				self.scoreboard_kills[shipname] += battle[4]
				self.ships[client] = (shipname,-1,-1,0,0)
				self.change_base_points(1)
				self.scoreboard_clears[shipname] += 1
				self.map[x][y]["Enemies"] = 0
				for _x, _y in self._all_neighbours(x,y):
					self.map[_x][_y]["fog"] = False
				self._map_changed()
				t = time.time()
				self.various_last_update = t
				self.scoreboard_last_update= t
				self.map[x][y]["last_update"]= t
		if x != -1:
			print(shipname + " cleared sector " + chr(x+ord('A')) + str(y+1) +"." )

	def kills_in_sector(self,shipname,id,kills,client):
		"""
		This is called after an Artemis client killed one or more enemies.
		The client still resides in that sector.
		"""
		with self._lock:
			assert client in self.ships
			battle = self.ships[client]
			x = battle[1]
			y = battle[2]
			assert battle[0] == shipname
			assert battle[3] == id
			self.ships[client] = (battle[0], battle[1], battle[2], battle[3], battle[4]-kills)
			self.map[x][y]["Enemies"] = min(battle[4]-kills, self.map[x][y]["Enemies"])
			self.scoreboard_kills[shipname] += kills
			t = time.time()
			self.various_last_update = t
			self.scoreboard_last_update= t
			self.map[x][y]["last_update"]= t
			self._map_changed()
		print(shipname + " defeated " + str(kills) + " enem" + ("y" if kills == 1 else "ies") + " in sector " + chr(battle[1]+ord('A')) + str(battle[2]+1) +"." )

	def disconnect_client(self, client):
		"""When a client disconects, free the sector"""
		with self._lock:
			if client in self.ships:
				self.ships[client] = (shipname,-1,-1,0,0)
				self.various_last_update = time.time()


	# varios methods

	def register_notification(self,event):
		"""
		The caller mat provide an event to the engine, which is set when the map changes.
		The caller must clear his event himself.
		"""
		self._notifications.append(event)

	def reset_fog(self):
		"""reveals fog around all sectors next to own sectors, and set fog to all others"""

		for col in range(0,8):
			for row in range(0,8):
				self.map[col][row]["fog"] = True
				self.map[col][row]["last_update"] = time.time()
		for col in range(0,8):
			for row in range(0,8):
				if self.map[col][row]["Enemies"] == 0 and self.map[col][row]["Hidden"] == False:
					for x,y in self._all_neighbours(col, row):
						if x <= 7 and x >= 0 and y <= 7 and y >= 0:
							self.map[x][y]["fog"] = False
		self._map_changed()

	def _map_changed(self):
		"""Called to notify other modules that the map has changed"""
		with self._lock:
			self.last_map_change = time.time()
		for e in self._notifications:
			e.set()

	def _next_turn(self):
		"""proceeds to the next turn"""
		with self._lock:
			self._timer_thread.cancel()	#ignored if this is executed by the timer_thread itself
			t = time.time()
			self.turn["turn_started"] = t
			self.turn["time_passed"] = 0.0
			if self.turn["interlude"]:
				if self.turn["turn_number"] <= self.turn["max_turns"]:
					self.turn["interlude"] = False 
					self.turn["remaining"] = self.settings["minutes per turn"]*60
					#autosave
					self._save_game("_autosave_"+time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(t))+"_turn_"+str(self.turn["turn_number"])+".sav")
				else:
					self.turn["remaining"] = self.settings["minutes between turns (interlude)"]*60
			else:
				self._defeat_bases(self.map)
				self._enemies_proceed(self.map)
				self._enemies_spawn(self.map)
				self.end_of_last_turn = time.time()
				for client in self.ships:
					self.ships[client] = (self.ships[client][0],-1,-1,0,0)	#clear all the shipnames
				self.turn["turn_number"] += 1
				self.turn["interlude"] = True
				self.turn["remaining"] = self.settings["minutes between turns (interlude)"]*60
			self.turn["last_update"] = t
			self._timer_thread = threading.Timer(self.turn["remaining"], self._next_turn)
			self._timer_thread.start()
			self._map_changed()	#awakens notify thread. Turn over is sent.

	def _defeat_bases(self,map):
		"""
		Destroys all bases in sectors where enemies are.
		The map given as argument is modified in-place.
		You may call this method with a copy of the games map,
		so you can see what happens without modifying the actual map.
		"""
		with self._lock:
			for column in map:
				for sector in column:
					if sector["Enemies"] > 0:
						sector["Rear_Bases"] = 0
						sector["Forward_Bases"] = 0
						sector["Fire_Bases"] = 0

	def _enemies_spawn(self,map):
		"""
		Enemies enter the map.
		The map given as argument is modified in-place.
		You may call this method with a copy of the games map,
		so you can see what happens without modifying the actual map.
		"""
		with self._lock:
			enemies = self.settings["invaders per turn"] // len(self.beachheads)
			plus_one = self.settings["invaders per turn"] % len(self.beachheads)
			for x,y in self.beachheads:
				map[x][y]["Enemies"] += enemies
				if plus_one > 0:
					map[x][y]["Enemies"] += 1
					plus_one -= 1

			
	def _enemies_proceed(self,map):
		"""
		Enemies move around.
		The map given as argument is modified in-place.
		You may call this method with a copy of the games map,
		so you can see what happens without modifying the actual map.
		"""
		with self._lock:
			for col in range(8):
				for row in range(8):
					sector = map[col][row]
					neighbours = self._neighbours(col,row)
					enemies = sector["Enemies"] // len(neighbours)
					for t in copy.copy(neighbours):
						x,y = t
						if x < 0 or x > 7 or y < 0 or y > 7:
							neighbours.remove(t)
						elif map[x][y]["Hidden"]:
							neighbours.remove(t)
					if self.settings["hidden sectors cant be neighbours"]:
						enemies = sector["Enemies"] // len(neighbours)
					for t in neighbours:
						x,y = t
						map[x][y]["pending_invaders"] += enemies
						sector["Enemies"] -= enemies
			for col in range(8):
				for row in range(8):
					map[col][row]["Enemies"] += map[col][row]["pending_invaders"]
					map[col][row]["pending_invaders"] = 0

	def _neighbours(self, x_0, y_0):
		result = []
		if self.settings["enemies can go north"]:
			nei = [(0,0),(1,0),(-1,0),(0,1),(0,-1)]
		else:
			nei = [(0,0),(1,0),(-1,0),(0,1)]

		for x_1,y_1 in nei:
			result.append((x_0+x_1, y_0+y_1))
		return result

	def _all_neighbours(self, x_0, y_0):
		"""all neighbouring sectors. used to determin which sector can be entered"""
		result = []
		for x_1,y_1 in [(0,-1),(1,0),(-1,0),(0,1)]:
			result.append((x_0+x_1, y_0+y_1))
		return result

	def __getstate__(self):
		with self._lock:
			#picke calls this method when serializing the object
			# Copy the object's state from self.__dict__ which contains
			# all our instance attributes. Always use the dict.copy()
			# method to avoid modifying the original state.
			state = self.__dict__.copy()
			# Remove the unpicklable entries.
			for k in self.__dict__:
				if k.startswith("_"):
					del state[k]
			return state

	def _save_game(self, filename):
		"""
			Saves the game.
			When calling manually, call get_turn_status before, to set remaining time correctly.
			Otherwise the game time is set to the last call of get_turn_status from any client.
		"""
		with self._lock:
			try:
				directory = "SaveGamesWarServer"
				filename = os.path.basename(filename)	#no directory traversal possible
				os.makedirs(directory, exist_ok=True)
				with open(directory+"/"+filename,"wb") as file:
					pickle.dump(self, file)
			except Exception as e:
				print("save failed: "+str(e))

	def _start_from_loaded_game(self):
		self._lock = threading.RLock()
		self._notifications = []
		self._timer_thread = threading.Timer(self.turn["remaining"], self._next_turn)
		t = time.time()
		self.end_of_last_turn = t
		self.turn["last_update"] = t
		self.turn["turn_started"] = t - self.turn["time_passed"]
		self._timer_thread.start()
		self._map_changed()	#awakens notify thread. Turn over is sent.
		print("Game Engine started")


#game=Game({})
game=None

def start_game(settings):
	#TODO ignored by now
	global game
	if settings == None:
		settings = {}
	game=Game(settings)
