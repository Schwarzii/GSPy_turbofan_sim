from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gspy.core.system import TSystemModel

from gspy.core.control import TControl
from gspy.core.combustor import TCombustor


class DesignCombustor:
    def __init__(self, fuel_flow_guess=1.1, od_sweep=(1600, 1100, -50), control_par=None, fuel_composition=''):
        self.fuel_flow_guess = fuel_flow_guess
        self.od_sweep = od_sweep
        self.control_par = control_par
        self.fuel_composition = fuel_composition

        self._lhv = None
        self._hc_ratio = None
        self._oc_ratio = None
        if fuel_composition == '':
            self._lhv = 43031
            self._hc_ratio = 1.9167
            self._oc_ratio = 0

        self._sys = None
        self._fuel_control = None
        self._combustor = None

    @property
    def fuel_control(self):
        if self._sys is None:
            raise ValueError('Turbofan system not defined')
        if self._fuel_control is None:
            self._fuel_control = TControl(
                self._sys, 'Control', '', self.fuel_flow_guess,
                self.od_sweep[0], self.od_sweep[1], self.od_sweep[2],
                self.control_par)
        return self._fuel_control

    @property
    def combustor(self):
        if self._sys is None:
            raise ValueError('Turbofan system not defined')
        if self._combustor is None:
            self._combustor = TCombustor(
                self._sys, 'combustor', '', self.fuel_control,
                3, 4,
                self.fuel_flow_guess, 1500, 1, 1, None,
                self._lhv, self._hc_ratio, self._oc_ratio,
                self.fuel_composition, None)
        return self._combustor

    def connect_sys(self, turbofan_sys: TSystemModel):
        self._sys = turbofan_sys


class NaturalGasCombustor(DesignCombustor):
    def __init__(self, fuel_flow_guess=1.1, od_sweep=(1600, 1100, -50), control_par=''):
        super().__init__(fuel_flow_guess, od_sweep, control_par, 'CH4:9, N2:1')


class HydrogenCombustor(DesignCombustor):
    def __init__(self, fuel_flow_guess=0.46, od_sweep=(1600, 1100, -50), control_par=''):
        super().__init__(fuel_flow_guess, od_sweep, control_par, 'H2:1')
