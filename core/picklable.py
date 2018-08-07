import threading
class RLock(object):	
	def __init__(self):	
		self._lock = threading.RLock()	

	def acquire(self):	
		self._lock.acquire()	

	def release(self):	
		self._lock.release()	

	def __enter__(self):	
		self.acquire()	

	def __exit__(self, *args):
		self.release()

	def __getstate__(self):
		return None

