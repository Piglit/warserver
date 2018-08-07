
import time
from box import Box, BoxList

class TimeBox(Box):
	def __init__(self, *args, **kwargs):
		self._mod_times = {}
		super.__init__(args, kwargs)

	def __setattr__(self, name, value):
		self._mod_times[name] = time.time() 
		super.__setattr__(name,value)
