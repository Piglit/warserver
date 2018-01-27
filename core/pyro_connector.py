import threading
import copy
import time
import Pyro4
from Pyro4 import naming

import engine

@Pyro4.expose
class Observer:
	"""
	The Observer adapter class has access to getter methods only.
	Other classes like the admiral or the gm inherit from Observer. 
	"""
	def __init__(self):
		self.role = ("Observer")	#HACK: tuple ensures noone gets confused with a ship called Observer

	def get_game_state(self):
		return {
			"last_update":	time.time(),
			"map":			self.get_map(), 
			"turn":			self.get_turn_status(), 
			"ships":		self.get_ships(), 
			"scoreboard":	self.get_scoreboard(),
			"settings":		self.get_settings(),
			"beachheads":	self.get_beachheads(),
			"base_points":	self.get_base_points(),
		}

	def get_map(self):
		#map already is a copy
		return (engine.game.get_map(client=self.role))

	def get_sector(self,x,y):
		#sector already is a copy
		return engine.game.get_sector(x,y,self.role)

	def get_everything_but_map(self):
		return {
			"last_update":	time.time(),
			"turn":			self.get_turn_status(), 
			"ships":		self.get_ships(), 
			"scoreboard":	self.get_scoreboard(),
			"settings":		self.get_settings(),
			"beachheads":	self.get_beachheads(),
			"base_points":	self.get_base_points(),
		}

	def get_update(self, last_call):
		"""returns every update that happend after last_call"""
		if last_call == None or engine.game.end_of_last_turn > last_call:
			return self.get_game_state()
		assert(type(last_call) == float)
		retval = dict()
		retval["last_update"] = time.time()
		if engine.game.turn["last_update"] > last_call:
			retval["turn"] = self.get_turn_status()
		if engine.game.various_last_update > last_call:
			retval["ships"] = self.get_ships()
			retval["beachheads"] = self.get_beachheads()
			retval["base_points"] = self.get_base_points()
		if engine.game.scoreboard_last_update > last_call:
			retval["scoreboard"] = self.get_scoreboard()
		if engine.game.settings["last_update"] > last_call:
			retval["settings"] = self.get_settings()
		if engine.game.last_map_change > last_call:
			retval["sectors"] = list()
			for x in range(0,8):
				for y in range(0,8):
					if engine.game.map[x][y]["last_update"]	> last_call:
						retval["sectors"].append(self.get_sector(x,y))
		return retval

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

	def get_events_get_map(self):
		return copy.deepcopy(engine.game.get_events_get_map(client=self.role))

	def get_events_enter_sector(self):
		return copy.deepcopy(engine.game.get_events_enter_sector(client=self.role))

	def get_nothing(self):
		#just a ping
		return

@Pyro4.expose
class GM(Observer):
	def __init__(self):
		self.role = ("GM") #HACK: tuple ensures noone gets confused with a ship called GM 
		

	def place_base(self,x,y,base_value):
		""" x and y are coordinates of the sector
			base_value: 1 rear, 2 forward, 3 fire base
		"""
		assert type(x) == int and type(y) == int and type(base_value) == int
		assert x >= 0 and x <= 7 and y >= 0 and y <= 7 and base_value >= 1 and base_value <= 3
		if base_value > engine.game.get_base_points(client=("Admiral")):
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

	def change_base_points(self,value):
		assert type(value) == int
		engine.game.change_base_points(value)

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

	def add_event_map(self,client,x,y,key,value):
		engine.game.add_event_map(client,x,y,key,value)

	def remove_event_map(self,client,x,y,key,value):
		engine.game.remove_event_map(client,x,y,key,value)

	def clear_event_map(self,client):
		engine.game.clear_event_map(client)

	def add_event_enter(self,client,x,y,key,value):
		engine.game.add_event_enter(client,x,y,key,value)

	def remove_event_enter(self,client,x,y,key,value):
		engine.game.remove_event_enter(client,x,y,key,value)

	def clear_event_enter(self,client):
		engine.game.clear_event_enter(client)

	def reset_fog(self):
		engine.game.reset_fog()

	def save_game(self, filename):
		engine.game.get_turn_status()
		engine.game._save_game(filename)

def start_pyro_server(ip=None, host=None):
	daemon = Pyro4.Daemon(host=ip)
	uri = daemon.register(GM)
	try:
		nameserver = Pyro4.locateNS(host=host)
		nameserver.ping()
		nameserver.register("warserver_game_master",uri)
		print('Pyro server running on '+str(ip or "localhost")+'. Connect custom python clients with Pyro4.Proxy("PYRONAME:warserver_game_master")')
	except Pyro4.errors.NamingError:
		print('No Pyro naming server found. Starting own Pyro naming server.')
		try:
			if host == None:
				host = ""
			threading.Thread(target=Pyro4.naming.startNSloop, kwargs={"host": host}).start()
			#TODO check if this works for all clients in the network
			nameserver = Pyro4.locateNS()
			nameserver.ping()
			nameserver.register("warserver_game_master",uri)
			print('Pyro server running on '+str(ip or "localhost")+'. Connect custom python clients with Pyro4.Proxy("PYRONAME:warserver_game_master")')
		except Pyro4.errors.NamingError:
			print('Could not start Pyro naming server. Connect custom python clients from localhost with Pyro4.Proxy("'+str(uri)+'")')
	if ip == None:
		print("WARNING: option ip not given. Clients may not connect from other machines than yours. Try:")
		print("python3 warserver.py --ip <your ip>")
	threading.Thread(target=daemon.requestLoop).start()	# start the event loop of the server to wait for calls
