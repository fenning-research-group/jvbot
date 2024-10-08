import os
import yaml
import numpy as np
from jvbot.hardware.gantry import Gantry

MODULE_DIR = os.path.dirname(__file__)
TRAY_VERSIONS_DIR = os.path.join(MODULE_DIR, "..", "tray_versions")
AVAILABLE_VERSIONS = {
    os.path.splitext(f)[0]: os.path.join(TRAY_VERSIONS_DIR, f)
    for f in os.listdir(TRAY_VERSIONS_DIR)
    if ".yaml" in f
}


class Tray:
    """
    General class for defining sample trays. Primary use is to calibrate the coordinate system of this workspace to
    the reference workspace to account for any tilt/rotation/translation in workspace mounting.
    """

    def __init__(self, version: str, gantry: Gantry, calibrate:bool = False):
        self._calibrated = False  # set to True after calibration routine has been run
        self.gantry = gantry
        self._load_version(version, calibrate=calibrate)  # generates grid of sample slot coordinates

        # coordinate system properties

    def _load_version(self, version, calibrate=False):
        if version not in AVAILABLE_VERSIONS:
            raise Exception(
                f'Invalid tray version "{version}".\n Available versions are: {list(AVAILABLE_VERSIONS.keys())}.'
            )
        with open(AVAILABLE_VERSIONS[version], "r") as f:
            constants = yaml.load(f, Loader=yaml.FullLoader)
        self.version = version
        self.pitch = (constants["xpitch"], constants["ypitch"])
        self.gridsize = (constants["numx"], constants["numy"])
        self.z_clearance = constants["z_clearance"]
        self.__generate_coordinates()

        if 'offset' in constants:
            self.offset = np.array([constants['offset']['x'], constants['offset']['y'], constants['offset']['z']])
            self.__calibrated = True
        else:
            print('No offset found in yaml file for this tray version, forcing calibration step.')
            calibrate = True
        if calibrate:
            self.calibrate()



    def __generate_coordinates(self):
        def letter(num):
            # converts number (0-25) to letter (A-Z)
            return chr(ord("A") + num)

        self._coordinates = {}
        self._ycoords = [
            letter(self.gridsize[1] - yidx - 1) for yidx in range(self.gridsize[1])
        ]  # lettering +y -> -y = A -> Z
        self._xcoords = [
            xidx + 1 for xidx in range(self.gridsize[0])
        ]  # numbering -x -> +x = 1 -> 100
        

        self.CALIBRATIONSLOT = None
        for yidx in range(self.gridsize[1]):  # y
            for xidx in range(self.gridsize[0]):  # x
                name = f"{self._ycoords[yidx]}{self._xcoords[xidx]}"
                self._coordinates[name] = np.array(
                    [                                
                            xidx * self.pitch[0],#-inst_offset[xidx+yidx][0],
                            yidx * self.pitch[1],#-inst_offset[xidx+yidx][1],
                            0
                    ]
                )
        
            if self.CALIBRATIONSLOT is None:
                self.CALIBRATIONSLOT = name #last slot, should be the bottom right one

    #             print(name)

    #     print(self._coordinates)

    # def __generate_coordinates(self):
    #     def letter(num):
    #         # converts number (0-25) to letter (A-Z)
    #         return chr(ord("A") + num)

    #     self._coordinates = {}
    #     self._ycoords = [
    #         letter(self.gridsize[1] - yidx - 1) for yidx in range(self.gridsize[1])
    #     ]  # lettering +y -> -y = A -> Z
    #     self._xcoords = [
    #         xidx + 1 for xidx in range(self.gridsize[0])
    #     ]  # numbering -x -> +x = 1 -> 100

    #     self.CALIBRATIONSLOT = None
    #     for yidx in range(self.gridsize[1]):  # y
    #         for xidx in range(self.gridsize[0]):  # x
    #             name = f"{self._ycoords[yidx]}{self._xcoords[xidx]}"
    #             self._coordinates[name] = np.array(
    #                 [
    #                     xidx * self.pitch[0],
    #                     yidx * self.pitch[1],
    #                     0,
    #                 ]
    #             )

             

    #         if self.CALIBRATIONSLOT is None:
    #             self.CALIBRATIONSLOT = name #last slot, should be the bottom right one

    #             print(name)

    #     print(self._coordinates)

    def get_slot_coordinates(self, name):
        if self.__calibrated == False:
            raise Exception(f"Need to calibrate tray position before use!")

        inst_offset = {    'H1' : [0,0.2,0], 'H2' : [0,0.2,0], 'H3' : [0,0.2,0], 'H4' : [0,0.2,0], ##H1-4
                           'G1' : [0,0.2,0], 'G2' : [0,0.2,0], 'G3' : [0,0.2,0], 'G4' : [0,0.2,0], ##G1-4
                           'F1' :  [0,0,0],'F2' : [0,0,0], 'F3' : [0,0,0], 'F4' : [0,0,0], ##F1-4
                           'E1' : [0,0,0], 'E2' : [0,0,0], 'E3' : [0,0,0], 'E4' :[0,0,0], ##E1-4
                           'D1' : [0,0,0], 'D2' :[0,0,0],  'D3' : [0,0,0], 'D4' : [0,0,0], ##D1-4
                           'C1' : [0,0,0], 'C2' : [0,0,0], 'C3' : [0,0,0], 'C4': [0,0,0], ##C1-4
                           'B1' : [0,0,0], 'B2' : [0,0,0], 'B3' : [0,0,0], 'B4' : [0,0,0], ##B1-4
                           'A1' : [0,-0.3,0], 'A2' : [0,-0.3,0], 'A3' : [0,-0.3,0], 'A4' : [0,-0.3,0] ##A1-4
        }

        coords = self._coordinates[name] + self.offset# - inst_offset[name]
        return coords



    def __call__(self, name):
        return self.get_slot_coordinates(name)

    def calibrate(self):
        """Calibrate the coordinate system of this workspace."""
        print(f"Make contact with device {self.CALIBRATIONSLOT} to calibrate the tray position")
        self.gantry.gui()
        self.offset = self.gantry.position - (self._coordinates[self.CALIBRATIONSLOT])
        self.gantry.moverel(z=self.gantry.ZHOP_HEIGHT)


        self.__calibrated = True

        with open(AVAILABLE_VERSIONS[self.version], "r") as f:
            constants = yaml.load(f, Loader=yaml.FullLoader)
            print("In function calibrate, constants:", constants)
        constants['offset'] = {k:float(v) for k,v in zip(['x', 'y', 'z'], self.offset)}
        print("in function calibrate, constants after loading offset?: \n", constants)
        print(" also here is 'constants[offset]': ",constants['offset'])


        with open(AVAILABLE_VERSIONS[self.version], "w") as f:
            yaml.dump(constants, f)