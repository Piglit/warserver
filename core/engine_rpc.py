
from core.game_state import game
import copy
#import json
## game state structure that needs special handling:
# game
#	-_lock
#	-countdown
#		-get_remaining()
#	-admiral
#		-strategy_points

class rpc:

	def __init__(self):
		pass

	def ping(self):
		return True

	def get_game_state(self):
		game_state = copy.deepcopy(game)
		del game_state["_lock"]
		del game_state["countdown"]
		game_state["turn"]["remaining"] = game.countdown.get_remaining()
		game_state = game_state.to_json()
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
		target = game
		for item in items[:-1]:
			try:
				target = target.get(item)
			except AttributeError:
				target = None
				break
		if items[-1] not in target:
			return False
		if instanceof(target[items[-1]]) != instanceof(value):
			return False
		target[items[-1]] = value
		return True
			
	def modify(self, path, value):
		#value = json.loads(value)
		items = path.split(".")
		target = game
		for item in items[:-1]:
			try:
				target = target.get(item)
			except AttributeError:
				target = None
				break
		if items[-1] not in target:
			return False
		if instanceof(target[items[-1]]) != instanceof(value):
			return False
		target[items[-1]] += value
		return True

	def place_base(self,x,y,base_value):
		""" x and y are coordinates of the sector
			base_value: 1 rear, 2 forward, 3 fire base
		"""
		assert type(x) == int and type(y) == int and type(base_value) == int
		assert x >= 0 and x <= 7 and y >= 0 and y <= 7 and base_value >= 1 and base_value <= 3
		if base_value > game.get_base_points(client=("Admiral")):
			return False
		base_type = ""
		if base_value == 1:
			base_type = "Rear_Bases"
		if base_value == 2:
			base_type = "Forward_Bases"
		if base_value == 3:
			base_type = "Fire_Bases"
		game.change_base_points(-base_value)
		game.change_sector(x,y,base_type,1)
		return True

	def end_turn(self):
		game.end_turn()

	def change_turn_time_remaining(self,seconds):
		assert type(seconds) is int, "seconds must be int"
		game.change_turn_time_remaining(seconds)

	def add_beachhead(self,x,y):
		assert type(x) == int, "x must be int"
		assert type(y) == int, "y must be int"
		assert x >= 0 and x < 8, "0 <= x <= 7"
		assert y >= 0 and y < 8, "0 <= y <= 7"
		game.add_beachhead(x,y)

	def remove_beachhead(self,x,y):
		assert type(x) == int, "x must be int"
		assert type(y) == int, "y must be int"
		assert x >= 0 and x < 8, "0 <= x <= 7"
		assert y >= 0 and y < 8, "0 <= y <= 7"
		game.remove_beachhead(x,y)

