try:
	import Pyro4
	pyro_avail = True
except ImportError:
	pyro_avail = False

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

	def get_beachheads(self):
		return copy.deepcopy(engine.game.get_beachheads(client=self.role))

	def get_base_points(self):
		return copy.deepcopy(engine.game.get_base_points(client=self.role))

@Pyro4.expose
class GM(Observer):
	def __init__(self):
		self.role = "GM"

	def place_base(self,x,y,base_value):
		""" x and y are coordinates of the sector
			base_value: 1 rear, 2 forward, 3 fire base
		"""
		assert type(x) == int and type(y) == int and type(base_value) == int
		assert x >= 0 and x <= 7 and y >= 0 and y <= 7 and base_value >= 1 and base_value <= 3
		if base_value > engine.game.get_base_points(client="Admiral"):
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


	def change_sector(self, x, y, key, value):
		"""
			x and y are coordinates of the sector.
			key,value must be in sector/
			"Name"(string) and "Hidden"(bool) values replace old values.
		"""
		assert type(x) == int, "x must be int"
		assert type(y) == int, "y must be int"
		assert x >= 0 and x < 8, "0 <= x <= 7"
		assert y >= 0 and y < 8, "0 <= y <= 7"
		assert key in engine.game.get_map(client=self.role)[x][y], str(key)+" does not exist in sector."
		if type(value) == bool or type(value) == str:
			engine.game.update_sector(x,y,key,value)
		elif type(value) == int:
			engine.game.change_sector(x,y,key,value)
		else:
			assert False, "Type Error"
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

	def add_beachhead(self,x,y):
		assert type(x) == int, "x must be int"
		assert type(y) == int, "y must be int"
		assert x >= 0 and x < 8, "0 <= x <= 7"
		assert y >= 0 and y < 8, "0 <= y <= 7"
		engine.game.add_beachhead(x,y)

	def remove_beachhead(self,x,y):
		assert type(x) == int, "x must be int"
		assert type(y) == int, "y must be int"
		assert x >= 0 and x < 8, "0 <= x <= 7"
		assert y >= 0 and y < 8, "0 <= y <= 7"
		engine.game.remove_beachhead(x,y)

def start_pyro_server():
	if pyro_avail:
		daemon = Pyro4.Daemon()
		uri = daemon.register(GM)
		try:
			nameserver = Pyro4.locateNS()
			nameserver.register("warserver_game_master",uri)
			print('Pyro server running. Connect custom python clients with Pyro4.Proxy("PYRONAME:warserver_game_master")')
		except Pyro4.errors.NamingError:
			print('Pyro server running. No Pyro name server found. Connect custom python clients from localhost with Pyro4.Proxy("'+str(uri)+'")')
		threading.Thread(target=daemon.requestLoop).start()	# start the event loop of the server to wait for calls
	else:
		print('Pyro module not available. Install pyro if you want to use custom python clients or an interactive shell.')
