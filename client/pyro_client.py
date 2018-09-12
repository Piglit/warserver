#!/usr/bin/python3
import Pyro4
PYROERROR = False 
import tkinter as TK
from tkinter import ttk
import time
import threading
import itertools
import functools
import string
import json

#ideas:
#sector map frames get focus by mouseover, change relief
#buttons get grey when not enough bps 

terrain_types = [
	"Empty",                   
	"Nebula",                   
	"Minefield",                
	"Asteroid Belt",            
	"Black Hole Nursery",       
	"Wildlands",                
	"Crossroads",               
]

PRIVILEGE_LEVEL = "gm-admiral"
privilege_flags = {	#binary flags!
	"gm-admiral":	3,
	"gm":		2,
	"admiral":	1,
	"observer":	0,
}

def allow_privilege(level):
	return privilege_flags[PRIVILEGE_LEVEL] & privilege_flags[level]

#colors
turn_color="#000033"
turn_text_color="cyan"
map_color="black"
sector_color = "#000033" #only at beginning, later from sectors
sector_text_color = "yellow"
ships_color = "#000033"
ship_text_color="yellow"
caption_color="white"

class InfoFrame(TK.LabelFrame):
	info_pane = None
	def __init__(self, fg=None, captionfg=caption_color, function=None, **kwargs):
		TK.LabelFrame.__init__(self, InfoFrame.info_pane, fg=captionfg, borderwidth=1, **kwargs)
		self.fg=fg
		self.function = function

	def show(self, sticky="nwes", **kwargs):
		InfoFrame.info_pane.add(self,sticky=sticky, **kwargs)

	def enable_right_click_menu(self):
		assert self.function != None
		#must be called when all children are registerd
		self.bind("<3>", self.function)
		self.bind("<1>", destroy_right_click_menu)
		for child in self.winfo_children():
			bindtags = list(child.bindtags())
			bindtags.insert(1, self)
			child.bindtags(tuple(bindtags))

class VariableLabel(TK.StringVar):
	def __init__(self, parent, row=None, text=None, textvariable=None, hidden=False, **kwargs):
		TK.StringVar.__init__(self)
		if "bg" not in kwargs and "background" not in kwargs:
			kwargs["bg"] = parent.config("bg")[4]
		if "fg" not in kwargs and "foreground" not in kwargs:
			if parent.fg is not None:
				kwargs["fg"] = parent.fg
			else:
				kwargs["fg"] = parent.config("fg")[4]
		if text:
			self.titlelable = TK.Label(parent, text=text+":", **kwargs)
		else:
			self.titlelable = None
		self.varlable   = TK.Label(parent, textvariable=textvariable or self, **kwargs)
		self.parent = parent
		self.hidden = hidden
		self.row = row or self.parent.grid_size()[1] 
		if not hidden:
			self.show()

	def config(self, **kwargs):
		if self.titlelable:
			self.titlelable.config(**kwargs)
		self.varlable.config(**kwargs)

	def show(self):
		if self.titlelable != None:
			self.titlelable.grid(row=self.row, column=0, sticky="E")
		self.varlable.grid	(row=self.row, column=1, sticky="W")

	
class Sector:
	"""
		repesents one game Sector.
		Each sector has two frames:
			a) the map frame, where the most important stats are shown
			b) the detail frame, where all information can be seen
		When the user clicks on the map frame, the detail frame will be shown
		In the detail frame are buttons, to place bases.
	"""
	def configure_class(map_frame, info_pane, map_size=None):
		Sector.map_frame = map_frame
		Sector.info_pane = info_pane
		if map_size!= None:
			Sector.map_sector_size = map_size/8
		else:
			#root maxsize is the maximum size of the window inclunding decorations, excluding tastbar
			#try removing two times the size of the taskbar to get an approriate size
			Sector.map_sector_size = (root.maxsize()[1] - 2*(root.winfo_screenheight() - root.maxsize()[1])) /8
		Sector.selected_sector = None
		Sector.empty_sector = InfoFrame(fg="white", bg="black", text="Sector Information")
		TK.Label(Sector.empty_sector, fg=sector_text_color, bg="black",text="Empty sector selected.").grid(row=0, sticky="nw")
