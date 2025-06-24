# ISSTracker
An ISS tracker app for the RPi.
## Instalation
To install, download the installer.sh from the releases page onto your RPi's home directory. Then run the following commands:
```bash
chmod +x installer.sh
```
Then run it:
```bash
./installer.sh
```
Everything will be installed from there.
## Deletion
Just run these to delete:
```bash
sudo rm /usr/local/bin/iss-tracker.py
sudo rm /home/pi/iss-tracker.deb
sudo rm -r /home/pi/ISSTracker
```
or
```bash
sudo rm -f /usr/local/bin/iss-tracker.py /home/pi/iss-tracker.deb && sudo rm -rf /home/pi/ISSTracker
```
## Preview
...
