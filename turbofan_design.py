from pathlib import Path
import pickle
from typing import Iterable

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from gspy.core import sys_global as fg
from gspy.core import system as fsys

from gspy.core.ambient import TAmbient
from gspy.core.inlet import TInlet
from gspy.core.fan import TFan
from gspy.core.compressor import TCompressor
from gspy.core.turbine import TTurbine
from gspy.core.duct import TDuct
from gspy.core.exhaustnozzle import TExhaustNozzle

from combustor_design import DesignCombustor


class TurbofanSim:
    def __init__(self, output_dir='methane_fuel_sim', combustor: DesignCombustor = DesignCombustor(), tol=1e-4):
        self.project_dir = Path(__file__).resolve().parent
        self.map_path = self.project_dir / 'gspy/data/sample_maps'
        self.output_dir = output_dir
        self.output_path = self.project_dir / output_dir
        fg.output_path = self.output_path

        fsys.Ambient = TAmbient('Ambient', 0, 0, 0, 0, None, None)
        self.sea_level_condition = ('DP', 0, 0, 0, None, None)
        self.cruise_condition =  ('OD', 10000, 0.8, 0, None, None)

        self.tf_combustor = combustor

        self._init_gas_flag = False
        fsys.ErrorTolerance = tol
        fsys.VERBOSE = False

        self.csv_name = None

    def set_combustor(self, combustor: DesignCombustor):
        self.tf_combustor = combustor

    def turbofan_configuration(self):
        fsys.system_model = [fsys.Ambient,
                             self.tf_combustor.fuel_control,
                             TInlet('Inlet1', '', None, 0, 2, 337, 1),
                             # for turbofan, note that fan has 2 GasOut outputs
                             TFan('FAN_BST', self.map_path / 'bigfanc.map', 2, 25, 21, 1, 4880, 0.8696, 5.3, 0.95, 0.7, 2.33,
                                  self.map_path / 'bigfand.map', 0.95, 0.7, 1.65, 0.8606,
                                  # cf = 1
                                  1),
                             # always start with the components following the 1st GasOut object
                             TCompressor('HPC', self.map_path / 'compmap.map', None, 25, 3, 2, 14000, 0.8433, 1, 0.8, 10.9,
                                         'GG', None),
                             self.tf_combustor.combustor,
                             TTurbine('HPT', self.map_path / 'turbimap.map', None, 4, 45, 2, 14000, 0.8732, 1, 0.65, 1, 'GG',
                                      None),

                             TTurbine('LPT', self.map_path / 'turbimap.map', None, 45, 5, 1, 4480, 0.8682, 1, 0.7, 1, 'GG',
                                      None),

                             TDuct('Exhduct_hot', '', None, 5, 7, 1.0),
                             TExhaustNozzle('HotNozzle', '', None, 7, 8, 9, 1, 1, 1),

                             # now add the list with components following the 2nd fan GasOut (i.e. the bypass duct)
                             TDuct('Exhduct_cold', '', None, 21, 23, 1.0),
                             TExhaustNozzle('ColdNozzle', '', None, 23, 18, 19, 1, 1, 1)]

    def _init_gas(self):
        if not self._init_gas_flag:
            fg.InitializeGas()
            self._init_gas_flag = True

    def design_point_methane(self):
        self._init_gas()

        fsys.Mode = 'DP'
        print("Design point (DP) results")
        print("=========================")
        # set DP ambient/flight conditions
        fsys.Ambient.SetConditions(*self.sea_level_condition)
        fsys.Run_DP_simulation()

    def run_turbofan_od(self):
        self._init_gas()

        # run the Off-Design (OD) simulation, to find the steady state operating points for all fsys.inputpoints
        fsys.Mode = 'OD'
        fsys.inputpoints = self.tf_combustor.fuel_control.Get_OD_inputpoints()
        print("\nOff-design (OD) results")
        print("=======================")
        # set OD ambient/flight conditions; note that Ambient.SetConditions must be implemented inside RunODsimulation if a sweep of operating/inlet
        # conditions is desired
        # typical cruise conditions:
        fsys.Ambient.SetConditions(*self.cruise_condition)
        # Run OD simulation
        fsys.Run_OD_simulation()

    def post_result(self, csv_name='turbofan'):
        self.csv_name = csv_name
        # export OutputTable to CSV
        fsys.OutputToCSV(fg.output_path, f"{csv_name}.csv")

        # plot nY vs X parameter
        fsys.Plot_X_nY_graph('Performance vs N1 [%] at Alt 10000m, Ma 0.8 (DP at ISA SL)',
                             fg.output_path / f"{csv_name}_1.jpg",
                             # common X parameter column name with label
                             ("N1%", "Fan speed [%]"),
                             # 4 Y parameter column names with labels and color
                             [("T4", "TIT [K]", "blue"),
                              ("T45", "EGT [K]", "blue"),
                              ("W2", "Inlet mass flow [kg/s]", "blue"),
                              ("Wf_combustor1", "Fuel flow [kg/s]", "blue"),
                              ("FN", "Net thrust [kN]", "blue")])

        # Create plots with operating lines if available
        for comp in fsys.system_model:
            comp.PlotMaps()

        print("end of running turbofan simulation")


