#!/usr/bin/env python3
import threading
import time

class countdown:
	def __init__(self, seconds, cmd, *args, **kwargs):
		if seconds:
			self.seconds = seconds
		else: 
			self.seconds = 0
		self.cmd = cmd
		self.args = args
		self.kwargs = kwargs
		self.started = time.time() 
		if seconds:
			self.paused = False
			self.start()
		else:
			self.paused = True 

	def get_remaining(self):
		return self.seconds - (time.time() - (self.started or 0))

	def get_started(self):
		return self.started

	def start(self):
		self.started = time.time()
		self.paused = False 
		self.timer = threading.Timer(self.seconds, self.zero)
		self.timer.start()

	def pause(self):
		self.timer.cancel()
		t = time.time()
		dt = t - self.started
		self.seconds -= dt
		self.paused = True
	
	def cancel(self):
		self.timer.cancel()
		self.seconds = 0
		self.paused = False
		self.started = 0
		
	def set(self, seconds):
		self.timer.cancel()
		self.seconds = seconds
		if not self.paused:
			self.start()	
		
	def inc(self, dseconds):
		self.timer.cancel()
		self.seconds += dseconds
		if not self.paused:
			self.start()	

	def dec(self, dseconds):
		self.timer.cancel()
		self.seconds -= dseconds
		if not self.paused:
			self.start()	

	def zero(self):
		self.timer.cancel() #ignored
		self.cmd(self.args, self.kwargs)

	def __getstate__(self):
		return None
		print("redrum")
		r = self.__dict__
		if "timer" in r:
			del r["timer"]
		if "cmd" in r:
			del r["cmd"]
		print(r)
		return r
