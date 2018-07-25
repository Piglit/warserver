
import Pyro4
from Pyro4 import naming

import threading
import core.engine_rpc

@Pyro4.expose
class pyro_rpc(core.engine_rpc.rpc):
	pass

def start_server(warserver_ip=None, nameserver_ip=None):
	#TODO warserver_ip autodetect 
	daemon = Pyro4.Daemon(host=warserver_ip)
	uri = daemon.register(pyro_rpc)
	try:
		nameserver = Pyro4.locateNS(host=nameserver_ip)
		nameserver.ping()
		nameserver.register("warserver_game_master",uri)
		print('Pyro server running on '+str(warserver_ip or "localhost")+'. Connect custom python clients with Pyro4.Proxy("PYRONAME:warserver_game_master")')
	except (Pyro4.errors.NamingError, OSError):
		print('No Pyro naming server found. Starting own Pyro naming server.')
		try:
			if nameserver_ip == None:
				nameserver_ip = ""
			threading.Thread(target=Pyro4.naming.startNSloop, kwargs={"host": nameserver_ip}).start()
			#TODO check if this works for all clients in the network
			nameserver = Pyro4.locateNS()
			nameserver.ping()
			nameserver.register("warserver_game_master",uri)
			print('Pyro server running on '+str(warserver_ip or "localhost")+'. Connect custom python clients with Pyro4.Proxy("PYRONAME:warserver_game_master")')
		except Pyro4.errors.NamingError:
			print('Could not start Pyro naming server. Connect custom python clients from localhost with Pyro4.Proxy("'+str(uri)+'")')
	if warserver_ip == None:
		print("WARNING: option ip not given. Clients may not connect from other machines than yours. Try:")
		print("python3 warserver.py --ip <your ip>")
	threading.Thread(target=daemon.requestLoop).start()	# start the event loop of the server to wait for calls

