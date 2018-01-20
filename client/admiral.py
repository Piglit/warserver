#!/usr/bin/python3
import Pyro4
import tkinter as TK
from tkinter import ttk
import time
import threading
import itertools
import functools

ROWS_OF_SHIPS_WINDOW = 4

terrain_types = {
	0:    "Empty",                   
	1:    "Nebula",                   
	2:    "Minefield",                
	3:    "Asteroid Belt",            
	4:    "Black Hole Nursery",       
	5:    "Wildlands",                
	6:    "Crossroads",               
}

class Sector(TK.Frame):
	selected_sector = None
	def __init__(self,parent,col,row):
		heur_height = root.maxsize()[1] - 2*(root.winfo_screenheight() - root.maxsize()[1])
		#root maxsize is the maximum size of the window inclunding decorations, excluding tastbar
		#try removing two times the size of the taskbar to get an approriate size
		self.size = heur_height/8
		TK.Frame.__init__(self,parent, width=self.size, height=self.size, borderwidth=1, relief="ridge")
		self.grid_propagate(0)
		self.grid(row=row, column=col, sticky="nsew")
		self.x=col
		self.y=row
		self.hidden = False
		self.variables={
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
		self.coordinates = chr(col+ord('A'))+" "+str(row+1)
		self.columnconfigure(0,weight=1)
		self.columnconfigure(1,weight=1)
		self.columnconfigure(2,weight=1)
		self.rowconfigure(0,weight=1)
		self.rowconfigure(1,weight=1)
		self.rowconfigure(2,weight=1)
		self.rowconfigure(3,weight=1)
		TK.Label(self, fg="red", textvariable=self["Enemies_short"]).grid(row=0, column=0, sticky="NW")
		TK.Label(self, fg="red", textvariable=self["Difficulty_short"], anchor="e").grid(row=0, column=2, sticky="NE")
		TK.Label(self, fg="yellow", textvariable=self["Bases_short"]).grid(row=1, column=0, columnspan=2, sticky="NW")
		TK.Label(self, fg="#00fc00", textvariable=self["Ships"]).grid(row=2, column=0, columnspan=3, sticky="NW")
		TK.Label(self, fg="white", text=self.coordinates).grid(row=3, column=0, sticky="SW")
		self.bind("<1>", self.on_click)
		for child in self.winfo_children():
			bindtags = list(child.bindtags())
			bindtags.insert(1, self)
			child.bindtags(tuple(bindtags))


	def __getitem__(self, item):
		return self.variables[item]	#raises key error
		
	def update(self, sector):
		self.hidden = sector["Hidden"]
		if not self.hidden:
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
			
		self.config(bg=color)	
		self.color = color
		for child in self.winfo_children():
			child.config(bg=color)

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
		self.config(bg=color)	
		self.color = color
		for child in self.winfo_children():
			child.config(bg=color)


	def draw_detailed_info(self, parent):
		for child in parent.winfo_children():
			child.destroy()
		sector_frame.config(bg=self.color)
		if not self.hidden:

			TK.Label(parent, bg=self.color, fg=sector_text_color, text="Coordinates:").grid(row=0, column=0, sticky="E")
			TK.Label(parent, bg=self.color, fg=sector_text_color, text=self.coordinates).grid(row=0, column=1, sticky="W")
			VariableLabel(parent, bg=self.color, fg=sector_text_color, text="Invading Enemies", textvariable=self["Enemies"], row=1)
			VariableLabel(parent, bg=self.color, fg=sector_text_color, text="Alert Level", textvariable=self["Difficulty"], row=2)
			VariableLabel(parent, bg=self.color, fg=sector_text_color, text="Rear Bases", textvariable=self["Rear_Bases"], row=3)
			VariableLabel(parent, bg=self.color, fg=sector_text_color, text="Forward Bases", textvariable=self["Forward_Bases"], row=4)
			VariableLabel(parent, bg=self.color, fg=sector_text_color, text="Fire Bases", textvariable=self["Fire_Bases"], row=5)
			VariableLabel(parent, bg=self.color, fg=sector_text_color, text="Sector Name", textvariable=self["Name"], row=6)
			VariableLabel(parent, bg=self.color, fg=sector_text_color, text="Terrain", textvariable=self["Terrain_string"], row=7)
			VariableLabel(parent, bg=self.color, fg=sector_text_color, text="Active Ships", textvariable=self["Ships"], wraplength=240, row=8)
			TK.Label(parent, bg=self.color, fg=sector_text_color, textvariable=self["Beachhead_mark"]).grid(row=9, column=0, columnspan=2, sticky="WE")
			TK.Button(parent, text="Place Rear Base (-1 Base Point)", command=functools.partial(self.place_base,1)).grid(row=10, column=0, columnspan=2, sticky="WE")
			TK.Button(parent, text="Place Forward Base (-2 Base Point)", command=functools.partial(self.place_base,2)).grid(row=11, column=0, columnspan=2, sticky="WE")
			TK.Button(parent, text="Place Fire Base (-3 Base Point)", command=functools.partial(self.place_base,3)).grid(row=12, column=0, columnspan=2, sticky="WE")
			
	def place_base(self,base_type):
		game.place_base(self.x,self.y,base_type)
		force_update.set()

	def on_click(self, event):
		if Sector.selected_sector != None:
			Sector.selected_sector.config(relief="ridge")
		Sector.selected_sector = self
		self.config(relief="groove")
		self.draw_detailed_info(sector_frame)	

class InfoFrame(TK.LabelFrame):
	info_pane = None
	def __init__(self, **kwargs):
		TK.LabelFrame.__init__(self, InfoFrame.info_pane, borderwidth=1, **kwargs)

	def show(self):
		InfoFrame.info_pane.add(self)

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
	
	def __getitem__(self, iid):
		return self.items[iid]
	
	def set_row(self, iid, **kwargs):
		for k in kwargs:
			self.set_variable(iid, k, kwargs[k])

class VariableLabel(TK.StringVar):
	def __init__(self, parent, row=None, text=None, textvariable=None, **kwargs):
		#TODO calculate row automatically
		TK.StringVar.__init__(self)
		if "bg" not in kwargs and "background" not in kwargs:
			kwargs["bg"] = parent.config("bg")[4]
		if "fg" not in kwargs and "foreground" not in kwargs:
			kwargs["fg"] = parent.config("fg")[4]
		self.titlelable = TK.Label(parent, text=text+":", **kwargs)
		self.varlable   = TK.Label(parent, textvariable=textvariable or self, **kwargs)
		self.titlelable.grid(row=row, column=0, sticky="E")
		self.varlable.grid	(row=row, column=1, sticky="W")


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
	
	def quick_update():
		global time_updated_clock
		while not terminate:
			time.sleep(0.1)
			now = time.time()
			time_diff = now - time_updated_clock
			time_updated_clock = now
			for clock in Clock._countdowns:
				clock.decrease(time_diff)

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
	#force_update.set()
	root.destroy()
	print("Terminating")
	#quick_thread.join(timeout=1.0)
	#update_thread.join(timeout=3.0)
	#print("Quit")
	#root.quit()
	#exit()


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

#colors
turn_color="#000033"
turn_text_color="cyan"
map_color="black"
sector_color = "#000033" #only at beginning, later from sectors
sector_text_color = "yellow"
ships_color = "#000033"
ship_text_color="yellow"

master_frame =	TK.PanedWindow(root, orient=TK.HORIZONTAL)
master_frame.grid(sticky="nwse")
master_frame.columnconfigure(0, weight=1)
master_frame.columnconfigure(1, weight=0)

#general layout
map_frame = 	TK.Frame(master_frame, borderwidth=2, bg="black")
info_frame = 	TK.Frame(master_frame, bg="black")
master_frame.add(map_frame)
master_frame.add(info_frame)

for x in range(0,8):
	map_frame.columnconfigure(x,weight=1)
	map_frame.rowconfigure(x,weight=1)

info_pane = 	TK.PanedWindow(info_frame, orient=TK.VERTICAL, bg="black")
status_bar = 	TK.Label(info_frame, textvariable=status_variable)
info_frame.rowconfigure(0,weight=1)
info_pane.grid(row=0, sticky="nwse")
status_bar.grid(row=1, sticky="wse")

#info_pane layout
InfoFrame.info_pane = info_pane
turn_frame = 	InfoFrame(text="Status", bg=turn_color, fg=turn_text_color)
score_frame = 	TableFrame(text="Ship Information", bg=ships_color, fg=turn_text_color)
ships_frame = 	InfoFrame(text="Ship Information", bg=ships_color, fg=turn_text_color)
sector_frame = 	InfoFrame(text="Sector Information", bg=sector_color, fg="white")

info_pane.add(turn_frame, minsize=100, sticky="nwe")
info_pane.add(sector_frame, minsize=300)
#info_pane.add(ships_frame, minsize=100, sticky="nwse")
#TODO better solution fpr minsize


#turns
time_remain = 0.0
time_war = 0.0
time_updated_clock = 0.0

turn_string = TK.StringVar()
turn_numbers = 	VariableLabel(turn_frame, text="Turn", row=0)
turn_time = 	Clock() 
turn_max_time = Clock(countdown=False) 
turn_war_time = Clock()

TK.Label(turn_frame, bg=turn_color, fg=turn_text_color, text="Time").grid(row=1, column=0,sticky="E")
TK.Label(turn_frame, bg=turn_color, fg=turn_text_color, textvariable=turn_time).grid(row=1,column=1,sticky="W")
TK.Label(turn_frame, bg=turn_color, fg=turn_text_color, textvariable=turn_max_time).grid(row=1,column=2,sticky="W")
TK.Label(turn_frame, bg=turn_color, fg=turn_text_color, text="Remaining War Time").grid(row=2, column=0,sticky="E")
TK.Label(turn_frame, bg=turn_color, fg=turn_text_color, textvariable=turn_war_time).grid(row=2, column=1,columnspan=2,sticky="W")
TK.Label(turn_frame, bg=turn_color, fg=turn_text_color, textvariable=turn_string).grid(row=3, column=0, sticky="E")

#base points
base_points = VariableLabel(turn_frame, row=4, text="Base Points")

#sector frame
TK.Label(sector_frame, bg=sector_color, fg=sector_text_color, text="Click on a sector to scan it").grid(row=0, column=0,sticky="W")
sector_frame.columnconfigure(0, weight=0)
sector_frame.columnconfigure(1, weight=1)

#scoreboard
score_frame.show()
score_frame.set_column_headings("Name","Kills","Clears", bg=ships_color, fg="white")
score_frame.add_row("123", fg="cyan")
score_frame.set_variable("123", "Name", "Tesselmis")
score_frame.set_variable("123", "Kills", 3)
score_frame.set_variable("123", "Clears", 4)
score_frame.add_row("2")
score_frame["2"]["Name"].set("USS KOENIG MELONIDAS II")
score_frame.add_row(23)
score_frame.set_row(23, Name="BlackmetalRegenbogenponyOfDOOM", Kills=23, Clears=None)

#ships
#ship_cache = {}
#ship_columns = ["Ship name","Kills","Clears","Sector","Enemies","Ip","Port"]
#ttk.Style().configure("Treeview", background=ships_color, fieldbackground=ships_color, foreground=ship_text_color)
#ship_tree = ttk.Treeview(ships_frame, columns=ship_columns, displaycolumns=ship_columns, height=ROWS_OF_SHIPS_WINDOW, selectmode="none")
#ships_bar = TK.Scrollbar(ships_frame, command=ship_tree.yview)
#ship_tree.configure(yscrollcommand=ships_bar.set)
#
#ship_tree.grid(row=0,column=0, sticky="NWSE")
#ships_bar.grid(row=0,column=1, sticky="NWSE")
#
#for c in ship_columns:
#	ship_tree.column(c,stretch=True)
#	ship_tree.heading(c,text=c)
#ship_tree.column("Ship name",width=240)
#ship_tree.column("Kills",width=60)
#ship_tree.column("Clears",width=60)
#ship_tree.column("Sector",width=60)
#ship_tree.column("Enemies",width=60)
#ship_tree.column("Ip",width=120)
#ship_tree.column("Port",width=60)
#ship_tree.column('#0',stretch=False,width=0,minwidth=0)

#map
map_data = []
for col in range(0,8):
	map_data.append([])
	for row in range(0,8):
		map_data[col].append(Sector(map_frame, col, row))


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

		if "ships" in updates or "scoreboard" in updates:
			ship_cache = {}
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
				if name not in ship_cache:
					ship_cache[name] = {}
				ship_cache[name]["ip"] = ip	
				ship_cache[name]["port"] = port	
				ship_cache[name]["x"] = x	
				ship_cache[name]["y"] = y
				ship_cache[name]["enemies"] = enemies
				ship_cache[name]["sector"] = sector
			for name in state["scoreboard"][0]:
				if name not in ship_cache:
					ship_cache[name] = {}
				ship_cache[name]["clears"] = state["scoreboard"][0].get(name)
			for name in state["scoreboard"][1]:
				if name not in ship_cache:
					ship_cache[name] = {}
				ship_cache[name]["kills"] = state["scoreboard"][1].get(name)
			for name in ship_cache:
				s = ship_cache[name]
				ship_tuple = (name,s.get("kills"),s.get("clears"),s.get("sector"),s.get("enemies"),s.get("ip"),s.get("port"))
				if not ship_tree.exists(name):
					ship_tree.insert("", 0, iid=name, values=ship_tuple)
				else:
					ship_tree.item(name, values=ship_tuple)


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
