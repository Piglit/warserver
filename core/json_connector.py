
import random
import engine
import jsonpickle as json


clients = {}

def get_update(client_id):
	if client_id == None or client_id not in clients:
		client_id = random.randint()




def test():
	print(json.dumps(engine.game, unpicklable=False))	#you can also try unpicklable = True for more meta information.
	print("this was the json test in json_connector.py. You may safely disable it.")


