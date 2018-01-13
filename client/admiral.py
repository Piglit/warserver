#!/usr/bin/python3
import Pyro4
import tkinter as TK
from tkinter import ttk
import time
import threading
import itertools
import functools

ROWS_OF_SHIPS_WINDOW = 4
SCREEN_HEIGHT = 600 #replace with the height you want

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
	sector_color = "yellow"
	def __init__(self,parent,col,row):
		self.size = min(root.winfo_screenwidth(),SCREEN_HEIGHT)/10
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
		self.bind("<1>", on_click_sector)
		for child in sector_frame.winfo_children():
			bindtags = list(child.bindtags())
			bindtags.insert(1, sector_frame)
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
			TK.Label(parent, bg=self.color, fg=sector_text_color, text="Invading Enemies:").grid(row=1, column=0, sticky="E")
			TK.Label(parent, bg=self.color, fg=sector_text_color, textvariable=self["Enemies"]).grid(row=1, column=1, sticky="W")
			TK.Label(parent, bg=self.color, fg=sector_text_color, text="Alert Level:").grid(row=2, column=0, sticky="E")
			TK.Label(parent, bg=self.color, fg=sector_text_color, textvariable=self["Difficulty"]).grid(row=2, column=1, sticky="W")
			TK.Label(parent, bg=self.color, fg=sector_text_color, text="Rear Bases:").grid(row=3, column=0, sticky="E")
			TK.Label(parent, bg=self.color, fg=sector_text_color, textvariable=self["Rear_Bases"]).grid(row=3, column=1, sticky="W")
			TK.Label(parent, bg=self.color, fg=sector_text_color, text="Forward Bases:").grid(row=4, column=0, sticky="E")
			TK.Label(parent, bg=self.color, fg=sector_text_color, textvariable=self["Forward_Bases"]).grid(row=4, column=1, sticky="W")
			TK.Label(parent, bg=self.color, fg=sector_text_color, text="Fire Bases:").grid(row=5, column=0, sticky="E")
			TK.Label(parent, bg=self.color, fg=sector_text_color, textvariable=self["Fire_Bases"]).grid(row=5, column=1, sticky="W")
			TK.Label(parent, bg=self.color, fg=sector_text_color, text="Sector Name:").grid(row=6, column=0, sticky="E")
			TK.Label(parent, bg=self.color, fg=sector_text_color, textvariable=self["Name"]).grid(row=6, column=1, sticky="W")
			TK.Label(parent, bg=self.color, fg=sector_text_color, text="Terrain:").grid(row=7, column=0, sticky="E")
			TK.Label(parent, bg=self.color, fg=sector_text_color, textvariable=self["Terrain_string"]).grid(row=7, column=1, sticky="W")
			TK.Label(parent, bg=self.color, fg=sector_text_color, text="Active Ships:").grid(row=8, column=0, sticky="E")
			TK.Label(parent, bg=self.color, fg=sector_text_color, textvariable=self["Ships"], wraplength=240).grid(row=8, column=1, columnspan=3, sticky="W")
			TK.Label(parent, bg=self.color, fg=sector_text_color, textvariable=self["Beachhead_mark"]).grid(row=9, column=0, columnspan=2, sticky="WE")
			TK.Button(parent, text="Place Rear Base (-1 Base Point)", command=functools.partial(self.place_base,1)).grid(row=10, column=0, columnspan=2, sticky="WE")
			TK.Button(parent, text="Place Forward Base (-2 Base Point)", command=functools.partial(self.place_base,2)).grid(row=11, column=0, columnspan=2, sticky="WE")
			TK.Button(parent, text="Place Fire Base (-3 Base Point)", command=functools.partial(self.place_base,3)).grid(row=12, column=0, columnspan=2, sticky="WE")
			
	def place_base(self,base_type):
		game.place_base(self.x,self.y,base_type)
		force_update.set()

print("Connecting to WarServer...")
game = Pyro4.Proxy("PYRONAME:warserver_game_master")
game.get_nothing()
print("Connected.")

state = {"last_update": -1.0}
time_last_update = time.time()
selected_sector = None
force_update = threading.Event()
terminate = False 


def on_click_sector(event):
	global selected_sector
	if selected_sector != None:
		selected_sector.config(relief="ridge")
	sector = event.widget
	selected_sector = sector
	selected_sector.config(relief="groove")
	sector.draw_detailed_info(sector_frame)	
#	root.update_idletasks()

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
if SCREEN_HEIGHT == None:
	SCREEN_HEIGHT = root.winfo_screenheight()
#print(root.winfo_screenwidth())

root.config(bg="black")
status_variable = TK.StringVar()
root.bind_all("<Key-q>", quit)

if SCREEN_HEIGHT >= 700:
	#default_font = tkFont.nametofont("TkDefaultFont")
	#default_font.configure(size=48)
	#root.option_add("*Font", "Trebuchet")
	root.option_add("*Font", "Bierbaron")

#general layout
root.rowconfigure(0, weight=0)
root.rowconfigure(1, weight=1)
root.rowconfigure(2, weight=0)
root.rowconfigure(3, weight=1)
root.rowconfigure(4, weight=1)
root.rowconfigure(5, weight=0)

turn_color="#000033"
turn_text_color="cyan"
map_color="black"
sector_color = "#000033" #only at beginning, later from sectors
sector_text_color = "yellow"
ships_color = "#000033"
ship_text_color="yellow"

