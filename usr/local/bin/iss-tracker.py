#!/usr/bin/env python3

import tkinter as tk
from tkinter import Canvas
import requests
from skyfield.api import load, EarthSatellite
from datetime import datetime, timedelta
import math
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
import io
import threading

class ISSTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ISS Tracker")
        self.width = 800
        self.height = 400

        self.canvas = Canvas(root, width=self.width, height=self.height, bg="black")
        self.canvas.pack(fill="both", expand=True)

        self.original_map = self.generate_map()
        self.tk_image = None

        self.ts = load.timescale()
        self.satellite = None
        self.last_tle_update = None
        self.time_offset = timedelta(seconds=0)

        self.load_tle()
        self.schedule_tle_refresh()

        self.root.bind("<Left>", self.go_back)
        self.root.bind("<Right>", self.go_forward)
        self.root.bind("<space>", self.reset_time)

        self.root.bind("<Configure>", self.resize)
        self.update_display()

    def generate_map(self):
        fig = plt.figure(figsize=(8, 4))
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
        ax.set_global()
        ax.stock_img()
        ax.coastlines()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return Image.open(buf)

    def load_tle(self):
        try:
            url = "https://celestrak.org/NORAD/elements/stations.txt"
            tle_data = requests.get(url, timeout=10).text
            lines = tle_data.split('\n')
            for i, line in enumerate(lines):
                if "ISS (ZARYA)" in line:
                    tle1 = lines[i+1].strip()
                    tle2 = lines[i+2].strip()
                    self.satellite = EarthSatellite(tle1, tle2, 'ISS (ZARYA)', self.ts)
                    self.last_tle_update = datetime.utcnow()
                    print("TLE updated:", self.last_tle_update)
                    return
        except Exception as e:
            print("Error updating TLE:", e)

    def schedule_tle_refresh(self):
        def tle_updater():
            while True:
                now = datetime.utcnow()
                if self.last_tle_update is None or (now - self.last_tle_update).total_seconds() > 600:
                    self.load_tle()
                threading.Event().wait(60)
        threading.Thread(target=tle_updater, daemon=True).start()

    def resize(self, event):
        self.width = event.width
        self.height = event.height
        self.update_display()

    def update_display(self):
        self.canvas.delete("all")

        # Resize map image
        resized_image = self.original_map.resize((self.width, self.height))
        self.tk_image = ImageTk.PhotoImage(resized_image)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

        now = datetime.utcnow() + self.time_offset
        t_now = self.ts.utc(now)

        geocentric = self.satellite.at(t_now)
        subpoint = geocentric.subpoint()
        lat, lon = subpoint.latitude.degrees, subpoint.longitude.degrees
        iss_x, iss_y = self.latlon_to_xy(lat, lon, self.width, self.height)

        self.canvas.create_oval(iss_x-4, iss_y-4, iss_x+4, iss_y+4, fill="purple", tags="iss")

        # Draw upcoming path (next orbit)
        path_coords = []
        for mins in range(-10, 90, 1):  
            future_time = now + timedelta(minutes=mins)
            t_future = self.ts.utc(future_time)
            geocentric_future = self.satellite.at(t_future)
            subpoint_future = geocentric_future.subpoint()
            lat_fut, lon_fut = subpoint_future.latitude.degrees, subpoint_future.longitude.degrees
            x, y = self.latlon_to_xy(lat_fut, lon_fut, self.width, self.height)
            path_coords.append((x, y))

        for i in range(len(path_coords)-1):
            self.canvas.create_line(path_coords[i][0], path_coords[i][1],
                                    path_coords[i+1][0], path_coords[i+1][1],
                                    fill="blue", width=2)

        # Draw current UTC time
        self.canvas.create_text(self.width//2, 20, text=now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                                 font=("Arial", 16, "bold"), fill="white")

        self.root.after(100, self.update_display)

    def latlon_to_xy(self, lat, lon, width, height):
        x = (lon + 180) * (width / 360)
        y = (90 - lat) * (height / 180)
        return x, y

    def go_forward(self, event):
        self.time_offset += timedelta(minutes=1)

    def go_back(self, event):
        self.time_offset -= timedelta(minutes=1)

    def reset_time(self, event):
        self.time_offset = timedelta(seconds=0)

if __name__ == "__main__":
    root = tk.Tk()
    app = ISSTrackerApp(root)
    root.mainloop()
