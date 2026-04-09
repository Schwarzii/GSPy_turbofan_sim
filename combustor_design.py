from gspy.core.control import TControl
from gspy.core.combustor import TCombustor


class DesignCombustor:
    def __init__(self, des_fuel_flow=1.1, od_sweep=(1600, 1100, -50), control_par=None, fuel_composition=''):
        self.des_fuel_flow = des_fuel_flow
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

        self.fuel_control = TControl('Control', '', self.des_fuel_flow,
                                     od_sweep[0], od_sweep[1], od_sweep[2],
                                     control_par)

        self.combustor = TCombustor('combustor1', '', self.fuel_control,
                                    3, 4,
                                    self.des_fuel_flow, 1500, 1, 1, None,
                                    self._lhv, self._hc_ratio, self._oc_ratio,
                                    self.fuel_composition, None)


class NaturalGasCombustor(DesignCombustor):
    def __init__(self, des_fuel_flow=1.1, od_sweep=(1600, 1100, -50), control_par='FN'):
        super().__init__(des_fuel_flow, od_sweep, control_par, 'CH4:9, N2:1')


class HydrogenCombustor(DesignCombustor):
    def __init__(self, des_fuel_flow=0.46, od_sweep=(1600, 1100, -50), control_par='FN'):
        super().__init__(des_fuel_flow, od_sweep, control_par, 'H2:1')
