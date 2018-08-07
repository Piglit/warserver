#!/usr/bin/env python3
from box import Box, BoxList
import pickle
import core.picklable as picklable
import random
import copy

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
	"beachhead_weight":	1,
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
#	-countdown
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
#		-seconds_per_turn
#		-seconds_per_interlude
#		-enemies_dont_go_direction == [ none | north | south | west | east ]

def save_game(filename):
	"""
		Saves the game.
		When calling manually, call get_turn_status before, to set remaining time correctly.
		Otherwise the game time is set to the last call of get_turn_status from any client.
	"""
	with game._lock:
		try:
			directory = "SaveGamesWarServer"
			filename = os.path.basename(filename)	#no directory traversal possible
			os.makedirs(directory, exist_ok=True)
			with open(directory+"/"+filename, "wb") as file:
				#TODO check
				pickle.dump(game.to_dict(), file)
		except Exception as e:
			print("save failed: "+str(e))


def create_game(save):
	"""creates a new game from file. (file may be empty)"""
	global game
	if save:
		try:
			game.update(Box(pickle.load(save), default_box=True))
		except:
			game.update(Box(yaml.load(save), default_box=True))
	else:
		pass
	if not game.map:
		game.map = BoxList([[Box(init_sector(x=x,y=y), default_box=True) for y in range(8)] for x in range(8)] ,default_box=True)
	game._lock = picklable.RLock()
	if not game.rules:
		game.rules = Box({}, default_box=True)
	print("game object created")
	return game

