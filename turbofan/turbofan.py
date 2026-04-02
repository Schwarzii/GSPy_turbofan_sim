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

from gspy.core import sys_global as fg
from gspy.core import system as fsys
from gspy.core import utils as fu

from gspy.core.control import TControl
from gspy.core.ambient import TAmbient
from gspy.core.shaft import TShaft
from gspy.core.inlet import TInlet
from gspy.core.fan import TFan
from gspy.core.compressor import TCompressor
from gspy.core.combustor import TCombustor
from gspy.core.turbine import TTurbine
from gspy.core.duct import TDuct
from gspy.core.exhaustnozzle import TExhaustNozzle

import os
import matplotlib.pyplot as plt
import pandas as pd
import multiprocessing
import functools
import pickle

from calc_co2 import co2_rate


def main(T_nom, fuel_info, fuelname):
    # Paths
    project_dir = Path(__file__).resolve().parent
    map_path = project_dir / "maps"
    fg.output_path = project_dir / "output"

    # create Ambient conditions object (to set ambient/inlet/flight conditions)
    #                              Altitude, Mach, dTs,    Ps0,    Ts0
    # None for Ps0 and Ts0 means values are calculated from standard atmosphere
    fsys.Ambient = TAmbient('Ambient', 0,   0, 0,   0,   None,   None)

    # create a control (controlling all inputs to the system model)
    # combustor Texit input, with Wf 1.11 as first guess for 1600 K DP combustor exit temperature
    relmin = 0.9
    relmax = 1.1
    steps = 5
    FuelControl = TControl('Control', '', 0.79, T_nom*relmin, T_nom*relmax, T_nom*(relmax-relmin)/steps, "FN")
       

    # create a turbojet system model
    fsys.system_model = [fsys.Ambient,

                        FuelControl,

                        TInlet('Inlet1',          '', None,           0,2,   337, 1    ),

                        # for turbofan, note that fan has 2 GasOut outputs
                        TFan('FAN_BST',map_path / 'bigfanc.map', 2, 25, 21,   1,   4880, 0.8696, 5.3, 0.95, 0.7, 2.33,
                                       map_path / 'bigfand.map', 0.95, 0.7, 1.65,            0.8606,
                                       # cf = 1
                                       1),

                        # always start with the components following the 1st GasOut object
                        TCompressor('HPC',map_path / 'compmap.map', None, 25,3,   2,   14000, 0.8433, 1, 0.8, 10.9, 'GG', None),

                        # ***************** Combustor ******************************************************
                        # fuel input
                        # Texit input, Wf guess for 1500 K is 1.1 kg/s
                        TCombustor('combustor1',  '',  FuelControl, 3,4, 1.1, 1500, 1, 1, *fuel_info),

                        TTurbine('HPT', map_path / 'turbimap.map', None, 4,45,   2,   14000, 0.8732,       1, 0.65, 1, 'GG', None),

                        TTurbine('LPT', map_path / 'turbimap.map', None, 45,5,   1,   4480, 0.8682,       1, 0.7, 1, 'GG', None),


                        TDuct('Exhduct_hot',      '', None,               5,7,   1.0                 ),
                        TExhaustNozzle('HotNozzle',     '', None,           7,8,9, 1, 1, 1),

                        # now add the list with components following the 2nd fan GasOut (i.e. the bypass duct)
                        TDuct('Exhduct_cold',      '', None,               21,23,   1.0                 ),
                        TExhaustNozzle('ColdNozzle',      '', None,           23,18,19, 1, 1, 1)]

    # define the gas model in f_global
    fg.InitializeGas()
    fsys.ErrorTolerance = 0.0001

    # run the system model Design Point (DP) calculation
    fsys.Mode = 'DP'
    print("Design point (DP) results")
    print("=========================")
    # set DP ambient/flight conditions
    fsys.Ambient.SetConditions('DP', 0, 0, 0, None, None)
    fsys.Run_DP_simulation()

    # run the Off-Design (OD) simulation, to find the steady state operating points for all fsys.inputpoints
    fsys.Mode = 'OD'
    fsys.inputpoints = FuelControl.Get_OD_inputpoints()
    print("\nOff-design (OD) results")
    print("=======================")
    # set OD ambient/flight conditions; note that Ambient.SetConditions must be implemented inside RunODsimulation if a sweep of operating/inlet
    # conditions is desired
    # typical cruise conditions:
    fsys.Ambient.SetConditions('OD', 10000, 0.8, 0, None, None)
    # Run OD simulation
    fsys.Run_OD_simulation()

    #  output results
    outputbasename = os.path.splitext(os.path.basename(__file__))[0]
    # export OutputTable to CSV
    fsys.OutputToCSV(fg.output_path, f"{fuelname}.csv")

    # plot nY vs X parameter
    """fsys.Plot_X_nY_graph('Performance vs FN at Alt 10000m, Ma 0.8 (DP at ISA SL)',
                            os.path.join(fg.output_path, outputbasename + "_1.jpg"),
                            # common X parameter column name with label
                            ("FN",           "Net thrust [kN]"),
                            # 4 Y paramaeter column names with labels and color
                            [   ("Wf_combustor1",   "Fuel flow [kg/s]",         "blue"),
                                ("FN",              "Net thrust [kN]",          "blue")            ])
    """
     # Create plots with operating lines if available
    # for comp in fsys.system_model:
    #     comp.PlotMaps()

    print("end of running turbofan simulation")
    return fg.output_path / f"{fuelname}.csv"