#		TK.Label(Sector.empty_sector, fg=sector_text_color, bg="black",text="Empty sectors can not be entered.").grid(row=1, sticky="nw")
		Sector.empty_sector.show(hide=True)
		Sector.foggy_sector = InfoFrame(fg="white", bg="grey", text="Sector Information")
		TK.Label(Sector.foggy_sector, fg=sector_text_color, bg="grey",text="Unexplored sector selected.").grid(row=0, sticky="nw")
#		TK.Label(Sector.foggy_sector, fg=sector_text_color, bg="grey",text="Conquer a adjacent sector.").grid(row=1, sticky="nw")
		Sector.foggy_sector.show(hide=True)

		Sector.default_sector = InfoFrame(fg="white", bg="black", text="Sector Information")
		meassure = TK.Label(Sector.default_sector, fg=sector_text_color, bg="black",text=25*"W") #not shown
		Sector.info_pane.desired_width = meassure.winfo_reqwidth()
		TK.Label(Sector.default_sector, fg=sector_text_color, bg="black",text="Click on a sector to show detailed info.").grid(row=0, sticky="nw")
		Sector.default_sector.show(width=Sector.info_pane.desired_width)

	def __init__(self,col,row):
		self.x=col
		self.y=row
		self.hidden = False
		self.color = "grey"
		self.variables={
			"coordinates":	TK.StringVar(value=chr(col+ord('A'))+" "+str(row+1)),
			"enemies": 		TK.StringVar(),
			"rear_bases":	TK.StringVar(),
			"forward_bases":TK.StringVar(),
			"fire_bases":	TK.StringVar(),
			"name":			TK.StringVar(),
			"terrain_string":		TK.StringVar(),
			"difficulty":	TK.StringVar(),
			"beachhead_mark":	TK.StringVar(),
			"ships":		TK.StringVar(),
			"enemies_short":	TK.StringVar(),
			"difficulty_short":	TK.StringVar(),
			"bases_short":	TK.StringVar(),
		}
		self.map_frame = SectorMapFrame(self)
		self.info_frame = SectorInfoFrame(self)


	def __getitem__(self, item):
		return self.variables[item]	#raises key error
		
	def update(self, sector):
		self.hidden = sector["hidden"]
		self.fog = sector["fog"] and not allow_privilege("gm")
		if not self.hidden:	
			for key in self.variables:
				if key in sector:
					self.variables[key].set(sector[key])
			self["coordinates"].set(chr(self.x+ord('A'))+" "+str(self.y+1))
			self["terrain_string"].set(sector["terrain"])
			self["difficulty"].set(sector["difficulty"])
			if sector["beachhead_weight"]:
				self["beachhead_mark"].set("Invasion Beachhead")
			else:
				self["beachhead_mark"].set("")
			if sector["rear_bases"] + sector["forward_bases"] + sector["fire_bases"] > 0 and not self.fog:
				self["bases_short"].set(str(sector["rear_bases"])+"/"+str(sector["forward_bases"])+"/"+str(sector["fire_bases"]))
			else:
				self["bases_short"].set("")
			if sector["enemies"] > 0 and not self.fog:
				self["enemies_short"].set("Inv " + str(sector["enemies"]))
				self["difficulty_short"].set("D " + str(sector["difficulty"]))
			else:
				self["enemies_short"].set("")
				self["difficulty_short"].set("")
		else:
			for key in self.variables:
				self.variables[key].set("")

		color = ""	
		if self.variables["ships"].get() != "":
			color = "#000033"
		elif sector["fog"]:
			color="grey"
		elif sector["hidden"]:
			color="black"
		elif sector["enemies"] <= 0:
			color="#003300"
		elif sector["rear_bases"] + sector["forward_bases"] + sector["fire_bases"] > 0:
			color="#330000"	
		else:
			color="#333300"	
		self.set_color(color)

	def push_to_server(self, key, value):
		pass
		
	def set_color(self,color):
		self.color = color
		self.map_frame.set_color(color)
		self.info_frame.set_color(color)
		
	def reset_ships(self):
		self.variables["ships"].set("")
		self.update(state["map"][self.x][self.y])

	def add_ship(self, name):
		old = self.variables["ships"].get()
		if old == "":
			self.variables["ships"].set(name)
		else:
			self.variables["ships"].set(old+", "+name)
		color = "#000033"
		self.set_color(color)

	def place_base(self,base_type):
		game.place_base(self.x,self.y,base_type)
		force_update.set()

	def on_click(self, event):
		destroy_right_click_menu()
		if Sector.selected_sector != None:
			Sector.selected_sector.map_frame.config(relief="ridge")
			Sector.info_pane.paneconfig(Sector.selected_sector.info_frame, hide=True)
		Sector.default_sector.show(hide=True)
		Sector.empty_sector.show(hide=True)
		Sector.foggy_sector.show(hide=True)
		Sector.selected_sector = self
		self.map_frame.config(relief="groove")
		self.info_frame.set_color(self.color)
		if self.fog and not allow_privilege("gm"):
			Sector.info_pane.paneconfig(Sector.foggy_sector, hide=False, height=self.info_frame.winfo_reqheight(), width=Sector.info_pane.desired_width)
		elif self.hidden: 
			Sector.info_pane.paneconfig(Sector.empty_sector, hide=False, height=self.info_frame.winfo_reqheight(), width=Sector.info_pane.desired_width)
		else:
			Sector.info_pane.paneconfig(self.info_frame, hide=False, height=self.info_frame.winfo_reqheight(), width=Sector.info_pane.desired_width)

	def on_right_click(self, event):
		m = place_right_click_menu(event)
		if allow_privilege("admiral"):
			if not isinstance(event.widget, SectorInfoFrame):
				m.add_command(label="show detailed info", command=functools.partial(self.on_click, event))
			m.add_command(label="Place Rear Base (-1 Base Point)", 	command=functools.partial(self.place_base,1))
			m.add_command(label="Place Forward Base (-2 Base Point)", 	command=functools.partial(self.place_base,2))
			m.add_command(label="Place Fire Base (-3 Base Point)", 	command=functools.partial(self.place_base,3))
		if allow_privilege("gm"):
			if allow_privilege("admiral"):
				m.add_separator()
			ac = TK.Menu(m, tearoff=False)
			m.add_cascade(label = "Set Accessability", menu = ac)
			ac.add_command(label="Toggle Empty Sector",	command=functools.partial (game.set, "game.map." + str(self.x) + "." + str(self.y) + ".hidden", not state["map"][self.x][self.y]["hidden"]))
			ac.add_command(label="Toggle Fog of War",	command=functools.partial (game.set, "game.map." + str(self.x) + "." + str(self.y) + ".fog", not state["map"][self.x][self.y]["fog"]))
			terrain = TK.Menu(m, tearoff=False)
			m.add_cascade(label="Set Terrain", menu = terrain)
			for key in terrain_types:
				terrain.add_radiobutton(label=key, value=key, variable=self["terrain_string"], command=functools.partial(game.set, "game.map." + str(self.x) + "." + str(self.y) + ".terrain", key))
			m.add_command(label="Change Enemy Number", command=functools.partial (change_integer_dialog, functools.partial (game.modify, "game.map." + str(self.x) + "." + str(self.y) + ".enemies"), "Enemies"))
			m.add_command(label="Change Difficulty", command=functools.partial (change_integer_dialog, functools.partial (game.modify, "game.map." + str(self.x) + "." + str(self.y) + ".difficulty"), "Difficulty"))
			m.add_command(label="Add Beachhead",	command=functools.partial (game.add_beachhead, self.x, self.y))
			m.add_command(label="Remove Beachhead",	command=functools.partial (game.remove_beachhead, self.x, self.y))
			m.add_command(label="Change Name", command=functools.partial (change_string_dialog, functools.partial (game.set, "game.map." + str(self.x) + "." + str(self.y) + ".name"), "Sector Name"))

