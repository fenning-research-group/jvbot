import os
import yaml
from natsort import natsorted
import csv
from datetime import datetime
from tqdm import tqdm

MODULE_DIR = os.path.dirname(__file__)
TRAY_VERSIONS_DIR = os.path.join(MODULE_DIR, "tray_versions")
AVAILABLE_VERSIONS = {
    os.path.splitext(f)[0]: os.path.join(TRAY_VERSIONS_DIR, f)
    for f in os.listdir(TRAY_VERSIONS_DIR)
    if ".yaml" in f
}

from jvbot.hardware.gantry import Gantry
from jvbot.hardware.keithley import Keithley
from jvbot.hardware.tray import Tray

class Control:
    def __init__(self, area=0.048, savedir="."):

        self.area = area  # cm2
        self.pause = 0.05
        self.keithley = Keithley()
        self.gantry = Gantry()
        self.savedir = savedir

    def set_tray(self, version:str, calibrate:bool = False):
        self.tray = Tray(version=version, gantry=self.gantry, calibrate=calibrate)

    def _save_to_csv(self, slot, vmeas, i, direction):
        fpath = os.path.join(self.savedir, f"{slot}_{direction}.csv")

        j = i / self.area
        p = j * vmeas
        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(fpath, "w", newline="") as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow(["Datetime", dt])
            writer.writerow(["Slot", slot])
            writer.writerow(["Area (cm2)", self.area])
            writer.writerow(
                [
                    "Voltage Measured (V)",
                    "Current Density (mA/cm2)",
                    "Current (mA)",
                    "Power Density (mW/cm2)",
                ]
            )
            for line in zip(vmeas, j, i, p):
                writer.writerow(line)

    def scan_cell(self, slot, vmin, vmax, steps=51, direction="forward"):
        direction_options = ["forward", "reverse", "both"]
        if direction not in direction_options:
            raise ValueError("direction must be one of {}".format(direction_options))

        if direction == "forward":
            if vmin > vmax:
                vmin, vmax = vmax, vmin
            vmeas, i = self.keithley.iv(vmin, vmax, steps)
            self._save_to_csv(slot, vmeas=vmeas, i=i, direction=direction)

        if direction == "reverse":
            if vmin < vmax:
                vmin, vmax = vmax, vmin
            vmeas, i = self.keithley.iv(vmin, vmax, steps)
            self._save_to_csv(slot, vmeas=vmeas, i=i, direction=direction)

        if direction == "both":
            self.scan_cell(slot, vmin, vmax, steps, "reverse")
            self.scan_cell(slot, vmin, vmax, steps, "forward")

    def scan_tray(
        self,
        vmin,
        vmax,
        steps=51,
        direction="both",
        repeat_scans = 1,
        initial_slot = None,
        final_slot=None,
        slots=None,
    ):
        if final_slot is not None:
            allslots = natsorted(list(self.tray._coordinates.keys()))
            final_idx = allslots.index(final_slot)
            if initial_slot is not None:
                initial_idx = allslots.index(initial_slot)
                slots = allslots[initial_idx:final_idx+1]
            else:
                slots = allslots[:final_idx+1]

        if slots is None:
            raise ValueError("Either final_slot or slots must be specified!")

        for slot in tqdm(slots, desc="Scanning Tray"):
            self.gantry.moveto(self.tray(slot))
            for i in range(repeat_scans):
                name = f"{slot}_{i}"
                self.scan_cell(name, vmin, vmax, steps, direction)
        self.gantry.movetoload()