class PostTFSim:
    def __init__(self, simulation: TurbofanSim, post_output_dir=''):
        self.post_out_dir = simulation.output_path / post_output_dir  # Default is not creating a separate folder
        self.sim_data = pd.read_csv(simulation.output_path / simulation.csv_name)
        self.sim_data['TSFC'] = self.sim_data['Wf_combustor1'] / (self.sim_data['FN'] * 1000) * 3600  # [kg/Nh]
        self.dp_perf = self.sim_data[self.sim_data['Mode'] == 'DP']
        self.od_perf = self.sim_data[self.sim_data['Mode'] == 'OD']

        self.map_data_dir = simulation.output_path / 'map_data'

    def fan_speed_vs_perf(self, y, lbl, save_name=None, row_layout=False):
        figure_setting = (len(y), 1, 8, len(y) * 3 + 2 * 1 / (len(y)))
        if row_layout:
            figure_setting = (1, len(y), 10, 4)
        fig, axes = plt.subplots(figure_setting[0], figure_setting[1], figsize=figure_setting[2:4])
        if not isinstance(axes, Iterable):
            axes = [axes]
        for i, ax in enumerate(axes):
            ax.plot(self.od_perf['N1%'], self.od_perf[y[i]])
            ax.scatter(
                self.dp_perf['N1%'], self.dp_perf[y[i]],
                s=40,  # points^2, screen-fixed size
                marker="s",
                facecolors="yellow",
                edgecolors="black",
                linewidths=0.8,
                zorder=1,
                label="Design point" if i == 0 else None  # add legend label once
            )
            for dpy in self.dp_perf[y[i]]:
                ax.axhline(dpy, color='k', ls='dashed', lw=0.8)

            ax.grid(True, which='major', ls='dashed')
            ax.grid(True, which='minor', ls='dotted')
            ax.minorticks_on()

            if row_layout:
                ax.set_xlabel('Fan speed [%]')
            ax.set_ylabel(lbl[i])

        if not row_layout:
            plt.xlabel('Fan speed [%]')
        plt.suptitle("Performance vs N1 [%] at Alt 10000m, Ma 0.8 (DP at ISA SL)")

        handles, labels = axes[0].get_legend_handles_labels()
        if handles:
            axes[0].legend(handles, labels, loc="best")
        plt.tight_layout()
        if save_name:
            plt.savefig(self.post_out_dir / f"{save_name}.png", dpi=100)
        plt.show()

        print()


if __name__ == '__main__':
    tf = TurbofanSim()
    tf.set_combustor(DesignCombustor(od_sweep=(1200, 1100, -100)))
    tf.turbofan_configuration()
    tf.design_point_methane()
    tf.run_turbofan_od()
    tf.post_result()
    print()