class SectorMapFrame(TK.Frame):
	"""This is a sector on the map frame, owned by a Sector object"""
	def __init__(self, sector):
		TK.Frame.__init__(self, Sector.map_frame, width=Sector.map_sector_size, height=Sector.map_sector_size, borderwidth=1, relief="ridge")
		self.grid_propagate(0)
		self.grid(row=row, column=col, sticky="nsew")
		self.columnconfigure(0,weight=1)
		self.columnconfigure(1,weight=1)
		self.columnconfigure(2,weight=1)
		self.rowconfigure(0,weight=1)
		self.rowconfigure(1,weight=1)
		self.rowconfigure(2,weight=1)
		self.rowconfigure(3,weight=1)
		TK.Label(self, fg="red", 	textvariable=sector["enemies_short"]).grid	(row=0, column=0, sticky="NW")
		TK.Label(self, fg="red", 	textvariable=sector["difficulty_short"], anchor="e").grid(row=0, column=2, sticky="NE")
		TK.Label(self, fg="yellow", textvariable=sector["bases_short"]).grid	(row=1, column=0, columnspan=2, sticky="NW")
		TK.Label(self, fg="#00fc00",textvariable=sector["ships"]).grid			(row=2, column=0, columnspan=3, sticky="NW")
		TK.Label(self, fg="white", 	textvariable=sector["coordinates"]).grid	(row=3, column=0, sticky="SW")
		self.bind("<1>", sector.on_click)
		self.bind("<3>", sector.on_right_click)
		for child in self.winfo_children():
			bindtags = list(child.bindtags())
			bindtags.insert(1, self)
			child.bindtags(tuple(bindtags))

	def set_color(self,color):
		self.config(bg=color)	
		for child in self.winfo_children():
			if not isinstance(child, TK.Menu):
				child.config(bg=color)
			
