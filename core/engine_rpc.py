
from core.game_state import game
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
		game_state_dict = dict()
		game_state_json = "{"
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

	def get(self, path):
		items = path.split(".")
		target = game
		for item in items:
			try:
				target = target.get(item)
			except AttributeError:
				target = None
				break
		try:
			retval = target.to_json()
		except AttributeError:
			retval = json.dumps(target)
		return retval
#
#	def call(self, path, *args, **kwargs):
#		items = path.split(".")
#		target = game
#		for item in items[:-1]:
#			try:
#				target = target.get(item)
#			except AttributeError:
#				target = None
#				break
#		target = items[-1](target, args, kwargs)
#		try:
#			retval = target.to_json()
#		except AttributeError:
#			retval = json.dumps(target)
#		return retval
#
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

	def save_game(self):
		pass
