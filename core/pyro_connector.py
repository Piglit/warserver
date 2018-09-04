
import Pyro4
from Pyro4 import naming
from core.engine_rpc import rpc
import threading
import socket
import core.engine_rpc
from time import sleep

@Pyro4.expose
class pyro_rpc(rpc):
	def __init__(self):
		rpc.__init__(self)

	def get_ip(self):
		return get_ip()	

	def ping(self):
		return rpc.ping(self)

	def get_game_state(self):
		return rpc.get_game_state(self)

	def get(self, path):
		return rpc.get(self, path)
	
	def set(self, path, value):
		return rpc.set(self, path, value)

	def modify(self, path, value):
		return rpc.modify(self, path, value)

	def place_base(self,x,y,base_value):
		return rpc.place_base(self,x,y,base_value)

	def end_turn(self):
		return rpc.end_turn(self)

	def change_turn_time_remaining(self,seconds):
		return rpc.change_turn_time_remaining(self,seconds)

	def add_beachhead(self,x,y):
		return rpc.add_beachhead(self,x,y)

	def remove_beachhead(self,x,y):
		return rpc.remove_beachhead(self,x,y)


def get_ip():
	"""* 
	* Does NOT need routable net access or any connection at all. * Works
	even if all interfaces are unplugged from the network. * Does NOT need or even
	try to get anywhere else. * Works with NAT, public, private, external, and
	internal IP's * Pure Python 2 (or 3) with no external dependencies. * Works on
	Linux, Windows, and OSX.
	"""
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		# doesn't even have to be reachable	
		s.connect(('10.255.255.255', 1))	
		IP = s.getsockname()[0]	
	except:	
		IP = '127.0.0.1'	
	finally:	
		s.close()	
	return IP

def get_pyro_nameserver(ip):
	"""we assume there is no pyro nameserver in the network."""
	threading.Thread(target=Pyro4.naming.startNSloop, kwargs={"host": ip}).start()
	nameserver = False
	failcount = 0
	while not nameserver and failcount < 3:
		try:
			nameserver = Pyro4.locateNS(host=ip)
		except Pyro4.errors.NamingError:
			sleep(0.1)
			failcount += 1
	nameserver.ping()
	return nameserver

def start_server():
	ip = get_ip()
	daemon = Pyro4.Daemon(host=ip)
	uri = daemon.register(pyro_rpc)
	try: 
		nameserver = get_pyro_nameserver(ip)
		nameserver.register("warserver",uri)
		print('Pyro server running on '+str(ip)+'. Connect custom python clients with Pyro4.Proxy("PYRONAME:warserver")')
	except Pyro4.errors.NamingError:
		print('Could not start Pyro naming server. Connect custom python clients from localhost with Pyro4.Proxy("'+str(uri)+'")')
	threading.Thread(target=daemon.requestLoop).start()	# start the event loop of the server to wait for calls