class SectorInfoFrame(InfoFrame):
	"""This is a sectors detail frame, owned by a Sector object"""
	
	def __init__(self, sector):	
		InfoFrame.__init__(self, fg="white", text="Sector Information")
		self.columnconfigure(0, weight=0)
		self.columnconfigure(1, weight=1)
		self.detail_variables=[
			VariableLabel(self, fg=sector_text_color, text="Coordinates", 		textvariable=sector["coordinates"], 	),
			VariableLabel(self, fg=sector_text_color, text="Invading Enemies", 	textvariable=sector["enemies"], 		),
			VariableLabel(self, fg=sector_text_color, text="Alert Level", 		textvariable=sector["difficulty"], 		),
			VariableLabel(self, fg=sector_text_color, text="Rear Bases", 		textvariable=sector["rear_bases"], 	),
			VariableLabel(self, fg=sector_text_color, text="Forward Bases", 	textvariable=sector["forward_bases"], ),
			VariableLabel(self, fg=sector_text_color, text="Fire Bases", 		textvariable=sector["fire_bases"], 	),
			VariableLabel(self, fg=sector_text_color, text="Sector Name", 		textvariable=sector["name"], 			),
			VariableLabel(self, fg=sector_text_color, text="Terrain", 			textvariable=sector["terrain_string"], ),
			VariableLabel(self, fg=sector_text_color, text="Active Ships", 		textvariable=sector["ships"], 		wraplength=240, ),
			VariableLabel(self, fg=sector_text_color, textvariable=sector["beachhead_mark"]),
		]

		self.bind("<3>", sector.on_right_click)
		self.bind("<1>", destroy_right_click_menu)
		for child in self.winfo_children():
			bindtags = list(child.bindtags())
			bindtags.insert(1, self)
			child.bindtags(tuple(bindtags))

		if allow_privilege("admiral"):
			TK.Button(self, text="Place Rear Base (-1 Base Point)", 	command=functools.partial(sector.place_base,1)).grid(row=10, column=0, columnspan=2, sticky="WE")
			TK.Button(self, text="Place Forward Base (-2 Base Point)", 	command=functools.partial(sector.place_base,2)).grid(row=11, column=0, columnspan=2, sticky="WE")
			TK.Button(self, text="Place Fire Base (-3 Base Point)", 	command=functools.partial(sector.place_base,3)).grid(row=12, column=0, columnspan=2, sticky="WE")
		Sector.info_pane.add(self, hide=True)

	def set_color(self,color):
		self.config(bg=color)	
		for child in self.winfo_children():
			if not isinstance(child, TK.Button) and not isinstance(child, TK.Menu):
				child.config(bg=color)

