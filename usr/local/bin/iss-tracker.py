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
import threading

class ISSTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ISS Tracker")
        self.canvas = Canvas(root, width=800, height=400, bg="black")
        self.canvas.pack()

        self.image = self.generate_map().resize((800, 400))
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

        self.time_offset = timedelta(seconds=0)
        self.satellite = None
        self.last_tle_update = None

        self.load_tle()
        self.schedule_tle_refresh()

        self.root.bind("<Left>", self.go_back)
        self.root.bind("<Right>", self.go_forward)
        self.root.bind("<space>", self.reset_time)

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
                    self.satellite = Satrec.twoline2rv(tle1, tle2)
                    self.last_tle_update = datetime.utcnow()
                    print("TLE updated:", self.last_tle_update)
                    return
        except Exception as e:
            print("Error updating TLE:", e)

    def schedule_tle_refresh(self):
        # Refresh TLE every 10 minutes
        def tle_updater():
            while True:
                now = datetime.utcnow()
                if self.last_tle_update is None or (now - self.last_tle_update).total_seconds() > 600:
                    self.load_tle()
                threading.Event().wait(60)
        threading.Thread(target=tle_updater, daemon=True).start()

    def update_display(self):
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)

        now = datetime.utcnow() + self.time_offset
        jd, fr = jday(now.year, now.month, now.day, now.hour, now.minute, now.second + now.microsecond/1e6)
        e, pos, vel = self.satellite.sgp4(jd, fr)
        lat, lon = self.eci_to_latlon(pos, jd)
        iss_x, iss_y = self.latlon_to_xy(lat, lon, 800, 400)

        # Draw ISS current position
        self.canvas.create_oval(iss_x-4, iss_y-4, iss_x+4, iss_y+4, fill="purple", tags="iss")

        # Draw current orbit path
        path_coords = []
        prev_lon = None
        for mins in range(-10, 90, 2):
            future_time = now + timedelta(minutes=mins)
            jd_fut, fr_fut = jday(future_time.year, future_time.month, future_time.day,
                                   future_time.hour, future_time.minute,
                                   future_time.second + future_time.microsecond/1e6)
            e_fut, pos_fut, vel_fut = self.satellite.sgp4(jd_fut, fr_fut)
            lat_fut, lon_fut = self.eci_to_latlon(pos_fut, jd_fut)

            if prev_lon is not None:
                lon_fut = self.smooth_longitude(prev_lon, lon_fut)
            prev_lon = lon_fut

            x, y = self.latlon_to_xy(lat_fut, lon_fut, 800, 400)
            path_coords.append((x, y))

        for i in range(len(path_coords)-1):
            self.canvas.create_line(path_coords[i][0], path_coords[i][1],
                                    path_coords[i+1][0], path_coords[i+1][1],
                                    fill="blue", width=2)

        # Draw current UTC time
        self.canvas.create_text(400, 20, text=now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                                 font=("Arial", 16, "bold"), fill="white")

        self.root.after(1000, self.update_display)

    def eci_to_latlon(self, pos, jd):
        T = (jd - 2451545.0) / 36525.0
        GMST = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * T**2 - T**3 / 38710000.0
        GMST = GMST % 360.0
        theta = math.radians(GMST)

        x = pos[0]*math.cos(theta) + pos[1]*math.sin(theta)
        y = -pos[0]*math.sin(theta) + pos[1]*math.cos(theta)
        z = pos[2]

        r = math.sqrt(x**2 + y**2 + z**2)
        lat = math.degrees(math.asin(z / r))
        lon = math.degrees(math.atan2(y, x))
        if lon > 180:
            lon -= 360
        return lat, lon

    def latlon_to_xy(self, lat, lon, width, height):
        x = (lon + 180) * (width / 360)
        y = (90 - lat) * (height / 180)
        return x, y

    def smooth_longitude(self, prev_lon, curr_lon):
        delta = curr_lon - prev_lon
        if delta > 180:
            curr_lon -= 360
        elif delta < -180:
            curr_lon += 360
        return curr_lon

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
