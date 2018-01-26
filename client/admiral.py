#!/usr/bin/python3
import Pyro4
import tkinter as TK
from tkinter import ttk
import time
import threading
import itertools
import functools
import string

#ideas:
#sector map frames get focus by mouseover, change relief
#buttons get grey when not enough bps 

terrain_types = {
	0:    "Empty",                   
	1:    "Nebula",                   
	2:    "Minefield",                
	3:    "Asteroid Belt",            
	4:    "Black Hole Nursery",       
	5:    "Wildlands",                
	6:    "Crossroads",               
}


PRIVILEGE_LEVEL = "admiral"
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
	def __init__(self, fg=None, captionfg=caption_color, **kwargs):
		TK.LabelFrame.__init__(self, InfoFrame.info_pane, fg=captionfg, borderwidth=1, **kwargs)
		self.fg=fg

	def show(self, sticky="nwes", **kwargs):
		InfoFrame.info_pane.add(self,sticky=sticky, **kwargs)

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
		TK.Label(Sector.foggy_sector, fg=sector_text_color, bg="grey",text="Unknown sector selected.").grid(row=0, sticky="nw")
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
			"Coordinates":	TK.StringVar(value=chr(col+ord('A'))+" "+str(row+1)),
			"Enemies": 		TK.StringVar(),
			"Rear_Bases":	TK.StringVar(),
			"Forward_Bases":TK.StringVar(),
			"Fire_Bases":	TK.StringVar(),
			"Name":			TK.StringVar(),
			"Terrain_string":		TK.StringVar(),
			"Difficulty":	TK.StringVar(),
			"Beachhead_mark":	TK.StringVar(),
			"Ships":		TK.StringVar(),
			"Enemies_short":	TK.StringVar(),
			"Difficulty_short":	TK.StringVar(),
			"Bases_short":	TK.StringVar(),
		}
		self.map_frame = SectorMapFrame(self)
		self.info_frame = SectorInfoFrame(self)


	def __getitem__(self, item):
		return self.variables[item]	#raises key error
		
	def update(self, sector):
		self.hidden = sector["Hidden"]
		self.fog = sector["fog"]
		if not self.hidden or self.fog:	#TODO improve this in engine!
			for key in self.variables:
				if key in sector:
					self.variables[key].set(sector[key])
			self["Terrain_string"].set(terrain_types[sector["Terrain"]])
			self["Difficulty"].set(sector["Difficulty_mod"]+state["settings"]["game difficulty level"])
			if sector["Beachhead"]:
				self["Beachhead_mark"].set("Invasion Beachhead")
			else:
				self["Beachhead_mark"].set("")
			if sector["Rear_Bases"] + sector["Forward_Bases"] + sector["Fire_Bases"] > 0:
				self["Bases_short"].set(str(sector["Rear_Bases"])+"/"+str(sector["Forward_Bases"])+"/"+str(sector["Fire_Bases"]))
			else:
				self["Bases_short"].set("")
			if sector["Enemies"] > 0:
				self["Enemies_short"].set("Inv " + str(sector["Enemies"]))
				self["Difficulty_short"].set("D " + str(sector["Difficulty_mod"]+state["settings"]["game difficulty level"]))
			else:
				self["Enemies_short"].set("")
				self["Difficulty_short"].set("")
		else:
			for key in self.variables:
				self.variables[key].set("")
		color = ""	
		if self.variables["Ships"].get() != "":
			color = "#000033"
		elif sector["Hidden"]:
			if sector["fog"]:
				color="grey"
			else:
				color="black"
		elif sector["Enemies"] <= 0:
			color="#003300"
		elif sector["Rear_Bases"] + sector["Forward_Bases"] + sector["Fire_Bases"] > 0:
			color="#330000"	
		else:
			color="#333300"	
		self.set_color(color)
		
	def set_color(self,color):
		self.color = color
		self.map_frame.set_color(color)
		self.info_frame.set_color(color)
		
	def reset_ships(self):
		self.variables["Ships"].set("")
		self.update(state["map"][self.x][self.y])

	def add_ship(self, name):
		old = self.variables["Ships"].get()
		if old == "":
			self.variables["Ships"].set(name)
		else:
			self.variables["Ships"].set(old+", "+name)
		color = "#000033"
		self.set_color(color)

	def place_base(self,base_type):
		game.place_base(self.x,self.y,base_type)
		force_update.set()

	def on_click(self, event):
		if Sector.selected_sector != None:
			Sector.selected_sector.map_frame.config(relief="ridge")
			Sector.info_pane.paneconfig(Sector.selected_sector.info_frame, hide=True)
		Sector.default_sector.show(hide=True)
		Sector.empty_sector.show(hide=True)
		Sector.foggy_sector.show(hide=True)
		Sector.selected_sector = self
		self.map_frame.config(relief="groove")
		self.info_frame.set_color(self.color)
		if not self.hidden:
			Sector.info_pane.paneconfig(self.info_frame, hide=False, height=self.info_frame.winfo_reqheight(), width=Sector.info_pane.desired_width)
		elif self.fog:
			if allow_privilege("gm"):
				Sector.info_pane.paneconfig(self.info_frame, hide=False, height=self.info_frame.winfo_reqheight(), width=Sector.info_pane.desired_width)
			else:
				Sector.info_pane.paneconfig(Sector.foggy_sector, hide=False, height=self.info_frame.winfo_reqheight(), width=Sector.info_pane.desired_width)

		else:
			Sector.info_pane.paneconfig(Sector.empty_sector, hide=False, height=self.info_frame.winfo_reqheight(), width=Sector.info_pane.desired_width)

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
		#TODO fix hiding by fog
		TK.Label(self, fg="red", 	textvariable=sector["Enemies_short"]).grid	(row=0, column=0, sticky="NW")
		TK.Label(self, fg="red", 	textvariable=sector["Difficulty_short"], anchor="e").grid(row=0, column=2, sticky="NE")
		TK.Label(self, fg="yellow", textvariable=sector["Bases_short"]).grid	(row=1, column=0, columnspan=2, sticky="NW")
		TK.Label(self, fg="#00fc00",textvariable=sector["Ships"]).grid			(row=2, column=0, columnspan=3, sticky="NW")
		TK.Label(self, fg="white", 	textvariable=sector["Coordinates"]).grid	(row=3, column=0, sticky="SW")
		self.bind("<1>", sector.on_click)
		for child in self.winfo_children():
			bindtags = list(child.bindtags())
			bindtags.insert(1, self)
			child.bindtags(tuple(bindtags))

	def set_color(self,color):
		self.config(bg=color)	
		for child in self.winfo_children():
			child.config(bg=color)