class TableFrame(InfoFrame):
	def __init__(self, *args, **kwargs):
		InfoFrame.__init__(self, *args, **kwargs)
		self.headings = {}
		self.items = {}

	def set_column_headings(self, *headings, **kwargs):
		self.headings = {}
		self.items = {}
		col = 0
		for h in headings:
			self.headings[h] = col
			TK.Label(self, text=h, **kwargs).grid(row=0, column=col)
			col += 1

	def add_row(self, iid, **kwargs):
		self.items[iid] = {}
		col = 0
		for h in self.headings:
			self.items[iid][h] = TK.StringVar()
			if "bg" not in kwargs and "background" not in kwargs:
				kwargs["bg"] = self.config("bg")[4]
			if "fg" not in kwargs and "foreground" not in kwargs:
				kwargs["fg"] = self.config("fg")[4]
			TK.Label(self, textvariable = self.items[iid][h], **kwargs).grid(row=len(self.items), column=col)
			col += 1

	def set_variable(self, iid, heading, value):
		self.items[iid][heading].set(value)

	def get_variable(self, iid, heading):
		return self.items[iid][heading].get()

	def __contains__(self, iid):
		return iid in self.items

	def __iter__(self):
		return self.items.__iter__()

	def __getitem__(self, iid):
		return self.items[iid]
	
	def set_row(self, iid, **kwargs):
		for k in kwargs:
			self.set_variable(iid, k, kwargs[k])

	

class Clock(TK.StringVar):
	#class is not threadsave
	_countdowns = []

	def __init__(self, countdown=True):
		TK.StringVar.__init__(self)
		self.countdown = countdown 
		if countdown:
			self.seconds = 0
			Clock._countdowns.append(self)	#not threadsave

	def set(self, seconds):
		"""accepts evert type, StringVar accepts. only float gets converted and counted down"""
		seconds = float(seconds)
		if self.countdown:
			self.seconds = seconds
		prefix=""
		if seconds < 0:
			seconds = -seconds
			prefix = "-"
		if seconds > 3600:
			seconds = time.strftime(prefix+"%H:%M:%S",time.gmtime(seconds))
		else:
			seconds = time.strftime(prefix+"%M:%S",time.gmtime(seconds))
		TK.StringVar.set(self, seconds)
		
	def decrease(self, dt):
		self.seconds -= dt
		self.set(self.seconds)

	def increase(self, dt):
		self.decrease(-dt)

	def quick_update():
		global time_updated_clock
		while not terminate:
			time.sleep(0.1)
			now = time.time()
			time_diff = now - time_updated_clock
			time_updated_clock = now
			for clock in Clock._countdowns:
				clock.decrease(time_diff)


def destroy_right_click_menu(_=None):
	global right_click_menu
	if right_click_menu != None:
		right_click_menu.destroy()

def place_right_click_menu(event):
	global right_click_menu
	destroy_right_click_menu()
	right_click_menu = TK.Menu(event.widget, tearoff=False)
	right_click_menu.post(event.x_root, event.y_root)
	return right_click_menu


def skip_interlude():
	if state["turn"]["interlude"] and time_remain > 10.0:
		game.end_turn()	

def call_remote_function_from_window(window, remote_function, cast, variable):
	value = variable.get()
	value = cast(value)
	remote_function(value)
	window.destroy()
	force_update.set()

