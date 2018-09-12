#!/usr/bin/env python3
from game_state import game

update_tree = dict()

##top-level stuctures
#-game
#	-map
#	-turn
#	-_countdown
#	-artemis_clients
#	-admiral
#	-rules

def updated(*path):
	with game._lock:
		t = time.time()
		key = tuple(path)
		update_tree[key] = t

def get_updates_since(time, toplevels*):
	with game._lock:
		paths = []
		for key, t in update_tree.items():
			if t > time:
				if not toplevels or key[0] in toplevels:
					paths.append(key)
		result = Box()
		for path in paths:
			src = game
			tar = result
			for n in path:
				if n not in tar:
					tar.n = Box()
				tar = tar.n
				src = src.n
			tar.update(copy.deepcopy(src))
		return result

def get_updates(toplevels*):
	t = time.time()
	r = get_updates_since(t, toplevels)	
	r.last_update = t
	return r
		

