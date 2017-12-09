import Pyro4
import threading
import copy

import engine

@Pyro4.expose
class Observer:
	"""
	The Observer adapter class has access to getter methods only.
	Other classes like the admiral or the gm inherit from Observer. 
	"""
	def __init__(self):
		self.role = "Observer"

	def get_game_state(self):
		return {
			"map":			self.get_map(), 
			"turn":			self.get_turn_status(), 
			"ships":		self.get_ships(), 
			"scoreboard":	self.get_scoreboard(),
		}

	def get_map(self):
		return copy.deepcopy(engine.game.get_map(client=self.role))

	def get_turn_status(self):
		return copy.deepcopy(engine.game.get_turn_status(client=self.role))

	def get_ships(self):
		return copy.deepcopy(engine.game.get_ships(client=self.role))
	
	def get_scoreboard(self):
		return copy.deepcopy(engine.game.get_scoreboard(client=self.role))

	def get_settings(self):
		return copy.deepcopy(engine.game.get_settings(client=self.role))

@Pyro4.expose
class Admiral(Observer):
	"""
	The Admiral adapter class provides an interface for the Admiral.
	He can view the base points and place bases.
	"""
	def __init__(self):
		self.role = "Admiral"

	def get_base_points(self):
		return copy.deepcopy(engine.game.get_base_points(client=self.role))

	def place_base(self,x,y,base_value):
		""" x and y are coordinates of the sector
			base_value: 1 rear, 2 forward, 3 fire base
		"""
		assert type(x) == int and type(y) == int and type(base_value) == int
		assert x >= 0 and x <= 7 and y >= 0 and y <= 7 and base_value >= 1 and base_value <= 3
		if base_value > engine.game.get_base_points(client=self.role):
			return False
		base_type = ""
		if base_value == 1:
			base_type = "Rear_Bases"
		if base_value == 2:
			base_type = "Forward_Bases"
		if base_value == 3:
			base_type = "Fire_Bases"
		engine.game.change_base_points(-base_value)
		engine.game.change_sector(x,y,base_type,1)
		return True

@Pyro4.expose
class GM(Observer):
	def __init__(self):
		self.role = "GM"

	def change_sector(self, x, y, updates):
		"""
			x and y are coordinates of the sector.
			updates is a dict of keys in sector -> difference of a value.
			E.g. {"Enemies": -3, "Rear_Bases": +1} removes 3 enemies and place 1 rear base in the sector.
			"Name"(string) and "Hidden"(bool) values replace old values.
		"""
		assert type(x) == int, "x must be int"
		assert type(y) == int, "y must be int"
		assert x >= 0 and x < 8, "0 <= x <= 7"
		assert y >= 0 and y < 8, "0 <= y <= 7"
		assert type(updates) is dict
		for k,v in updates:
			assert(engine.game.get_map(client=self.role)[x][y][k] is not None, str(k)+" does not exist in sector.")
		for k,v in updates:
			if type(v) == bool or type(v) == str:
				engine.game.update_sector(x,y,k,v)
			else:
				engine.game.change_sector(x,y,k,v)
		return True	

	def change_turn_number(self, n):
		assert type(n) is int, "number must be int"
		engine.game.change_turn_number(n)

	def change_max_turns(self, n):
		assert type(n) is int, "number must be int"
		engine.game.change_max_turns(n)

	def end_turn(self):
		engine.game.end_turn()

	def change_turn_time_remaining(self,seconds):
		assert type(seconds) is int, "seconds must be int"
		engine.game.change_turn_time_remaining(seconds)

	def change_setting(self,setting,value):
		#TODO typecheck and existence check
		if type(value) == int or type(value) == float:
			engine.game.change_setting(setting,value)
		else:
			engine.game.set_setting(setting,value)

	def change_scoreboard_kills(self,shipname,value):
		assert type(shipname) == str
		assert type(value) == int
		engine.game.change_scoreboard_kills(shipname,value)

	def change_scoreboard_clears(self,shipname,value):
		assert type(shipname) == str
		assert type(value) == int
		engine.game.change_scoreboard_clears(shipname,value)


@Pyro4.expose
class Advanced(Observer):
	def __init__(self):
		self.role = "Advanced"


def start_pyro_server():
	daemon = Pyro4.Daemon()
	nameserver = Pyro4.locateNS()
	#nameserver.register("warserver_observer", daemon.register(Observer))
	nameserver.register("warserver_admiral",daemon.register(Admiral))
	nameserver.register("warserver_game_master",daemon.register(GM))
	#nameserver.register("warserver_advanced_game_master",daemon.register(Advanced))

	threading.Thread(target=daemon.requestLoop).start()	# start the event loop of the server to wait for calls
	print('Pyro server running. Connect with Pyro4.Proxy("PYRONAME:warserver_admiral")')