def change_integer_dialog(remote_function, text):
	""" creates a dialoge window that asks for an integer input
		raises the local_variable about the user given amount
		and calls the remote_function with the same amount.
	"""
	w = TK.Toplevel(root)
	v = TK.StringVar()
	TK.Label(w, text=text + " += ").grid(row=0, column=0)
	TK.Entry(w, textvariable=v).grid(row=0, column=1)
	TK.Button(w, text="OK", command=functools.partial(call_remote_function_from_window, w, remote_function, int, v)).grid(row=1, column=1)
	TK.Button(w, text="Cancel", command=w.destroy).grid(row=1,column=0)

def change_float_dialog(remote_function, text):
	""" creates a dialoge window that asks for an integer input
		raises the local_variable about the user given amount
		and calls the remote_function with the same amount.
	"""
	w = TK.Toplevel(root)
	v = TK.StringVar()
	TK.Label(w, text=text + " += ").grid(row=0, column=0)
	TK.Entry(w, textvariable=v).grid(row=0, column=1)
	TK.Button(w, text="OK", command=functools.partial(call_remote_function_from_window, w, remote_function, float, v)).grid(row=1, column=1)
	TK.Button(w, text="Cancel", command=w.destroy).grid(row=1,column=0)

def change_string_dialog(remote_function, text):
	""" creates a dialoge window that asks for an integer input
		raises the local_variable about the user given amount
		and calls the remote_function with the same amount.
	"""
	w = TK.Toplevel(root)
	v = TK.StringVar()
	TK.Label(w, text=text + " = ").grid(row=0, column=0)
	TK.Entry(w, textvariable=v).grid(row=0, column=1)
	TK.Button(w, text="OK", command=functools.partial(call_remote_function_from_window, w, remote_function, str, v)).grid(row=1, column=1)
	TK.Button(w, text="Cancel", command=w.destroy).grid(row=1,column=0)


def turn_menu(event):
	m = place_right_click_menu(event)
	if allow_privilege("admiral"):
		if state["turn"]["interlude"] and time_remain > 10.0:
			m.add_command(label="Skip Interlude", command=skip_interlude)
			#skip interlude, but make sure, theres enough time left! Race condition must be prevented!
		else: 
			m.add_command(label="Skip Interlude", state="disabled")
	if allow_privilege("gm"):
		m.add_command(label="Save Game", command= functools.partial (game.save_game, "gm-save_"+time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))+"_turn_"+str(state["turn"]["turn_number"])+".sav"))
		m.add_command(label="End Turn", command= functools.partial (game.end_turn))
		m.add_command(label="Change Turn Number", command= functools.partial (change_integer_dialog, functools.partial(game.modify, "turn.turn_number"), "Turn Number"))
		m.add_command(label="Change Total Turns", command= functools.partial (change_integer_dialog, functools.partial(game.modify, "turn.max_turns"), "Total Turns"))
	#	m.add_command(label="Change Remaining Time", command= functools.partial (change_integer_dialog, functools.partial(game.change_turn_time_remaining), "Seconds Remaining"))
		m.add_command(label="Change Base Points", command= functools.partial (change_integer_dialog, functools.partial(game.modify, "admiral.strategy_points") , "Strategy Points"))
	#	m.add_command(label="Expand Fog of War", command= functools.partial (game.reset_fog))
	#	m.add_command(label="Change global Difficulty", command= functools.partial (change_integer_dialog, functools.partial(game.change_setting, "game difficulty level"), "global Difficulty"))
		m.add_command(label="Change Invaders Per Turn", command= functools.partial (change_integer_dialog, functools.partial(game.modify, "rules.invaders_per_turn"), "Invaders per turn"))
		m.add_command(label="Change Minutes Per Turn", command= functools.partial (change_float_dialog, functools.partial(game.modify, "rules.seconds_per_turn"), "Seconds per turn"))
		m.add_command(label="Change Minutes between Turns", command= functools.partial (change_float_dialog, functools.partial(game.modify, "seconds_per_interlude"), "Seconds between turns"))

