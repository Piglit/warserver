#!/usr/bin/python3
"""
This is the WarServers artemis engine module.
The functions defined here are called when an Artemis server wants to modify the game state.
If you are used to an object-orientaded programming paradigm, you can see those functions as methods of the game object, that are visible to the artemis connector.
"""

__author__ = "Pithlit"
__version__ = 1.2

import copy
from core.game_state import game



#not used now, but these strings are diplayed in Artemis when you transmit the corresponding numbers
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
#	-countdown
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


	# getter methods

def get_map():
	"""
	Returns the whole map.
	It is used to show the map to Artemis clients.
	"""
	with game._lock:
		map = copy.deepcopy(game.map)
	return map


def get_turn_status():
	"Returns the turn dict with the seconds remaining as float"
	with game._lock:
		c = game.countdown
		print(c)
		turn = copy.deepcopy(game.turn)
		turn["remaining"] = c.get_remaining()
		return turn

def get_ships():
	with self._lock:
		ships = []
		for client, c in game.artemis_clients:
			if c.in_combat:
				ship = (c.shipname, c.battle.x, c.battle.y)
			else:
				ship = (c.shipname, -1, -1)
		ships.appens(ship)
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
		return False
	if sector.gm_allow:
		return True
	if sector.hidden:
		return False
	if game.rules.fog_of_war and sector.fog:
		return False
	if game.rules.clients_block_sectors and sector.client_inside:
		return False
	if sector.enemies <= 0:
		return False
	if _adjacent_for_artemis_clients(sector):
		return True
	return False

def _adjacent_for_artemis_clients(sector):
	"""returns all sectors, that count as connected for artemis clients"""
	x_0 = sector.x
	y_0 = sector.y
	result = []
	neighbours = [(1, 0), (-1, 0), (0, 1), (0, -1)]
	for x_1, y_1 in nei:
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
		if sector.enemies > 0:
			if game.rules.clients_move_through_sectors_with_other_clients and s.client_inside:
				pass
			else:
				continue	
		result.append(s)
	return result

def _start_battle(client, sector):
		c = game.artemis_clients[client]
		c.in_combat = True
		c.battle.id = random.randrange(16**4)
		c.battle.seed = random.randrange(2**31)
		x = c.battle.x = sector.x
		y = c.battle.y = sector.y
		c.battle.difficulty = max(min(int(sector.get("difficulty", 7)),11),1)
		c.battle.enemies = int(sector.get("enemies",1))
		c.battle.rear_bases = int(sector.get("rear_bases",0))
		c.battle.forward_bases = int(sector.get("forward_bases",0))
		c.battle.fire_bases = int(sector.get("fire_bases",0))
		c.battle.terrain = TERRAIN_TYPES.get(sector.terrain, 0)
		c.battle.unknown = int(sector.get("unknown",0))
		c.log.append(t,"enter_sector",(x,y))
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

	with self._lock:
		t = time.time()
		sector = game.map[x][y]
		if not _clientwall(client, sector):
			game.artemis_clients[client].log.append(t,"on_map")	
			updated("artemis_clients", client, "log")
			return None
		game.artemis_clients[client].shipname = shipname	#_start_battle updates
		return _start_battle(client, sector)
		#changes = []
		#c = self.events_enter_sector.get(("All-Artemis-Clients"))
		#if c is not None:
		#	if "any" in c:
		#		changes += c["any"]
		#	if (x, y) in c:
		#		changes += c[(x, y)]
		#c = self.events_enter_sector.get(client)
		#if c == None:
		#	c = self.events_enter_sector.get(client[0])
		#if c == None:
		#	c = self.events_enter_sector.get(shipname)
		#if c is not None:
		#	if "any" in c:
		#		changes += c["any"]
		#	if (x, y) in c:
		#		changes += c[(x, y)]
		#for k, v in changes:
		#	if type(v) == int or type(v) == float:
		#		sector[k] += v
		#	else:
		#		sector[k] = v
		

def kills_in_sector(shipname, id, kills, client):
	"""
	This is called after an Artemis client killed one or more enemies.
	The client still resides in that sector.
	"""
	with game._lock:
		t = time.time()
		c = game.artemis_clients[client]
		assert c.in_combat
		battle = c.battle
		assert battle.id == id
		battle.enemies -= kills
		sector = game.map[battle.x][battle.y]
		sector.enemies = max(0,min(battle.enemies, sector.enemies))
		c.log.append(t,"kills",kills)	
		updated("artemis_clients", client)
		updated("map",x,y)


def clear_sector(shipname, id, client):
	"""
	This is called after an Artemis client sends an leave sector packet.
	The client has defeated all enemies in that sector.
	"""

	with game._lock:
		t = time.time()
		c = game.artemis_clients[client]
		assert c.in_combat
		battle = c.battle
		assert battle.id == id
		sector = game.map[battle.x][battle.y]
		c.log.append(t,"clear",(battle.x, battle.y))	
		sector.enemies = 0
		_release_ship(client)	#_release_ship updates
		game.admiral.strategy_points += 1
		updated("admiral")

#			for _x, _y in game._all_neighbours(x, y):
#				game.map[_x][_y]["fog"] = False
#			game._map_changed()

	def disconnect_client(self, client):
		"""When a client disconects, free the sector"""
		_release_ship(client)

	# varios methods

def register_notification(self, event):
	"""
	The caller mat provide an event to the engine, which is set when the map changes.
	The caller must clear his event himself.
	"""
	self._notifications.append(event)

