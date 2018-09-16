#!/usr/bin/python3
"""
This is the WarServer game module.
Here the map and the game state is represented.
Other modules communicate with this module to read and to write the game state.
"""

import time
from box import Box
from core.game_state import game
from core.game_state import updated 
from core.game_state import save_game 
from core.countdown import countdown
from core import engine_artemis


## game state structure needed by this module:
# game
#	-map(Map)
#		[-sector]
#			-enemies
#			-pending_invaders
#			-rear_bases
#			-forward_bases
#			-fire_bases
#			-last_update
#			-beachhead_weight(float)
#	-turn
#		-turn_number
#		-max_turns
#		-interlude(bool)
#		-last_update
#	-_countdown
#		-get_remaining()
#	-rules
#		-allow_interludes
#		-infinite_game
#		-invasion_mode [ beachheads | random | none ]
#		-invaders_per_turn
#		-seconds_per_turn
#		-seconds_per_interlude
#		-enemies_dont_go_direction == [ none | north | south | west | east ]
#	-_notifications(list)

__author__ = "Pithlit"
__version__ = 1.0

def log(msg):
	print(time.asctime() + " Turn " + str(msg))

def start(remaining=None):
	if remaining is not None:
		t = remaining
	else:
		t = game.rules.seconds_per_turn
	if not game._countdown:
		game._countdown = countdown(t, proceed_turn)
	updated("turn")

def start_default_game():
	start()
	enemies_spawn()
	enemies_proceed()
	enemies_spawn()
	enemies_proceed()
	enemies_spawn()
	enemies_proceed()
	enemies_spawn()
	enemies_proceed()
	enemies_spawn()
	defeat_bases()
	enemies_proceed()
	updated("turn")
	

def proceed_turn(*args, **kwargs):
	"""proceeds to the next turn"""
	with game._lock:
		game._countdown.cancel()	#ignored if this is executed by the timer_thread itself
		turn = game.turn
		logmsg = None
		if turn["interlude"]:
			if turn["turn_number"] <= turn["max_turns"]:
				#turn_number starts with 1, interlude 1 comes after turn 1.
				turn["interlude"] = False
				game._countdown = countdown(game.rules.seconds_per_turn, proceed_turn)
				logmsg = str(turn.turn_number)
		else:
			defeat_bases()
			enemies_proceed()
			enemies_spawn()
			engine_artemis.release_all_ships()
			turn.turn_number += 1
			if not game.rules.allow_interludes:
				game._countdown = countdown(game.rules.seconds_per_turn, proceed_turn)
			else:
				turn.interlude = True
				game._countdown = countdown(game.rules.seconds_per_interlude, proceed_turn)
			save_game("_autosave_"+time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())+"_turn_"+str(turn["turn_number"])+".sav")

			logmsg = "interlude"
		updated("turn")
	if logmsg:
		log(logmsg + " started")



def defeat_bases():
	"""
	Destroys all bases in sectors where enemies are.
	The map given as argument is modified in-place.
	You may call this method with a copy of the games map,
	so you can see what happens without modifying the actual map.
	"""
	with game._lock:
		for column in game.map.values():	
			for sector in column.values():
				if sector["enemies"] > 0:
					sector["rear_bases"] = 0
					sector["forward_bases"] = 0
					sector["fire_bases"] = 0
					sector["last_update"] = time.time()

def enemies_spawn():
	"""
	Enemies enter the map.
	The map given as argument is modified in-place.
	You may call this method with a copy of the games map,
	so you can see what happens without modifying the actual map.
	"""
	with game._lock:
		if game.rules.invasion_mode == "beachheads":
			invading_sectors = []
			sum_weights = 0
			for column in game.map.values():	
				for sector in column.values():
					weight = sector.get("beachhead_weight")
					if weight and weight > 0.0:
						invading_sectors.append((weight, sector))
						sum_weights += weight
			if sum_weights > 0:
				remaining_enemies = game.rules["invaders_per_turn"]
				enemies_per_weight = int(game.rules["invaders_per_turn"] // sum_weights)
				for w, sector in invading_sectors:
					enemies = int(enemies_per_weight * w)
					sector["enemies"] += enemies 
					remaining_enemies -= enemies
				while remaining_enemies > 0: 
					for w, sector in sorted(invading_sectors):
						if remaining_enemies > 0:
							sector["enemies"] += 1
							remaining_enemies -= 1
						else:
							break
		elif game.rules.invasion_mode == "random":
			invading_sectors = []
			for column in game.map.values():	
				for sector in column.values():
					if sector["enemies"] > 0:
						invading_sectors.append(sector)
			for e in range(game.rules["invaders_per_turn"]):
				s = random.select(invading_sectors)	#eigentlich suche "invaders" zufällige
				s["enemies"] += 1

		if game.rules.invasion_mode == "none":
			pass

def enemies_proceed():
	"""
	Enemies move around.
	The map given as argument is modified in-place.
	You may call this method with a copy of the games map,
	so you can see what happens without modifying the actual map.
	"""
	with game._lock:
		for col in range(8):
			for row in range(8):
				sector = game.map[col][row]
				neighbours = _adjacent_for_enemies(col, row)
				if len(neighbours) == 0:
					continue
				enemies = int(sector.get("enemies",0) // len(neighbours))
				for s in neighbours:
					s["pending_invaders"] += enemies
					sector["enemies"] -= enemies
		for col in range(8):
			for row in range(8):
				game.map[col][row]["enemies"] += game.map[col][row]["pending_invaders"]
				game.map[col][row]["pending_invaders"] = 0

def _adjacent_for_enemies(x_0, y_0):
	"""returns all sectors, that count as connected for enemies"""
	result = []
	nei = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]
	if game.rules.enemies_dont_go_direction == "south":
		nei.remove (0, 1)
	if game.rules.enemies_dont_go_direction == "north":
		nei.remove (0, -1)
	if game.rules.enemies_dont_go_direction == "west":
		nei.remove (-1, 0)
	if game.rules.enemies_dont_go_direction == "east":
		nei.remove (1, 0)

	for x_1, y_1 in nei:
		x = x_0+x_1
		y = y_0+y_1
		if x < 0 or x >= 8:
			continue
		if y < 0 or y >= 8:
			continue
		s = game.map[x][y]
		if s.get("hidden"):
			continue
		result.append(s)
	return result