def score_menu(event):
	if allow_privilege("admiral"):
		pass
		#merge two ships scores
	if allow_privilege("gm"):
		pass
		#change_scoreboard_kills
		#change_scoreboard_clears


def tech_menu(event):
	pass

def settings_menu(event):
	pass


#################################################################################

if __name__ == "__main__":
	print("Connecting to WarServer...")
	game = Pyro4.Proxy("PYRONAME:warserver")
	game.ping()
	print("Connected.")

state = {"last_update": -1.0}
time_last_update = time.time()
selected_sector = None
force_update = threading.Event()
terminate = False 

def quit(event=None):
	global terminate
	terminate = True
	root.destroy()
	print("Terminating")

root = TK.Tk()
root.title("Admiral Screen")

root.config(bg="black")
status_variable = TK.StringVar()
root.bind_all("<Key-q>", quit)

root.rowconfigure(0, weight=1)
root.columnconfigure(0, weight=1)


if root.maxsize()[1] >= 700:
	#default_font = tkFont.nametofont("TkDefaultFont")
	#default_font.configure(size=48)
	#root.option_add("*Font", "Trebuchet")
	root.option_add("*Font", "Bierbaron")

right_click_menu = None

master_frame =	TK.PanedWindow(root, orient=TK.HORIZONTAL)
master_frame.grid(sticky="nwse")
master_frame.columnconfigure(0, weight=1)
master_frame.columnconfigure(1, weight=1)

#general layout
map_frame = 	TK.Frame(master_frame, borderwidth=2, bg="black")
info_frame = 	TK.Frame(master_frame, bg="black")
master_frame.add(map_frame)
master_frame.add(info_frame, sticky="nwse")



info_pane = 	TK.PanedWindow(info_frame, orient=TK.VERTICAL, bg="black")
status_bar = 	TK.Label(info_frame, textvariable=status_variable)
info_frame.rowconfigure(0,weight=1)
info_pane.grid(row=0, sticky="nwse")
status_bar.grid(row=1, sticky="wse")

#info_pane layout
InfoFrame.info_pane = info_pane
turn_frame = 	InfoFrame(text="Status", 				bg=turn_color,	fg=turn_text_color, function=turn_menu)
score_frame = 	TableFrame(text="Ship Information", 	bg=ships_color,	fg=turn_text_color, function=score_menu)
tech_frame = 	TableFrame(text="Connected Clients", 	bg=ships_color,	fg=turn_text_color, function=tech_menu)

#turns
time_remain = 0.0
time_updated_clock = 0.0

turn_string = TK.StringVar()
turn_numbers = 	VariableLabel(turn_frame, text="Turn")
turn_time = 	Clock() 
turn_max_time = Clock(countdown=False) 
turn_war_time = Clock()

VariableLabel(turn_frame, bg=turn_color, fg=turn_text_color, text="Remaining Turn Time", textvariable=turn_time)
VariableLabel(turn_frame, bg=turn_color, fg=turn_text_color, text="Remaining War Time", textvariable=turn_war_time)
VariableLabel(turn_frame, bg=turn_color, fg=turn_text_color, textvariable=turn_string)

#base points
base_points = VariableLabel(turn_frame, text="Base Points")

turn_frame.show()
turn_frame.enable_right_click_menu()

#map
Sector.configure_class(map_frame, info_pane)
map_data = []
for col in range(0,8):
	map_data.append([])
	map_frame.columnconfigure(col,weight=1)
	map_frame.rowconfigure(col,weight=1)
	for row in range(0,8):
		map_data[col].append(Sector(col, row))

#scoreboard
score_frame.show()
score_frame.set_column_headings("Name","Kills","Clears", bg=ships_color, fg="white")
score_frame.enable_right_click_menu()

#techboard
if allow_privilege("gm"):
	tech_frame.show()
	tech_frame.set_column_headings("Name","Address", bg=ships_color, fg="white")
	tech_frame.enable_right_click_menu() #not implemented yet



