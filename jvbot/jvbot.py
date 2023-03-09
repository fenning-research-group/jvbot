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
from jvbot.hardware.control3 import Control_Sean ###Changed the name of the class so it doesn't clash with Control in jvbot file, importing control 3
from jvbot.hardware.tray import Tray


class Control:
    def __init__(self, area=0.07, savedir="."):
        print('deniz 9/9/22')
        self.area = area  # cm2
        self.pause = 0.05
        self.control_sean = Control_Sean() ## control_sean is now the variable for controlling the keithley
        self.gantry = Gantry()
        self.savedir = savedir

    def open_shutter(self):
        # self.shutter.write(b'1')
        # self._shutteropen = True
        return

    def close_shutter(self):
        # self.shutter.write(b'0')
        # self._shutteropen = False
        return

    def set_tray(self, version:str, calibrate:bool = False):
        self.tray = Tray(version=version, gantry=self.gantry, calibrate=calibrate)

    def _save_to_csv(self, slot, vmeas, i, direction):
        fpath = os.path.join(self.savedir, f"{slot}_{direction}.csv")
        # i = i
        # v = v
        # i = i
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

    def scan_cell(self, name, vmin, vmax, direction = 'fwdrev',  vsteps = 50, light = True, preview = True): ##Making it so that the jv() function in Seans code gets what it needs
        
        self.control_sean.jv(name, direction, vmin, vmax, vsteps = 50, light = True, preview = True)
        """
            Conducts a JV scan, previews data, saves file
            
            Args:
                name (string): name of device
                direction (string): direction -- fwd, rev, fwdrev, or revfwd
                vmin (float): start voltage for JV sweep (V)
                xmax (float): end voltage for JV sweep (V)
                vsteps (int = 50): number of voltage steps between max and min
                light (boolean = True): boolean to describe status of light
                preview (boolean = True): boolean to determine if data is plotted
        """
        """
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
        """

        

    def scan_tray(
        self,
        tray_version,
        direction,
        vmin,
        vmax,
        vsteps = 50,
        final_slot=None,
        slots=None,
        ## Added the necessary arguments here
    ):
        if final_slot is not None:
            allslots = natsorted(list(self.tray._coordinates.keys()))
            final_idx = allslots.index(final_slot)
            slots = allslots[: final_idx + 1]
        if slots is None:
            raise ValueError("Either final_slot or slots must be specified!")

        for slot in tqdm(slots, desc="Scanning Tray"):
            self.gantry.moveto(self.tray(slot))
            name = slot
            # print("this is vmin and vmax:", vmin,vmax)
            self.control_sean.jv(name, direction, vmin, vmax) ## Calls Sean's code and that handles the rest
        self.gantry.movetoload()

    # def _preview(self, v, j, label):
    #     def handle_close(evt, self):
    #         self.__previewFigure = None
    #         self.__previewAxes = None

    #     if (
    #         self.__previewFigure is None
    #     ):  # preview window is not created yet, lets make it
    #         plt.ioff()
    #         self.__previewFigure, self.__previewAxes = plt.subplots()
    #         self.__previewFigure.canvas.mpl_connect(
    #             "close_event", lambda x: handle_close(x, self)
    #         )  # if preview figure is closed, lets clear the figure/axes handles so the next preview properly recreates the handles
    #         plt.ion()
    #         plt.show()

    #     # for ax in self.__previewAxes:   #clear the axes
    #     #     ax.clear()
    #     self.__previewAxes.plot(v, j, label=label)
    #     self.__previewAxes.legend()
    #     self.__previewFigure.canvas.draw()
    #     self.__previewFigure.canvas.flush_events()
    #     time.sleep(1e-4)  # pause allows plot to update during series of measurements


### OLD CODE STARTS HERE ###

"""
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
    def __init__(self, area=0.07, savedir="."):
        print('deniz 10/05/22')
        self.area = area  # cm2
        self.pause = 0.05
        self.keithley = Keithley()
        self.gantry = Gantry()
        self.savedir = savedir
        #self.gantry.gohome()

    def open_shutter(self):
        # self.shutter.write(b'1')
        # self._shutteropen = True
        return

    def close_shutter(self):
        # self.shutter.write(b'0')
        # self._shutteropen = False
        return

    def set_tray(self, version:str, calibrate:bool = False):
        self.tray = Tray(version=version, gantry=self.gantry, calibrate=calibrate)

    def _save_to_csv(self, slot, vmeas, i, direction):
        fpath = os.path.join(self.savedir, f"{slot}_{direction}.csv")
        # i = i
        # v = v
        # i = i
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
        tray_version,
        vmin,
        vmax,
        steps=5,
        direction="both",
        final_slot=None,
        slots=None,
    ):
        if final_slot is not None:
            allslots = natsorted(list(self.tray._coordinates.keys()))
            print('in function scan_tray: tray._coordinates =',self.tray._coordinates)
            final_idx = allslots.index(final_slot)
            print('in function scan tray: final_idx =', final_idx)
            slots = allslots[: final_idx + 1]
            print(' in function scan tray: slots =', slots)
        if slots is None:
            raise ValueError("Either final_slot or slots must be specified!")

        for slot in tqdm(slots, desc="Scanning Tray"):
            print(slot)
            self.gantry.moveto(self.tray(slot))
            self.scan_cell(slot, vmin, vmax, steps, direction)
        self.gantry.movetoload()

    # def _preview(self, v, j, label):
    #     def handle_close(evt, self):
    #         self.__previewFigure = None
    #         self.__previewAxes = None

    #     if (
    #         self.__previewFigure is None
    #     ):  # preview window is not created yet, lets make it
    #         plt.ioff()
    #         self.__previewFigure, self.__previewAxes = plt.subplots()
    #         self.__previewFigure.canvas.mpl_connect(
    #             "close_event", lambda x: handle_close(x, self)
    #         )  # if preview figure is closed, lets clear the figure/axes handles so the next preview properly recreates the handles
    #         plt.ion()
    #         plt.show()

    #     # for ax in self.__previewAxes:	#clear the axes
    #     # 	ax.clear()
    #     self.__previewAxes.plot(v, j, label=label)
    #     self.__previewAxes.legend()
    #     self.__previewFigure.canvas.draw()
    #     self.__previewFigure.canvas.flush_events()
    #     time.sleep(1e-4)  # pause allows plot to update during series of measurements
    """
