
from core.game_state import game
from core import game_state as engine
import core.engine_turns
import copy
from box import Box
import json

## game state structure that needs special handling:
# game
#	-_lock
#	-_countdown
#		-get_remaining()
#	-admiral
#		-strategy_points

class rpc:

	def __init__(self):
		pass

	def ping(self):
		return True

	def get_game_state(self):
		return engine.get_game_state_as_json()

	def get(self, path):
		return engine.get_item_as_json(path)

	def set(self, path, value):
		#value = json.loads(value)
		items = path.split(".")
		if items[0] == "game":
			items = items[1:]
		target = game
		for item in items[:-1]:
			try:
				if item.isdigit():
					i = int(item)
					target = target[i]
				else:
					target = target[item]
			except AttributeError:
				target = None
				break
		if not target or items[-1] not in target:
			print(target)
			raise AttributeError(path)
		if type(target[items[-1]]) != type(value):
			raise TypeError(value)
		with game._lock:
			target[items[-1]] = value
		return True
			
	def modify(self, path, value):
		#value = json.loads(value)
		items = path.split(".")
		if items[0] == "game":
			items = items[1:]
		target = game
		for item in items[:-1]:
			try:
				if item.isdigit():
					i = int(item)
					target = target[i]
				else:
					target = target[item]
			except AttributeError:
				target = None
				break
		if not target or items[-1] not in target:
			raise AttributeError
		if type(target[items[-1]]) != type(value):
			raise AttributeError
		with game._lock:
			target[items[-1]] += value
		return True

	def place_base(self,x,y,base_value):
		""" x and y are coordinates of the sector
			base_value: 1 rear, 2 forward, 3 fire base
		"""
		assert type(x) == int and type(y) == int and type(base_value) == int
		assert x >= 0 and x <= 7 and y >= 0 and y <= 7 and base_value >= 1 and base_value <= 3
		base_type = ""
		if base_value == 1:
			base_type = "rear_bases"
		if base_value == 2:
			base_type = "forward_bases"
		if base_value == 3:
			base_type = "fire_bases"
		with game._lock:
			if base_value > game.admiral.strategy_points:
				return False
			game.admiral.strategy_points -= base_value
			game.map[x][y][base_type] += 1
		return True

	def end_turn(self):
		core.engine_turns.proceed_turn()

	def change_turn_time_remaining(self,seconds):
		assert type(seconds) is int, "seconds must be int"
		with game._lock:
			game._countdown.inc(seconds)

	def save_game(self, filename):
		engine.save_game(filename)