def update():
	global time_remain
	global time_updated_clock
	global terminate
	while not terminate:
		force_update.wait(timeout=2)
		force_update.clear()
		time_called_for_update = time.time()
		try:
			updates = json.loads(game.get_game_state())#state["last_update"])
			if "map" in updates:
				corrected_map = []
				for x, col in updates["map"].items():
					corrected_map.append([])
					for y, sector in col.items():
						corrected_map[int(x)].append(sector)
				updates["map"] = corrected_map
			#print(updates)
		except:
			print("connnection lost")
			raise
			status_variable.set("connection lost since "+time.strftime("%S seconds",time.gmtime(time_called_for_update - time_got_update)))
			root.update_idletasks()
			continue
		time_got_update = time.time()
		time_latency = (time_got_update - time_called_for_update)/2
		state.update(updates)
		status_variable.set("connected to WarServer (IP: "+ str(game.get_ip()) +")")
		
		if "turn" in updates:
			turn_numbers.set(str(state["turn"]["turn_number"])+" / "+str(state["turn"]["max_turns"]))

			if state["turn"]["interlude"]:
				turn_string.set("Interlude")
				maxtime = state["rules"].get("seconds_per_interlude", 60*60)
			else:
				turn_string.set("")
				maxtime = state["rules"].get("seconds_per_turn", 60*60)
			turn_max_time.set(maxtime)
			time_remain = state["turn"]["remaining"]-time_latency
			time_updated_clock = time.time()
			turn_time.set(time_remain)
			time_war = (state["turn"]["max_turns"] - state["turn"]["turn_number"]) * (state["rules"].get("seconds_per_turn", 60*60) + state["rules"].get("seconds_per_interlude", 60*60))
			if state["turn"]["interlude"]:
				time_war += state["rules"].get("seconds_per_turn", 60*60)
			time_war += time_remain  
			turn_war_time.set(time_war)

		if "base_points" in updates:
			base_points.set(str(state["base_points"]))

		if "ships" in updates:
			for x in range(0,8):
				for y in range(0,8):
					map_data[x][y].reset_ships()
			for k in state["ships"]:
				ip,port = k
				name,x,y,_,enemies = state["ships"][k]
				if x > 0:
					sector = chr(x+ord('A')) + str(y+1)
					map_data[x][y].add_ship(name)
				else:	
					sector = None
				if k not in tech_frame:
					tech_frame.add_row(k, fg="cyan")
				tech_frame.set_row(k, Name=name, Address=str(ip))#+":"+str(port))

			for k in tech_frame:
				if k not in state["ships"]:
					tech_frame.remove_row(k)
			if allow_privilege("gm"):
				info_pane.paneconfig(tech_frame, height=tech_frame.winfo_reqheight())

		if "scoreboard" in updates:
			for name in state["scoreboard"][1]:
				kills = state["scoreboard"][1].get(name)
				clears = state["scoreboard"][0].get(name)
				if (kills == None or kills == 0) and (clears == None or clears == 0):
					if name in score_frame:
						scoreboard.remove_row(name)
				else:
					if name not in score_frame:
						score_frame.add_row(name, fg="cyan")
					score_frame.set_row(name, Name=name, Kills=state["scoreboard"][1][name], Clears=state["scoreboard"][0].get(name))
			info_pane.paneconfig(score_frame, height=score_frame.winfo_reqheight())

		if "sectors" in updates:
			map_iterator = updates["sectors"]
			del state["sectors"]
		elif "map" in updates:
			map_iterator = itertools.chain()
			for col in updates["map"]:
				map_iterator = itertools.chain(map_iterator, col)
		else:
			map_iterator = []
		for sector in map_iterator:
			x = sector["x"]
			y = sector["y"]
			state["map"][x][y].update(sector)
			map_data[x][y].update(sector)

print("Starting interface")

try:
	quick_thread = threading.Thread(target=Clock.quick_update)
	update_thread = threading.Thread(target=update)
	force_update.set()
	quick_thread.start()
	update_thread.start()

	TK.mainloop()
except:
	pass
terminate = True
