#!/usr/bin/python3
"""
This is the WarServers artemis engine module.
The functions defined here are called when an Artemis server wants to modify the game state.
If you are used to an object-orientaded programming paradigm, you can see those functions as methods of the game object, that are visible to the artemis connector.
"""

__author__ = "Pithlit"
__version__ = 1.2

import random
import copy
import time
from core.game_state import game
from core.game_state import updated 

## game state structure needed by this module:
# game
#	-_lock
#	-map(Map)
#		[-sector]
#			-gm_forbid
#			-gm_allow
#			-hidden
#			-fog
#			-client_inside
#			-hinder_movement
#			-x
#			-y
#			-difficulty
#			-enemies
#			-rear_bases
#			-forward_bases
#			-fire_bases
#			-seed
#			-terrain(string)
#			-unknown
#			-name
#	-turn
#		-turn_number
#		-max_turns
#		-interlude(bool)
#	-_countdown
#		-get_remaining()
#	-artemis_clients
#		-in_combat(bool)
#		-battle
#			-id
#			-x
#			-y
#			-difficulty
#			-enemies
#			-rear_bases
#			-forward_bases
#			-fire_bases
#			-seed
#			-terrain(id)
#			-unknown
#	-admiral
#		-strategy_points
#	-rules
#		-fog_of_war
#		-clients_block_sectors
#		-clients_move_through_sectors_with_other_clients
#	-_notifications(list)

def log(msg):
	print(time.asctime() + " Artemis Client " + msg)

# getter methods

def get_map():
	"""
	Returns the whole map.
	It is used to show the map to Artemis clients.
	"""
	rv = []
	with game._lock:
		for x,column in sorted(game.map.items()):
			assert x == len(rv), "x: "+ str(x) +" rv: "+str(rv)
			rv.append([])
			for y,sector in sorted(column.items()):
				assert y == len(rv[x])
				rv[x].append(copy.deepcopy(sector))
	return rv

def get_turn_status():
	"Returns the turn dict with the seconds remaining as float"
	with game._lock:
		c = game._countdown
		turn = copy.deepcopy(game.turn)
		turn["remaining"] = max(c.get_remaining(), 0)
		return turn

def get_ships():
	with game._lock:
		ships = []
		for key, c in game.artemis_clients.items():
			if c.in_combat:
				ship = (str(c.shipname), int(c.battle.x), int(c.battle.y))
			else:
				ship = (str(c.shipname), -1, -1)
			ships.append(ship)
		return ships
	#artemis connected interaction
	#since this code is called from artemis connector request, exceptions can be thrown.

def _release_ship(client):
	"""removes clients ship from battles"""
	with game._lock:
		c = game.artemis_clients[client]
		if not c:
			game.artemis_clients[client] = c
		if c.in_combat:
			#battle is not reset because a clear package can arrive after turn release.
			x = c.battle.x
			y = c.battle.y
			cs = game.map[x][y].client_inside
			if client in cs:
				cs.remove(client)
				updated("map",x,y)
		c.in_combat = False 
		updated("artemis_clients", client)

def release_all_ships():
	"""called at the end of each turn"""
	with game._lock:
		for client in game.artemis_clients:
			_release_ship(client)

def _clientwall(client, sector):
	"""check if client may enter the sector"""
	c = game.artemis_clients[client]
	if sector.gm_forbid:
		log(str(client) + " enter request for sector " + str(sector.coordinates) + " refused (gm_forbid).")
		return False
	if sector.gm_allow:
		return True
	if sector.hidden:
		log(str(client) + " enter request for sector " + str(sector.coordinates) + " refused (hidden).")
		return False
	if game.rules.fog_of_war and sector.fog:
		log(str(client) + " enter request for sector " + str(sector.coordinates) + " refused (fog).")
		return False
	if game.rules.clients_block_sectors and sector.client_inside:
		log(str(client) + " enter request for sector " + str(sector.coordinates) + " refused (client_inside).")
		return False
	if sector.enemies <= 0:
		log(str(client) + " enter request for sector " + str(sector.coordinates) + " refused (no enemies).")
		return False
	if _adjacent_for_artemis_clients(sector):
		return True
	log(str(client) + " enter request for sector " + str(sector.coordinates) + " refused (no adjacent friendly sector).")
	return False

