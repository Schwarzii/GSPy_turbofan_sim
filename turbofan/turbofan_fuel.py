# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Authors
#   Wilfried Visser
#   Oscar Kogenhop

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gspy.core import sys_global as FG

from gspy.core.control import TControl
from gspy.core.ambient import TAmbient
from gspy.core.inlet import TInlet
from gspy.core.fan import TFan
from gspy.core.compressor import TCompressor
from gspy.core.combustor import TCombustor
from gspy.core.turbine import TTurbine
from gspy.core.duct import TDuct
from gspy.core.exhaustnozzle import TExhaustNozzle

from ExhaustLogger import ExhaustLogger

import matplotlib.pyplot as plt
import numpy as np
from contextlib import redirect_stdout
import pandas as pd
from multiprocessing import Pool

    # IMPORTANT NOTE TO THIS MODEL FILE
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # note that this model is only to serve as example and does not represent an actual gas turbine design,
    # nor an optimized design. The component maps are just sample maps scaled to the model design point.
    # The maps are entirely unrealistic and therefore result in unrealistic, unstable off design performance,
    # stall margin exceedance etc.
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

def setup(controller):
    """Setup the experiment (equivalent to turbofan.py, except for configurable control)."""
    from gspy.core import system as fsys

    project_dir = Path(__file__).resolve().parent
    map_path = project_dir / "maps"
    FG.output_path = project_dir / "output"

    # create Ambient conditions object (to set ambient/inlet/flight conditions)
    #                              Altitude, Mach, dTs,    Ps0,    Ts0
    # None for Ps0 and Ts0 means values are calculated from standard atmosphere
    fsys.Ambient = TAmbient('Ambient', 0,   0, 0,   0,   None,   None)

    # create a control (controlling all inputs to the system model)
    # combustor Texit input, with Wf 1.11 as first guess for 1600 K DP combustor exit temperature
    
    logger = ExhaustLogger("ExhaustLogger")
    # create a turbojet system model
    fsys.system_model = [fsys.Ambient,
                        controller,
                        TInlet('Inlet1',          '', None,           0,2,   337, 1    ),
                        TFan('FAN_BST',map_path / 'bigfanc.map', 2, 25, 21,   1,   4880, 0.8696, 5.3, 0.95, 0.7, 2.33,
                                       map_path / 'bigfand.map', 0.95, 0.7, 1.65,            0.8606,
                                       # cf = 1
                                       1),
                        TCompressor('HPC',map_path / 'compmap.map', None, 25,3,   2,   14000, 0.8433, 1, 0.8, 10.9, 'GG', None),
                        TCombustor('combustor1',  '',  FuelControl, 3,4, 1.1 , 1500, 1, 1, None, 43031, 1.9167, 0, '', None),
                        TTurbine('HPT', map_path / 'turbimap.map', None, 4,45,   2,   14000, 0.8732,       1, 0.65, 1, 'GG', None),
                        TTurbine('LPT', map_path / 'turbimap.map', None, 45,5,   1,   4480, 0.8682,       1, 0.7, 1, 'GG', None),
                        TDuct('Exhduct_hot',      '', None,               5,7,   1.0                 ),
                        TExhaustNozzle('HotNozzle',     '', None,           7,8,9, 1, 1, 1),
                        TDuct('Exhduct_cold',      '', None,               21,23,   1.0                 ),
                        TExhaustNozzle('ColdNozzle',      '', None,           23,18,19, 1, 1, 1),
                        logger]
    
    # define the gas model in f_global
    FG.InitializeGas()
    fsys.ErrorTolerance = 0.0001

    return fsys

def DP(system):
    """Perform design point calculations."""
    # run the system model Design Point (DP) calculation
    system.Mode = 'DP'
    print("Design point (DP) results")
    print("=========================")
    # set DP ambient/flight conditions
    system.Ambient.SetConditions('DP', 0, 0, 0, None, None)
    system.Run_DP_simulation()

    return system

def OD(system, fuelparams, start_wf_guess):
    """Perform off-design calculations."""
    system.Mode = 'OD'
    system.inputpoints = FuelControl.Get_OD_inputpoints()
    print("\nOff-design (OD) results")
    print("=======================")
    # set OD ambient/flight conditions; note that Ambient.SetConditions must be implemented inside RunODsimulation if a sweep of operating/inlet
    # conditions is desired
    # typical cruise conditions:
    system.components['combustor1'].SetFuel(*fuelparams)
    system.components['Control'].DP_inputvalue = start_wf_guess
    system.Ambient.SetConditions('OD', 10000, 0.8, 0, None, None)
    # Run OD simulation
    system.Run_OD_simulation()

    return system

def generate_output(system, fuel_name, top_n=10):
    """Generate simulation outputs."""
    
    system.OutputToCSV(FG.output_path, fuel_name + ".csv")
    
    # create additional output listing the top top_n emitted gases and their flowrate
    # This will be for the last OD datapaoint for the given fuel
    mass_dict = system.components["ExhaustLogger"].get_exhaust_masses()
    s = pd.Series(mass_dict).sort_values(ascending=False).head(top_n)
    s.to_csv(FG.output_path / f"{fuel_name}_top{top_n}_species.csv")


def process_fuel(args):
    """Worker function to process a single fuel in a separate process."""
    fuel_name, fuelparams, assumed_od_wf = args
    
    # Setup and run DP for this process (this is the same regardless of fuel)
    system_blueprint = setup(FuelControl)
    sized_system = DP(system_blueprint)
    
    # Run off-design for this fuel
    result_system = OD(sized_system, fuelparams, assumed_od_wf)
    
    # Generate output
    generate_output(result_system, fuel_name)

# Thrust sweep params (sweep goes from T_nom*relmin to T_nom*relmax in "steps" steps)
relmin = 0.9
relmax = 1.1
steps = 5
T_nom = 24.45 # [kN]

# Fuel params
fueltemp = 273 # [K] Assumed based on instructor's input
assumed_od_wf = 0.5 # Initial guess for OD calculations. Adjust to converge for all fuels.

# All fuel compositions to test (additional ones can be defined here)
FUEL_DICT = {
    "H2": [fueltemp, None, None, None, 'H2:1'],
    "jet": [None, 43031, 1.9167, 0, ''],
    "naturalgas": [fueltemp, None, None, None, 'CH4:9, N2:1'],
}

FuelControl = TControl('Control', '', 1.11, T_nom*relmin, T_nom*relmax, T_nom*(relmax-relmin)/steps, "FN")

if __name__ == "__main__":

    # Define controller. DP_inputvalue MUST be 1.11 to match the reference system.
    
    # Prepare fuel data for multiprocessing
    fuel_data = [
        (fuel_name, fuelparams, assumed_od_wf)
        for fuel_name, fuelparams in FUEL_DICT.items()
    ]
    
    # Process fuels in parallel using multiprocessing
    with Pool() as pool:
        pool.map(process_fuel, fuel_data)