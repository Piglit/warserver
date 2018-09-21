#!/usr/bin/env python3
from box import Box, BoxList
import pickle
import core.picklable as picklable
import random
import copy
import json
import os

"""the game object is accessible from all engine modules"""
game = Box(default_box=True)

DEFAULT_SECTOR = {
	"gm_forbid":	False,
	"gm_allow":		False,
	"hidden":		False,
	"fog":			False,
	"client_inside":	[],
	"hinder_movement":	False,
	"difficulty":	5,
	"enemies":		0,
	"rear_bases":	0,
	"forward_bases":0,
	"fire_bases":	0,
	"terrain":	"Sector",
	"unknown":	0,
	"name":	"",
	"pending_invaders":	0,
	"beachhead_weight":	0,
}
def init_sector(**kwargs):
	s = copy.deepcopy(DEFAULT_SECTOR)
	for k,v in kwargs.items():
		s[k] = v
	return s

## game state structure complete:
# game
#	-_lock
#	-map[x][y]
#			-gm_forbid
#			-gm_allow
#			-hidden
#			-fog
#			-client_inside
#			-hinder_movement
#			-x
#			-y
#			-coordinates(printable)
#			-difficulty
#			-enemies
#			-rear_bases
#			-forward_bases
#			-fire_bases
#			-seed
#			-terrain(string)
#			-unknown
#			-name
#			-last_update
#			-pending_invaders
#			-beachhead_weight(float)
#	-turn
#		-turn_number
#		-max_turns
#		-interlude(bool)
#		-last_update
#	-_countdown
#		-get_remaining()
#	-artemis_clients
#		-in_combat(bool)
#		-last_update
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
#		-allow_interludes
#		-infinite_game
#		-invasion_mode [ beachheads | random | none ]
#		-invaders_per_turn
#		-seconds_per_turn
#		-seconds_per_interlude
#		-enemies_dont_go_direction == [ none | north | south | west | east ]
#	-_notifications(list)

def updated(*args):
	"""something (given in args) has changed. Notifications are sent"""
	#TODO args should be used
	with game._lock:
		for event in game._notifications:
			event.set()

def get_game_state_as_json():
	game_state_dict = dict()
	game_state_json = "{"
	global game
	with game._lock:
		for key, value in game.items():
			if key.startswith("_"):
				continue
			else:
				if isinstance(value, Box):
					if key == "turn":
						value = copy.deepcopy(value.to_dict())
						value["remaining"] = game.countdown.get_remaining()
						game_state_dict[key] = value
					else:
						game_state_json += '"'+ key +'": ' + value.to_json() + ', '
				else:
					game_state_dict[key] = copy.deepcopy(value)
		game_state = game_state_json + json.dumps(game_state_dict).lstrip("{")
	return game_state

def get_item_as_json(path):
	global game
	items = path.split(".")
	target = game
	for item in items:
		try:
			target = target.get(item)
		except AttributeError:
			target = None
			break
		if item == "turn":
			value = copy.deepcopy(target.to_dict())
			value["remaining"] = game.countdown.get_remaining()
			target = value
	try:
		retval = target.to_json()
	except AttributeError:
		retval = json.dumps(target)
	return retval

def save_game(filename):
	"""
		Saves the game.
		When calling manually, call get_turn_status before, to set remaining time correctly.
		Otherwise the game time is set to the last call of get_turn_status from any client.
	"""
	json_game = get_game_state_as_json()
	try:
		directory = "SaveGamesWarServer"
		filename = os.path.basename(filename)	#no directory traversal possible
		os.makedirs(directory, exist_ok=True)
		with open(directory+"/"+filename, "w") as file:
			file.write(json_game)
		print("saved game as "+filename)
	except Exception as e:
		print("save failed: "+str(e))

def create_game(save):
	"""creates a new game from file. (file may be empty)"""
	global game
	if save:
		try:
			game.update(Box(json.load(save), default_box=True))
		except:
			game.update(Box(yaml.load(save), default_box=True))
	else:
		pass
	game._lock = picklable.RLock()
	if not game.map:
		game.map = Box()
		for x in range(8):
			game.map[x] = Box()
			for y in range(8):
				printable_coordinates = str(chr(ord("A")+x)) + str(y+1)
				terrain = random.choice(["Sector","Nebula","Minefield","Asteroid Belt","Black Hole Nursery","Wildlands","Crossroads"])
				game.map[x][y] = Box(init_sector(x=x, y=y, coordinates=printable_coordinates, seed=random.randrange(0x7fff*2), terrain=terrain))
	else:
		# keys may be strings now
		new_map = Box()
		for x, column in sorted(game.map.items()):
			assert int(x) == len(new_map)
			new_map[int(x)] = Box()
			for y, sector in sorted(column.items()):
				assert int(y) == len(new_map[int(x)])
				new_map[int(x)][int(y)] = sector
		game.map = new_map		
		

	if not game.rules:
		#Test mode
		game.rules = Box({}, default_box=True)
		game.rules.fog_of_war = False
		game.rules.clients_block_sectors = True
		game.rules.clients_move_through_sectors_with_other_clients = False
		game.rules.allow_interludes = True
		game.rules.infinite_game = False
		game.rules.invasion_mode = "beachheads"
		game.rules.invaders_per_turn = 20
		game.rules.seconds_per_turn = 120
		game.rules.seconds_per_interlude = 30
		game.rules.enemies_dont_go_direction = "none"
		game.map[4][0].beachhead_weight = 1.0
	if not game.turn:
		game.turn = Box(default_box=True)
		game.turn.turn_number = 1
		game.turn.interlude = False
		game.turn.max_turns = 10 
	if not game.admiral:
		game.admiral = Box({}, default_box=True)
		game.admiral.strategy_points = 0

	print("game object created")
	return game

