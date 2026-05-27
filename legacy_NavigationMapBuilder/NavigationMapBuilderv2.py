import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import json
import os
import math
from PIL import Image, ImageTk, ImageDraw

class NavigationMapBuilder:
    def __init__(self, root):
        self.root = root
        self.root.title("Navigation Map Builder")
        self.root.geometry("1200x800")
        self.waypoints = []
        self.routes = []
        self.current_tool = "select"
        self.map_image = None
        self.photo_image = None
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.waypoint_counter = 0
        self._route_start = None
        self._pan_x = 0
        self._pan_y = 0
        self.setup_ui()

    def setup_ui(self):
        self.root.configure(bg="#2b2b2b")
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New", command=self.new_map)
        file_menu.add_command(label="Open Image...", command=self.open_image)
        file_menu.add_separator()
        file_menu.add_command(label="Save Map...", command=self.save_map)
        file_menu.add_command(label="Load Map...", command=self.load_map)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        self.root.config(menu=menubar)

        toolbar = tk.Frame(self.root, bg="#3c3c3c", height=45)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        toolbar.pack_propagate(False)

        tk.Label(toolbar, text="Tool:", bg="#3c3c3c", fg="white").pack(side=tk.LEFT, padx=(10,4), pady=10)
        self.tool_var = tk.StringVar(value="select")
        tools = [("Select","select"),("Waypoint","waypoint"),("Route","route"),("Delete","delete")]
        for label, val in tools:
            tk.Radiobutton(
                toolbar, text=label, variable=self.tool_var, value=val,
                bg="#3c3c3c", fg="white", selectcolor="#555",
                activebackground="#3c3c3c", activeforeground="white"
            ).pack(side=tk.LEFT, padx=4)

        tk.Button(toolbar, text="Clear All", command=self.clear_all,
                  bg="#c0392b", fg="white", relief=tk.FLAT, padx=8).pack(side=tk.RIGHT, padx=8, pady=6)
        tk.Button(toolbar, text="Export JSON", command=self.save_map,
                  bg="#27ae60", fg="white", relief=tk.FLAT, padx=8).pack(side=tk.RIGHT, padx=4, pady=6)

        main = tk.Frame(self.root, bg="#2b2b2b")
        main.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(main, bg="#1e1e1e", cursor="crosshair")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<MouseWheel>", self.on_scroll)
        self.canvas.bind("<B2-Motion>", self.on_pan)
        self.canvas.bind("<Button-2>", self.start_pan)

        panel = tk.Frame(main, bg="#2b2b2b", width=220)
        panel.pack(side=tk.RIGHT, fill=tk.Y)
        panel.pack_propagate(False)

        tk.Label(panel, text="Waypoints", bg="#2b2b2b", fg="#aaa",
                 font=("Arial",10,"bold")).pack(pady=(12,4))
        self.wp_listbox = tk.Listbox(panel, bg="#1e1e1e", fg="white",
                                      selectbackground="#3498db", height=15)
        self.wp_listbox.pack(fill=tk.X, padx=8)

        tk.Label(panel, text="Routes", bg="#2b2b2b", fg="#aaa",
                 font=("Arial",10,"bold")).pack(pady=(12,4))
        self.rt_listbox = tk.Listbox(panel, bg="#1e1e1e", fg="white",
                                      selectbackground="#3498db", height=8)
        self.rt_listbox.pack(fill=tk.X, padx=8)

        self.status = tk.StringVar(value="Ready - select a tool and click the canvas")
        tk.Label(self.root, textvariable=self.status, bg="#1a1a1a", fg="#aaa",
                 anchor="w", padx=8).pack(side=tk.BOTTOM, fill=tk.X)

    def on_click(self, event):
        tool = self.tool_var.get()
        cx, cy = event.x, event.y
        if tool == "waypoint":
            self.waypoint_counter += 1
            wp = {"id": self.waypoint_counter, "name": "WP" + str(self.waypoint_counter),
                  "x": cx, "y": cy, "color": "#e74c3c"}
            self.waypoints.append(wp)
            self.draw_waypoint(wp)
            self.wp_listbox.insert(tk.END, wp["name"] + " (" + str(cx) + "," + str(cy) + ")")
            self.status.set("Waypoint " + wp["name"] + " added at (" + str(cx) + "," + str(cy) + ")")
        elif tool == "route":
            hit = self.find_nearest_waypoint(cx, cy)
            if hit:
                if self._route_start is None:
                    self._route_start = hit
                    self.status.set("Route start: " + hit["name"] + " - click another waypoint")
                else:
                    route = {"from": self._route_start["id"], "to": hit["id"]}
                    self.routes.append(route)
                    self.draw_route(self._route_start, hit)
                    self.rt_listbox.insert(tk.END, self._route_start["name"] + " -> " + hit["name"])
                    dist = math.sqrt((hit["x"]-self._route_start["x"])**2 +
                                     (hit["y"]-self._route_start["y"])**2)
                    self.status.set("Route: " + self._route_start["name"] + " -> " + hit["name"] + " (" + str(round(dist,1)) + "px)")
                    self._route_start = None
        elif tool == "delete":
            hit = self.find_nearest_waypoint(cx, cy)
            if hit:
                self.waypoints = [w for w in self.waypoints if w["id"] != hit["id"]]
                self.routes = [r for r in self.routes
                               if r["from"] != hit["id"] and r["to"] != hit["id"]]
                self.redraw()
                self.status.set("Deleted " + hit["name"])

    def find_nearest_waypoint(self, x, y, threshold=20):
        best, best_d = None, threshold
        for wp in self.waypoints:
            d = math.sqrt((wp["x"]-x)**2 + (wp["y"]-y)**2)
            if d < best_d:
                best, best_d = wp, d
        return best

    def draw_waypoint(self, wp):
        x, y, r = wp["x"], wp["y"], 8
        self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=wp["color"],
                                outline="white", width=2, tags="wp")
        self.canvas.create_text(x, y-16, text=wp["name"], fill="white",
                                font=("Arial",8), tags="wp")

    def draw_route(self, a, b):
        self.canvas.create_line(a["x"], a["y"], b["x"], b["y"],
                                fill="#3498db", width=2, arrow=tk.LAST, tags="rt")

    def redraw(self):
        self.canvas.delete("wp")
        self.canvas.delete("rt")
        if self.photo_image:
            self.canvas.create_image(self.offset_x, self.offset_y,
                                     anchor="nw", image=self.photo_image)
        wp_map = {w["id"]: w for w in self.waypoints}
        for r in self.routes:
            if r["from"] in wp_map and r["to"] in wp_map:
                self.draw_route(wp_map[r["from"]], wp_map[r["to"]])
        for wp in self.waypoints:
            self.draw_waypoint(wp)
        self.wp_listbox.delete(0, tk.END)
        for wp in self.waypoints:
            self.wp_listbox.insert(tk.END, wp["name"] + " (" + str(wp["x"]) + "," + str(wp["y"]) + ")")
        self.rt_listbox.delete(0, tk.END)
        wp_map2 = {w["id"]: w["name"] for w in self.waypoints}
        for r in self.routes:
            fn = wp_map2.get(r["from"], "?")
            tn = wp_map2.get(r["to"], "?")
            self.rt_listbox.insert(tk.END, fn + " -> " + tn)

    def on_scroll(self, event):
        factor = 1.1 if event.delta > 0 else 0.9
        self.scale_factor *= factor
        self.status.set("Zoom: " + str(round(self.scale_factor, 2)) + "x")

    def start_pan(self, event):
        self._pan_x = event.x
        self._pan_y = event.y

    def on_pan(self, event):
        dx = event.x - self._pan_x
        dy = event.y - self._pan_y
        self.canvas.move("all", dx, dy)
        self.offset_x += dx
        self.offset_y += dy
        self._pan_x = event.x
        self._pan_y = event.y

    def open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if path:
            img = Image.open(path)
            self.map_image = img
            self.photo_image = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self.photo_image)
            self.status.set("Loaded: " + os.path.basename(path))

    def new_map(self):
        if messagebox.askyesno("New Map", "Clear everything and start fresh?"):
            self.clear_all()
            self.map_image = None
            self.photo_image = None
            self.canvas.delete("all")

    def clear_all(self):
        self.waypoints.clear()
        self.routes.clear()
        self.waypoint_counter = 0
        self._route_start = None
        self.canvas.delete("wp")
        self.canvas.delete("rt")
        self.wp_listbox.delete(0, tk.END)
        self.rt_listbox.delete(0, tk.END)
        self.status.set("Cleared")

    def save_map(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Map", "*.json"), ("All", "*.*")])
        if path:
            data = {"version": "1.0", "waypoints": self.waypoints, "routes": self.routes}
            with open(path, "w") as fh:
                json.dump(data, fh, indent=2)
            self.status.set("Saved: " + os.path.basename(path))
            messagebox.showinfo("Saved", "Map saved to: " + path)

    def load_map(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON Map", "*.json"), ("All", "*.*")])
        if path:
            with open(path) as fh:
                data = json.load(fh)
            self.waypoints = data.get("waypoints", [])
            self.routes = data.get("routes", [])
            if self.waypoints:
                self.waypoint_counter = max(w["id"] for w in self.waypoints)
            self.redraw()
            self.status.set("Loaded: " + os.path.basename(path))

if __name__ == "__main__":
    root = tk.Tk()
    app = NavigationMapBuilder(root)
    root.mainloop()
