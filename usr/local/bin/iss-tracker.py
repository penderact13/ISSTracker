#!/usr/bin/env python3

import tkinter as tk
from tkinter import Canvas
import requests
from sgp4.api import Satrec, WGS72, jday
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

def get_pi_location():
    try:
        response = requests.get("http://ip-api.com/json/")
        data = response.json()
        return data['lat'], data['lon']
    except:
        return 0, 0

def fetch_iss_tle():
    url = "https://celestrak.org/NORAD/elements/stations.txt"
    tle_data = requests.get(url).text
    lines = tle_data.split('\n')
    for i, line in enumerate(lines):
        if "ISS (ZARYA)" in line:
            return lines[i+1], lines[i+2]
    return None, None

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

        self.lat, self.lon = get_pi_location()
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

        x, y = latlon_to_xy(self.lat, self.lon, 800, 400)
        self.canvas.create_oval(x-4, y-4, x+4, y+4, fill="red", tags="markers")

        if self.satellite:
            now = datetime.utcnow() + self.time_offset
            jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond/1e6)
            e, pos, vel = self.satellite.sgp4(jd, fr)
            iss_lat = math.degrees(math.asin(pos[2]/(WGS72.radiuse + pos[0]**2 + pos[1]**2 + pos[2]**2)**0.5))
            iss_lon = math.degrees(math.atan2(pos[1], pos[0]))
            if iss_lon > 180:
                iss_lon -= 360

            iss_x, iss_y = latlon_to_xy(iss_lat, iss_lon, 800, 400)
            self.canvas.create_oval(iss_x-4, iss_y-4, iss_x+4, iss_y+4, fill="purple", tags="markers")

            for mins in range(5, 90, 5):
                future_time = now + timedelta(minutes=mins)
                jd_fut, fr_fut = jday(
                    future_time.year, future_time.month, future_time.day,
                    future_time.hour, future_time.minute,
                    future_time.second + future_time.microsecond / 1e6
                )
                e_fut, pos_fut, vel_fut = self.satellite.sgp4(jd_fut, fr_fut)
                lat_fut = math.degrees(math.asin(pos_fut[2]/(WGS72.radiuse + pos_fut[0]**2 + pos_fut[1]**2 + pos_fut[2]**2)**0.5))
                lon_fut = math.degrees(math.atan2(pos_fut[1], pos_fut[0]))
                if lon_fut > 180:
                    lon_fut -= 360
                path_x, path_y = latlon_to_xy(lat_fut, lon_fut, 800, 400)
                self.canvas.create_oval(path_x-1, path_y-1, path_x+1, path_y+1, fill="blue", tags="markers")

        self.root.after(1000, self.update_display)

    def go_forward(self, event):
        self.time_offset += timedelta(minutes=10)

    def go_back(self, event):
        self.time_offset -= timedelta(minutes=10)

    def reset_time(self, event):
        self.time_offset = timedelta(seconds=0)

if __name__ == "__main__":
    root = tk.Tk()
    app = ISSTrackerApp(root)
    root.mainloop()
