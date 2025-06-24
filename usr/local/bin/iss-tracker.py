#!/usr/bin/env python3

import tkinter as tk
from tkinter import Canvas
import requests
from sgp4.api import Satrec, jday
from datetime import datetime, timedelta
import math
import cartopy.crs as ccrs
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
import io

def generate_map():
    fig = plt.figure(figsize=(8, 4))
    ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
    ax.set_global()
    ax.stock_img()
    ax.coastlines()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close(fig)
    return Image.open(buf)

def fetch_iss_tle():
    url = "https://celestrak.org/NORAD/elements/stations.txt"
    tle_data = requests.get(url).text
    lines = tle_data.split('\n')
    for i, line in enumerate(lines):
        if "ISS (ZARYA)" in line:
            return lines[i+1], lines[i+2]
    return None, None

def eci_to_latlon(pos, jd):
    # Calculate GMST (Greenwich Mean Sidereal Time)
    T = (jd - 2451545.0) / 36525.0
    GMST = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * T**2 - T**3 / 38710000.0
    GMST = GMST % 360.0
    theta = math.radians(GMST)

    # ECI to ECEF rotation
    x = pos[0]*math.cos(theta) + pos[1]*math.sin(theta)
    y = -pos[0]*math.sin(theta) + pos[1]*math.cos(theta)
    z = pos[2]

    # Convert to lat/lon
    r = math.sqrt(x**2 + y**2 + z**2)
    lat = math.degrees(math.asin(z / r))
    lon = math.degrees(math.atan2(y, x))
    if lon > 180:
        lon -= 360
    return lat, lon

def latlon_to_xy(lat, lon, width, height):
    x = (lon + 180) * (width / 360)
    y = (90 - lat) * (height / 180)
    return x, y

class ISSTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ISS Tracker")
        self.canvas = Canvas(root, width=800, height=400)
        self.canvas.pack()

        self.image = generate_map().resize((800, 400))
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

        self.load_tle()

        self.time_offset = timedelta(seconds=0)

        self.root.bind("<Left>", self.go_back)
        self.root.bind("<Right>", self.go_forward)
        self.root.bind("<space>", self.reset_time)

        self.update_display()

    def load_tle(self):
        tle1, tle2 = fetch_iss_tle()
        if tle1 and tle2:
            self.satellite = Satrec.twoline2rv(tle1, tle2)
        else:
            self.satellite = None

    def update_display(self):
        self.canvas.delete("markers")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

        now = datetime.utcnow() + self.time_offset
        jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond/1e6)

        # Current ISS position
        e, pos, vel = self.satellite.sgp4(jd, fr)
        lat, lon = eci_to_latlon(pos, jd)
        iss_x, iss_y = latlon_to_xy(lat, lon, 800, 400)
        self.canvas.create_oval(iss_x-4, iss_y-4, iss_x+4, iss_y+4, fill="purple", tags="markers")

        # Future path
        path_coords = []
        for mins in range(0, 90, 2):
            future_time = now + timedelta(minutes=mins)
            jd_fut, fr_fut = jday(
                future_time.year, future_time.month, future_time.day,
                future_time.hour, future_time.minute,
                future_time.second + future_time.microsecond / 1e6
            )
            e_fut, pos_fut, vel_fut = self.satellite.sgp4(jd_fut, fr_fut)
            lat_fut, lon_fut = eci_to_latlon(pos_fut, jd_fut)
            path_x, path_y = latlon_to_xy(lat_fut, lon_fut, 800, 400)
            path_coords.append((path_x, path_y))

        # Draw blue path line
        for i in range(len(path_coords)-1):
            self.canvas.create_line(path_coords[i][0], path_coords[i][1],
                                    path_coords[i+1][0], path_coords[i+1][1],
                                    fill="blue", width=2, tags="markers")

        # Draw time label
        self.canvas.create_text(400, 20, text=now.strftime("%Y-%m-%d %H:%M:%S UTC"), font=("Arial", 16), fill="white", tags="markers")

        self.root.after(1000, self.update_display)

    def go_forward(self, event):
        self.time_offset += timedelta(minutes=2)

    def go_back(self, event):
        self.time_offset -= timedelta(minutes=2)

    def reset_time(self, event):
        self.time_offset = timedelta(seconds=0)

if __name__ == "__main__":
    root = tk.Tk()
    app = ISSTrackerApp(root)
    root.mainloop()