turn_frame = TK.LabelFrame(root, text="Status", borderwidth=1, bg=turn_color, fg=turn_text_color)
#base_point_frame = TK.Frame(root, borderwidth=1, bg="red")
ships_frame = TK.Frame(root, borderwidth=0, bg="black")
map_frame = TK.Frame(root, borderwidth=2, bg=map_color)
sector_frame = TK.LabelFrame(root, text="Sector Information" ,borderwidth=1, bg=sector_color, fg="white")
map_frame.grid			(row=0,column=0,rowspan=4,sticky="nsew")
turn_frame.grid			(row=0,column=1,sticky="nsew")
#base_point_frame.grid	(row=1,column=1,sticky="nsew")
#padding
sector_frame.grid		(row=2,column=1,sticky="nsew")
#padding
ships_frame.grid		(row=4,column=0,columnspan=2,sticky="nsew")
TK.Label(root, textvariable=status_variable).grid(row=5,column=0,columnspan=2,sticky="wse")

#turns
time_remain = 0.0
time_war = 0.0
time_updated_clock = 0.0
turn_string = TK.StringVar()
turn_numbers = TK.StringVar()
turn_time = TK.StringVar()
turn_max_time = TK.StringVar()
turn_war_time = TK.StringVar()
TK.Label(turn_frame, bg=turn_color, fg=turn_text_color, textvariable=turn_string).grid(row=0, column=0, sticky="E")
TK.Label(turn_frame, bg=turn_color, fg=turn_text_color, textvariable=turn_numbers).grid(row=0, column=1, columnspan=2, sticky="W")
TK.Label(turn_frame, bg=turn_color, fg=turn_text_color, text="Time").grid(row=1, column=0,sticky="E")
TK.Label(turn_frame, bg=turn_color, fg=turn_text_color, textvariable=turn_time).grid(row=1,column=1,sticky="W")
TK.Label(turn_frame, bg=turn_color, fg=turn_text_color, textvariable=turn_max_time).grid(row=1,column=2,sticky="W")
TK.Label(turn_frame, bg=turn_color, fg=turn_text_color, text="Remaining War Time").grid(row=2, column=0,sticky="E")
TK.Label(turn_frame, bg=turn_color, fg=turn_text_color, textvariable=turn_war_time).grid(row=2, column=1,columnspan=2,sticky="W")

#base points
base_points = TK.StringVar() 
TK.Label(turn_frame, bg=turn_color, fg=turn_text_color, text="Base Points").grid(row=3,column=0, sticky="E")
TK.Label(turn_frame, bg=turn_color, fg=turn_text_color, textvariable=base_points).grid(row=3,column=1, sticky="W")

#sector frame
TK.Label(sector_frame, bg=sector_color, fg=sector_text_color, text="Click on a sector to scan it").grid(row=0, column=0,sticky="W")
sector_frame.columnconfigure(0, weight=0)
sector_frame.columnconfigure(1, weight=1)


#ships
ship_cache = {}
ship_columns = ["Ship name","Kills","Clears","Sector","Enemies","Ip","Port"]
ttk.Style().configure("Treeview", background=ships_color, fieldbackground=ships_color, foreground=ship_text_color)
ship_tree = ttk.Treeview(ships_frame, columns=ship_columns, displaycolumns=ship_columns, height=ROWS_OF_SHIPS_WINDOW, selectmode="none")
ships_bar = TK.Scrollbar(ships_frame, command=ship_tree.yview)
ship_tree.configure(yscrollcommand=ships_bar.set)

ship_tree.grid(row=0,column=0, sticky="NWSE")
ships_bar.grid(row=0,column=1, sticky="NWSE")

for c in ship_columns:
	ship_tree.column(c,stretch=True)
	ship_tree.heading(c,text=c)
ship_tree.column("Ship name",width=240)
ship_tree.column("Kills",width=60)
ship_tree.column("Clears",width=60)
ship_tree.column("Sector",width=60)
ship_tree.column("Enemies",width=60)
ship_tree.column("Ip",width=120)
ship_tree.column("Port",width=60)
ship_tree.column('#0',stretch=False,width=0,minwidth=0)

#map
map_data = []
for col in range(0,8):
	map_data.append([])
	for row in range(0,8):
		map_data[col].append(Sector(map_frame, col, row))


def update():
	global time_remain
	global time_war
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
			turn_max_time.set(" / "+time.strftime("%M:%S",time.gmtime(maxtime)))
			time_remain = state["turn"]["remaining"]-time_latency
			time_updated_clock = time.time()
			turn_time.set(time.strftime("%M:%S", time.gmtime(time_remain)))
			time_war = (state["turn"]["max_turns"] - state["turn"]["turn_number"]) * (state["settings"]["minutes per turn"] + state["settings"]["minutes between turns (interlude)"])*60
			if state["turn"]["interlude"]:
				time_war += state["settings"]["minutes per turn"]*60
			time_war += time_remain  
			turn_war_time.set(time.strftime("%H:%M:%S", time.gmtime(time_war)))
			

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
#		try:
#			root.update()	#i dont use update_idletasks, because update refreshes everything. This is needed, when the window was not visible and is again.
#		except Exception:
#			print("Terminating")
#			break
			

def quick_update():
	global time_remain
	global time_war
	global time_updated_clock
	while not terminate:
		time.sleep(0.1)
		now = time.time()
		time_remain -= now - time_updated_clock 
		time_war -= now - time_updated_clock
		time_updated_clock = now
		turn_time.set(time.strftime("%M:%S", time.gmtime(time_remain)))
		turn_war_time.set(time.strftime("%H:%M:%S", time.gmtime(time_war)))
#		try:
#			root.update_idletasks()
#		except RuntimeError:
#			break

print("Starting interface")

try:
	quick_thread = threading.Thread(target=quick_update)
	update_thread = threading.Thread(target=update)
	force_update.set()
	quick_thread.start()
	update_thread.start()

	TK.mainloop()
except:
	pass
terminate = True