# main program start, calls main()
# Constants
T_nom = 24.45 # kN
fueltemp = 273 # TODO: Ask what this should be
FUEL_DICT = {
    "jet": [None, 43031, 1.9167, 0, '', None],
    "naturalgas": [fueltemp, None, None, None, 'CH4:9, N2:1', None],
    "H2": [fueltemp, None, None, None, 'H2:1', None],
}

def run_simulation(fuel_tuple, t_nominal):
    """
    because main is stateful ahhhhh
    """
    fuel_name, fuel_params = fuel_tuple
    # This calls your original main function
    return main(t_nominal, fuel_params, fuelname=fuel_name)

if __name__ == "__main__":
    if True:
        tasks = list(FUEL_DICT.items())
        worker_func = functools.partial(run_simulation, t_nominal=T_nom)
        #filepaths.append(main(T_nom, FUEL_DICT.get(fuelchoice), fuelname=fuelchoice))
        with multiprocessing.Pool() as pool:
            filepaths = pool.map(worker_func, tasks)
            with open("./filepaths", "wb") as file:
                pickle.dump(filepaths, file)
    else:
        with open("./filepaths", "rb") as file:
            filepaths = pickle.load(file)

    # Plotting
    fig, ax1 = plt.subplots(figsize=(10, 6))
    ax2 = ax1.twinx()
    for filepath in filepaths:
        fuel_name = filepath.stem
        composition = FUEL_DICT.get(fuel_name)[4]
        composition = "JET_A:1" if composition == "" else composition
        print(composition)
        co2_factor = co2_rate(composition)
        print(co2_factor)
        df = pd.read_csv(filepath)
        df = df[df["Mode"] == "OD"]
        df["co2"] = df["WF"] * co2_factor
        ax1.plot(df["FN"], df["WF"], label=f"{fuel_name} (WF)", marker="o")
        ax2.plot(df["FN"], df["co2"], label=f"{fuel_name} (CO2)", marker="x")

    ax1.set_xlabel("Net thrust [kN]")
    ax1.set_ylabel("Fuel flow [kg/s]")
    ax2.set_ylabel("CO2 emission [kg/s]")
    ax1.grid(True, linestyle=':', alpha=0.7)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize='small')
    plt.tight_layout()
    plt.show()
