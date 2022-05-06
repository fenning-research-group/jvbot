from pymeasure.instruments.keithley import Keithley2400
import time
import yaml
import numpy as np
import os

MODULE_DIR = os.path.dirname(__file__)
with open(os.path.join(MODULE_DIR, "hardwareconstants.yaml"), "r") as f:
    constants = yaml.load(f, Loader=yaml.FullLoader)["keithley"]


class Keithley(Keithley2400):
    def __init__(self, address=None):
        if address is None:
            address = constants["address"]
        super().__init__(address)
        self.reset()
        self.use_front_terminals()
        self.constants = constants

        if constants["four_wire"]:
            self.wires = 4
        else:
            self.wires = 2
        self.buffer_points = 2
        self._source_voltage_measure_current()

    def _source_voltage_measure_current(self):
        self.apply_voltage()
        self.measure_current()
        self.compliance_current = self.constants["compliance_current"]
        self.source_voltage = 0

    def _source_current_measure_voltage(self):
        self.apply_current()
        self.measure_voltage()
        self.compliance_voltage = self.constants["compliance_voltage"]
        self.source_current = 0

    def _set_buffer(self, npts):
        self.disable_buffer()
        self.buffer_points = self.constants["counts"]
        self.reset_buffer()

    def _parse_buffer(self, npts):
        alldata = self.buffer_data
        means = np.zeros((npts,))
        stds = np.zeros((npts,))
        for i in range(npts):
            idx = slice(i * npts, (i + 1) * npts)
            means[i] = np.mean(alldata[idx])
            stds[i] = np.std(alldata[idx])
        return {"mean": means, "std": stds}

    def measure(self):
        """
        returns voltage, current, and resistance measured
        """
        self.config_buffer(self.constants["counts"])
        self.start_buffer()
        self.wait_for_buffer()
        return self.means

    def isc(self):
        self._source_voltage_measure_current()
        self.source_voltage = 0
        self.enable_source()
        isc = self.measure()[1]
        self.disable_source()

        return -isc  # flip sign for convention

    def voc(self):
        self._source_current_measure_voltage()
        self.source_current = 0
        self.enable_source()

        voc = self.measure()[0]

        self.disable_source()
        # print(f"Voc: {voc*1000:.2f} mV")

        return voc

    def iv(self, vmin, vmax, steps=51):
        self._source_voltage_measure_current()
        self.source_voltage = vmin

        v = np.linspace(vmin, vmax, steps)
        vmeas = np.zeros(steps)
        i = np.zeros(steps)

        self.enable_source()
        for m, v_ in enumerate(v):
            self.source_voltage = v_
            vmeas[m], i[m], _ = self.measure()
        self.disable_source()

        return vmeas, -i  # flip current sign for convention