def _adjacent_for_artemis_clients(sector):
	"""returns all sectors, that count as connected for artemis clients"""
	x_0 = sector.x
	y_0 = sector.y
	result = []
	neighbours = [(1, 0), (-1, 0), (0, 1), (0, -1)]
	for x_1, y_1 in neighbours:
		x = x_0+x_1
		y = y_0+y_1
		if x < 0 or x >= 8:
			continue
		if y < 0 or y >= 8:
			continue
		s = game.map[x][y]
		if s.hidden:
			continue
		if game.rules.fog_of_war and s.fog:
			continue
		if s.enemies > 0:
			if game.rules.clients_move_through_sectors_with_other_clients and s.client_inside:
				pass
			else:
				continue	
		result.append(s)
	return result

def _start_battle(client, sector):
	with game._lock:
		t = time.time()
		c = game.artemis_clients[client]
		c.in_combat = True
		c.battle.id = random.randrange(16**4)
		c.battle.seed = sector.seed
		c.battle.x = sector.x
		c.battle.y = sector.y
		x = c.battle.x
		y = c.battle.y
		c.battle.difficulty = max(min(int(sector.get("difficulty", 7)),11),1)
		c.battle.enemies = int(sector.get("enemies",1))
		c.battle.rear_bases = int(sector.get("rear_bases",0))
		c.battle.forward_bases = int(sector.get("forward_bases",0))
		c.battle.fire_bases = int(sector.get("fire_bases",0))
		c.battle.terrain = sector.terrain
		c.battle.unknown = int(sector.get("unknown",0))
		c.log[t] = ("enter_sector", sector.coordinates)
		if not sector.client_inside:
			sector.client_inside = set()
		sector.client_inside.add(client)
		updated("artemis_clients", client)
		updated("map",x,y)
		return copy.deepcopy(c.battle)

def enter_sector(x, y, shipname, client):
	"""
	This is called when an Artemis client enters a sector.
	Returns the sector as dict.
	The implementation may decide to send other data then shown on the map.
	You may also alter the shipname here to avoid collisions.
	You can return None, to forbid that client enters that setor now.
	"""

	_release_ship(client)

	with game._lock:
		t = time.time()
		sector = game.map[x][y]
		game.artemis_clients[client].shipname = shipname	
		if not _clientwall(client, sector):
			game.artemis_clients[client].log[t] = ("on_map")	
			updated("artemis_clients", client, "log")
			return None
		log(shipname + str(client) + " entering sector " + str(sector.coordinates) )
		return _start_battle(client, sector)
		
def kills_in_sector(shipname, id, kills, client):
	"""
	This is called after an Artemis client killed one or more enemies.
	The client still resides in that sector.
	"""
	with game._lock:
		t = time.time()
		c = game.artemis_clients[client]
		if not c.in_combat:
			#too late; turn may be over or some bug occured
			return
		battle = c.battle
		assert battle.id == id
		battle.enemies -= kills
		sector = game.map[battle.x][battle.y]
		sector.enemies = max(0,min(battle.enemies, sector.enemies))
		c.log[t] = ("kills",kills)	
		updated("artemis_clients", client)
		updated("map",battle.x,battle.y)
	log(shipname + str(client) + " killed " + str(kills) + " in " + str(sector.coordinates))

def clear_sector(shipname, id, client):
	"""
	This is called after an Artemis client sends an leave sector packet.
	The client has defeated all enemies in that sector.
	"""

	with game._lock:
		t = time.time()
		c = game.artemis_clients[client]
		package_arrived_in_interlude = False
		if not c.in_combat:
			if not c.battle:
				return
			#clear arrived after turn over: check if no enemies are left.
			package_arrived_in_interlude = True
		battle = c.battle
		assert battle.id == id
		if package_arrived_in_interlude:
			if battle.enemies > 0:
				return	#invalid
		else:
			sector = game.map[battle.x][battle.y]
			sector.enemies = 0
		c.log[t] = ("clear",(battle.x, battle.y))	
		_release_ship(client)	#_release_ship updates
		game.admiral.strategy_points += 1
		updated("admiral")
	log(shipname + str(client) + " cleared " + str(sector.coordinates))

def disconnect_client(self, client):
	"""When a client disconects, free the sector"""
	_release_ship(client)

def register_notification(event):
	"""
	The caller gives to the engine, which is set when the map changes.
	The caller must clear his event himself.
	"""
	with game._lock:
		if not game._notifications:
			game._notifications = list()
		game._notifications.append(event)

