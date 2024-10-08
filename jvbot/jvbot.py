import os
import yaml
import shutil
import pickle as pkl
from natsort import natsorted
import csv
from datetime import datetime
from tqdm import tqdm
from frgtools import jv


MODULE_DIR = os.path.dirname(__file__)
TRAY_VERSIONS_DIR = os.path.join(MODULE_DIR, "tray_versions")
AVAILABLE_VERSIONS = {
    os.path.splitext(f)[0]: os.path.join(TRAY_VERSIONS_DIR, f)
    for f in os.listdir(TRAY_VERSIONS_DIR)
    if ".yaml" in f
}

from jvbot.hardware.gantry import Gantry
from jvbot.hardware.control3 import Control_Keithley 
from jvbot.hardware.tray import Tray


class Control:
    def __init__(self, area=0.07, savedir="."):
        print('deniz 9/9/22')
        self.area = area  # cm2
        self.pause = 0.05
        self.control_keithley = Control_Keithley() ## control_keithley class communicates with keithley code
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
        self.gantry.moveto([55,24,30])
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

    def scan_cell(self, name, vmin, vmax, direction = 'fwdrev',  vsteps = 50, light = True, preview = True): 
        
        self.control_keithley.jv(name, direction, vmin, vmax)
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
        retry=False
        ## Added the necessary arguments here
    ):
        if final_slot is not None:
            allslots = natsorted(list(self.tray._coordinates.keys()))
            final_idx = allslots.index(final_slot)
            slots = allslots[: final_idx + 1]
        if slots is None:
            raise ValueError("Either final_slot or slots must be specified!")
        
        if retry == True:
            i = 0
            os.mkdir("retries")
            os.chdir("retries")
            jitter_list = [[0,0.5,1],[0.5,0,1],[0,0,2],[0,0.5,2]]
            j = 0
            for slot in tqdm(slots, desc="Scanning Tray"):
                self.gantry.moveto(self.tray(slot)+jitter_list[j])
                name_jv = "x"+str(self.position_to_number(slot)).zfill(2)+"_P1_S"+str(j+2)
                i = i+1
                name = name_jv
                self.control_keithley.jv(name, direction, vmin, vmax) 

        else:
            i = 0
            for slot in tqdm(slots, desc="Scanning Tray"):
                self.gantry.moveto(self.tray(slot))
                name_keithley = "x"+str(i+1).zfill(2)+"_P1_S1"
                i = i+1
                name = name_keithley
                self.control_keithley.jv(name, direction, vmin, vmax) 

        self.gantry.movetoload()
        self.copy_rename_csv()
        retry_slots = self.flag_function()
        #if retry is not True:
        #    self.scan_tray(tray_version,direction,vmin,vmax,vsteps = 50, slots = retry_slots, retry = True)

    
    def position_to_number(self, position):
        try:
            row, column = position[0], int(position[1:])
            if 'A' <= row <= 'H' and 1 <= column <= 4:
                return (ord(row) - ord('A')) * 4 + column
        except ValueError:
            pass
        return "Invalid input"



    def numbers_to_positions(self, numbers):
        if not all(1 <= num <= 32 for num in numbers):
            return ["Invalid Number" for num in numbers]
        
        row_labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        column_labels = ['1', '2', '3', '4']
        
        positions = []
        
        for number in numbers:
            row_index = (number - 1) // len(column_labels)
            column_index = (number - 1) % len(column_labels)
            positions.append(f"{row_labels[row_index]}{column_labels[column_index]}")
        
        positions = list(set(positions))
        return(positions)

   


    def flag_function(self):
            rawdf = jv.jv_metrics_pkl(rootdir=os.getcwd(), pce_cutoff=None, voc_cutoff=None, export_raw=True, area=.07) #.21
            print(rawdf[['name','pixel','repeat','direction','pce','ff','voc','jsc','rsh','rs']].sort_values(by = ['name'], ascending = True))
 
            column_ranges = {
                'pce': (5, 25),  # Range for Column1
                'ff': (50, 100)   # Range for Column2
            }

            # Create a list of row names where values do not fall within the specified range for each column
            abnormal_rows = rawdf[
                (rawdf['pce'] < column_ranges['pce'][0]) |
                (rawdf['pce'] > column_ranges['pce'][1]) |
                (rawdf['ff'] < column_ranges['ff'][0]) |
                (rawdf['ff'] > column_ranges['ff'][1])
            ]['name'].tolist()

            abnormal_rows_int = [int(x) for x in abnormal_rows]

            print("Row names with abnormal data for each column:")
            print(abnormal_rows_int)
            #return(len(abnormal_rows_int))
             # Example usage:
            
            positions = self.numbers_to_positions(abnormal_rows_int)
            print(positions)
            return(positions)

    def copy_rename_csv(self):

        # Get the current working directory
        current_directory = os.getcwd()
        os.mkdir("light")

        # List all files in the current directory
        files = os.listdir(current_directory)

        # Filter only the CSV files
        csv_files = [file for file in files if file.endswith('.csv')]

        # Iterate through CSV files and make a copy with modified names
        for csv_file in csv_files:
             # Extract the filename without extension
             filename, extension = os.path.splitext(csv_file)
                    
             # Remove the first character from the filename
             new_filename = filename[1:] + extension
                    
             # Construct the old and new file paths
             old_path = os.path.join(current_directory, csv_file)
             new_path = os.path.join(current_directory+"\\light", new_filename)
                    
             # Make a copy with the modified name
             shutil.copy2(old_path, new_path)

        print("Copies of CSV files with modified names created successfully.")

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