class SectorInfoFrame(InfoFrame):
	"""This is a sectors detail frame, owned by a Sector object"""
	
	def __init__(self, sector):	
		InfoFrame.__init__(self, fg="white", text="Sector Information")
		self.columnconfigure(0, weight=0)
		self.columnconfigure(1, weight=1)
		self.detail_variables=[
			VariableLabel(self, fg=sector_text_color, text="Coordinates", 		textvariable=sector["Coordinates"], 	),
			VariableLabel(self, fg=sector_text_color, text="Invading Enemies", 	textvariable=sector["Enemies"], 		),
			VariableLabel(self, fg=sector_text_color, text="Alert Level", 		textvariable=sector["Difficulty"], 		),
			VariableLabel(self, fg=sector_text_color, text="Rear Bases", 		textvariable=sector["Rear_Bases"], 	),
			VariableLabel(self, fg=sector_text_color, text="Forward Bases", 	textvariable=sector["Forward_Bases"], ),
			VariableLabel(self, fg=sector_text_color, text="Fire Bases", 		textvariable=sector["Fire_Bases"], 	),
			VariableLabel(self, fg=sector_text_color, text="Sector Name", 		textvariable=sector["Name"], 			),
			VariableLabel(self, fg=sector_text_color, text="Terrain", 			textvariable=sector["Terrain_string"], ),
			VariableLabel(self, fg=sector_text_color, text="Active Ships", 		textvariable=sector["Ships"], 		wraplength=240, ),
			VariableLabel(self, fg=sector_text_color, textvariable=sector["Beachhead_mark"]),
		]
		#self.bh_label = TK.Label(self, fg=sector_text_color, textvariable=sector["Beachhead_mark"])
		#self.bh_label.grid(row=9, column=0, columnspan=2, sticky="WE")
		TK.Button(self, text="Place Rear Base (-1 Base Point)", 	command=functools.partial(sector.place_base,1)).grid(row=10, column=0, columnspan=2, sticky="WE")
		TK.Button(self, text="Place Forward Base (-2 Base Point)", 	command=functools.partial(sector.place_base,2)).grid(row=11, column=0, columnspan=2, sticky="WE")
		TK.Button(self, text="Place Fire Base (-3 Base Point)", 	command=functools.partial(sector.place_base,3)).grid(row=12, column=0, columnspan=2, sticky="WE")
		Sector.info_pane.add(self, hide=True)

	def set_color(self,color):
		self.config(bg=color)	
		for child in self.winfo_children():
			if not isinstance(child, TK.Button):
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
		if type(seconds) == float:
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
		else:
			print("Warning: setting clock object not to float!")
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


class ModifiableLabel(TK.Frame):
	def __init__(self, parent, textvariable=None, backend_setter=None, needed_privilege_level="gm", **kwargs):
		TK.Frame__init__(self, parent, **kwargs)
		self.modifiable = privilege_flags[needed_privilege_level] & privilege_flags[PRIVILEGE_LEVEL]
		#TODO test^	
		self.textvariable = textvariable
		self.backend_setter = backend_setter
		self.label = TK.Label(self, textvariable=textvariable, **kwargs)
		self.label.grid(row=1, sticky="we")

class IncreasableLabel(ModifiableLabel):
	def __init__(self, *args, **kwargs):
		ModifiableLabel.__init__(self,*args,**kwargs)
		if self.modifiable:
			self.downframe = TK.Frame(self, **kwargs)
			self.upframe = TK.Frame(self, **kwargs)
			self.downframe.grid(row=2, sticky="we")
			self.upframe.grid(row=0, sticky="we")
			self.buttoncolmns = 0
			self._reset_buttons(float(self.textvariable.get()))

	def _reset_buttons(self, value):
		if isinstance(self.textvariable, Clock):
			if len(value) <= 2 and self.buttoncolmns != 2:
				buttoncolmns = 2
			elif len(value) <= 5 and self.buttoncolmns != 4:
				buttoncolmns = 4
			else:
				buttoncolmns = 5
			if self.buttoncolmns != buttoncolmns:
				self.buttoncolmns = buttoncolmns
				for child in self.upframe.winfo_children():
					child.destroy()
				for child in self.downframe.winfo_children():
					child.destroy()
				multiplier = 1
				for i in range(0, buttoncolmns):
					#TODO add placeholder for : in display
					TK.Button(self.upframe, 	command=functools.partial(self._inc, multiplier)).grid(column=buttoncolmns-1-i, row=0, sticky="we")
					TK.Button(self.downframe, 	command=functools.partial(self._dec, multiplier)).grid(column=1, row=buttoncolmns-1-i, sticky="we")
					if i%2 == 0:
						multiplier *= 10
					else:
						multiplier *= 6
		else:
			if value > 19 and self.buttoncolmns != 2:
				self.buttoncolmns = 2
				for child in self.upframe.winfo_children():
					child.destroy()
				for child in self.downframe.winfo_children():
					child.destroy()
				TK.Button(self.upframe, 	command=functools.partial(self._inc, 1)).grid(column=1, row=0, sticky="we")
				TK.Button(self.downframe, 	command=functools.partial(self._dec, 1)).grid(column=1, row=0, sticky="we")
				TK.Button(self.upframe, 	command=functools.partial(self._inc, 10)).grid(column=0, row=0, sticky="we")
				TK.Button(self.downframe, 	command=functools.partial(self._dec, 10)).grid(column=0, row=0, sticky="we")
			elif value < 10 and self.buttoncolmns != 1:
				self.buttoncolmns = 1
				for child in self.upframe.winfo_children():
					child.destroy()
				for child in self.downframe.winfo_children():
					child.destroy()
				TK.Button(self.upframe, 	command=functools.partial(self._inc, 1)).grid(column=0, row=0, sticky="we")
				TK.Button(self.downframe, 	command=functools.partial(self._dec, 1)).grid(column=0, row=0, sticky="we")
				self.lastvalue = value

	def _inc(self, delta):
		#not threadsave
		value = float(self.textvariable.get()) + delta
#		self.textvariable.set(value)	#make it visible, variable will be set correctly at next udate (FIXME or not if remote set fails!)
		self.backend_setter(delta)	#does not call force update
		#Better less responsive then faulty behaviour
		self._reset_buttons(value)

	def _dec(self, delta):
		self._inc(-delta)

print("Connecting to WarServer...")
game = Pyro4.Proxy("PYRONAME:warserver_game_master")
game.get_nothing()
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
turn_frame = 	InfoFrame(text="Status", bg=turn_color, fg=turn_text_color)
score_frame = 	TableFrame(text="Ship Information", bg=ships_color, fg=turn_text_color)
tech_frame = 	TableFrame(text="Connected Clients", bg=ships_color, fg=turn_text_color)


turn_frame.show()


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

#techboard
tech_frame.show()
tech_frame.set_column_headings("Name","Address", bg=ships_color, fg="white")

def update():
	global time_remain
	global time_updated_clock
	global terminate
	while not terminate:
		force_update.wait(timeout=2)
		force_update.clear()
		time_called_for_update = time.time()
		try:
			updates = game.get_update(state["last_update"])
		except:
			print("connnection lost")
			status_variable.set("connection lost since "+time.strftime("%S seconds",time.gmtime(time_called_for_update - time_got_update)))
			root.update_idletasks()
			continue
		time_got_update = time.time()
		time_latency = (time_got_update - time_called_for_update)/2
		state.update(updates)
		status_variable.set("connected to WarServer (IP: "+ str(game._pyroConnection.sock.getsockname()[0]) +")")
		

		if "turn" in updates:
			turn_numbers.set(str(state["turn"]["turn_number"])+" / "+str(state["turn"]["max_turns"]))

			if state["turn"]["interlude"]:
				turn_string.set("Interlude")
				maxtime = state["settings"]["minutes between turns (interlude)"]*60
			else:
				turn_string.set("Turn")
				maxtime = state["settings"]["minutes per turn"]*60
			turn_max_time.set(maxtime)
			time_remain = state["turn"]["remaining"]-time_latency
			time_updated_clock = time.time()
			turn_time.set(time_remain)
			time_war = (state["turn"]["max_turns"] - state["turn"]["turn_number"]) * (state["settings"]["minutes per turn"] + state["settings"]["minutes between turns (interlude)"])*60
			if state["turn"]["interlude"]:
				time_war += state["settings"]["minutes per turn"]*60
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
			info_pane.paneconfig(tech_frame, height=tech_frame.winfo_reqheight())

		if "scoreboard" in updates:
			for name in state["scoreboard"][1]:
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
