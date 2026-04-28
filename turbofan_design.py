from pathlib import Path
import pickle
from typing import Iterable

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from gspy.core.system import TSystemModel

from gspy.core.inlet import TInlet
from gspy.core.fan import TFan
from gspy.core.compressor import TCompressor
from gspy.core.turbine import TTurbine
from gspy.core.duct import TDuct
from gspy.core.exhaustnozzle import TExhaustNozzle

from combustor_design import DesignCombustor


class TurbofanSim:
    def __init__(self, output_dir='methane_fuel_sim', combustor: DesignCombustor = DesignCombustor()):
        self.project_dir = Path(__file__).resolve().parent
        # self.map_path = self.project_dir / 'gspy/data/sample_maps'
        self.output_dir = output_dir
        self.output_path = self.project_dir / output_dir

        self.verbose = False

        self.sys = TSystemModel('Turbofan', model_file=__file__, output_dir=output_dir, verbose=self.verbose)
        self.tf_combustor = None
        self.set_combustor(combustor)

        self.sea_level_condition = ('DP', 0, 0, 0, None, None)
        self.cruise_condition =  ('OD', 10000, 0.8, 0, None, None)

        self.csv_name = None

    def set_combustor(self, combustor: DesignCombustor):
        self.tf_combustor = combustor
        self.tf_combustor.connect_sys(self.sys)

    def turbofan_configuration(self):
        inlet = TInlet(self.sys,  # owning system model object
                       'Inlet',  # component name
                       '',  # map file name
                       None,  # optional control component
                       1, 2,  # station nr in and out
                       337,  # design inlet mass flow
                       1  # design pressure ratio (PR = 1 - Ploss_relative)
                       )
        fan = TFan(self.sys,  # owning system model object
                   'Fan_Bst',  # component name
                   'bigfanc.map',  # core flow map file name
                   2, 25, 21,  # station nr in, core out, bypass (duct side) out
                   1,  # shaft nr
                   4880,  # design rpm
                   0.8696,  # core flow design efficiency
                   5.3,  # design bypass ratio BPR
                   0.95,  # core map design Nc (for scaling)
                   0.7,  # core map design Beta (for scaling)
                   2.33,  # core flow design PR

                   # bypass flow map data
                   'bigfand.map',  # bypass flow map file name
                   0.95,  # bypass (duct side) map design Nc (for scaling)
                   0.7,  # bypass map design Beta (for scaling)
                   1.65,  # bypass flow design PR
                   0.8606,  # bypass flow design efficiency

                   1  # cross flow control factor (see fan.py code)
                   )

        hpc = TCompressor(self.sys,
                          'HPC',  # component name
                          'compmap.map',  # map file name
                          None,  # optional control component
                          25, 3,  # station nr in and out
                          2,  # shaft nr
                          14000,  # design rpm
                          0.8433,  # design efficiency
                          1,  # map design Nc (for scaling)
                          0.8,  # map design Beta (for scaling)
                          10.9,  # design pressure ratio
                          'GG',  # speed option
                          None  # option list of bleeds
                          )

        hpt = TTurbine(self.sys, 'HPT',  # component name
                       'turbimap.map',  # map file name
                       None,  # optional control component
                       4, 45,  # station nr in and out
                       2,  # shaft nr
                       14000,  # design point (DP) rpm
                       0.8732,  # design point (DP) efficiency
                       1,  # map design Nc (for scaling)
                       0.65,  # map design Beta (for scaling)
                       1.0,  # design mechanical efficiency (standard isentropic, Polytropic_Eta = 0)
                       'GG',  # turbine type 'GG' = gas generator delivering all power required by the shaft
                       #              'PT' = free power turbine or turbine driving power output shaft
                       None  # optional cooling flows object list
                       )
        # option for working with polytropic efficiency: uncomment next line
        # turbine1.Polytropic_Eta = 1

        lpt = TTurbine(self.sys, 'LPT',
                       'turbimap.map',  # map file name
                       None,  # optional control component
                       45, 5,  # station nr in and out
                       1,  # shaft nr
                       4480,  # design point (DP) rpm
                       0.8682,  # design point (DP) efficiency
                       1,  # map design Nc (for scaling)
                       0.7,  # map design Beta (for scaling)
                       1.0,  # design mechanical efficiency (standard isentropic, Polytropic_Eta = 0)
                       'GG',  # turbine type 'GG' = gas generator delivering all power required by the shaft
                       #              'PT' = free power turbine or turbine driving power output shaft
                       None  # optional cooling flows object list
                       )
        # option for working with polytropic efficiency: uncomment next line
        # turbine1.Polytropic_Eta = 1

        hot_duct = TDuct(self.sys, 'Exhduct_hot',  # component name
                         '',  # optional map file name
                         None,  # optional control component
                         5, 7,  # station nr in and out
                         1.0  # design pressure ratio, use to specify rel. pressure loss ploss (PR = (1 - ploss)/Pin)
                         )

        hot_nozzle = TExhaustNozzle(self.sys, 'HotNozzle',  # component name
                                    '',  # option map file name
                                    None,  # optional control component
                                    7, 8, 9,
                                    # station nr of entry, throat and exit  (throat and exit only different fo con-di nozzle)
                                    # con-di nozzle model still to be implemented
                                    1,  # design CX thrust coefficient
                                    1,  # design CV velocity coefficient
                                    1  # design CD discharge coefficient
                                    )

        # now add the list with components following the 2nd fan GasOut (i.e. the bypass duct)
        cold_duct = TDuct(self.sys, 'Exhduct_cold',  # component name
                          '',  # optional map file name
                          None,  # optional control component
                          21, 23,  # station nr in and out
                          1.0  # design pressure ratio, use to specify rel. pressure loss ploss (PR = (1 - ploss)/Pin)
                          )

        cold_nozzle = TExhaustNozzle(self.sys, 'ColdNozzle',
                                     '',  # option map file name
                                     None,  # optional control component
                                     23, 18, 19,
                                     # station nr of entry, throat and exit  (throat and exit only different fo con-di nozzle)
                                     # con-di nozzle model still to be implemented
                                     1,  # design CX thrust coefficient
                                     1,  # design CV velocity coefficient
                                     1  # design CD discharge coefficient
                                     )

        # create a turbojet system model
        self.sys.define_comp_run_list(self.tf_combustor.fuel_control,
                                      inlet,
                                      fan,
                                      hpc,
                                      self.tf_combustor.combustor,
                                      hpt,
                                      lpt,
                                      hot_duct,
                                      hot_nozzle,
                                      cold_duct,
                                      cold_nozzle)

    def run_design_point_methane(self):
        self.sys.Mode = 'DP'
        print("Design point (DP) results")
        print("=========================")
        # set DP ambient/flight conditions
        self.sys.ambient.SetConditions(*self.sea_level_condition)
        self.sys.Run_DP_simulation()

    def run_turbofan_od(self):
        # run the Off-Design (OD) simulation, to find the steady state operating points for all fsys.inputpoints
        self.sys.Mode = 'OD'
        self.sys.inputpoints = self.tf_combustor.fuel_control.get_OD_input_points()
        print("\nOff-design (OD) results")
        print("=======================")
        # set OD ambient/flight conditions; note that Ambient.SetConditions must be implemented inside RunODsimulation if a sweep of operating/inlet
        # conditions is desired
        # typical cruise conditions:
        self.sys.ambient.SetConditions(*self.cruise_condition)
        # Run OD simulation
        self.sys.Run_OD_simulation()

    def save_post_result(self):
        # export OutputTable to CSV
        self.sys.OutputToCSV()

        # plot nY vs X parameter
        self.sys.Plot_X_nY_graph('Performance vs N1 [%] at Alt 10000m, Ma 0.8 (DP at ISA SL)',
                             "_1",
                             # common X parameter column name with label
                             ("N1%", "Fan speed [%]"),
                             # 4 Y parameter column names with labels and color
                             [("T4", "TIT [K]", "blue"),
                              ("T45", "EGT [K]", "blue"),
                              ("W2", "Inlet mass flow [kg/s]", "blue"),
                              ("Wf_combustor", "Fuel flow [kg/s]", "blue"),
                              ("FN", "Net thrust [kN]", "blue")])

        # Create plots with operating lines if available
        self.sys.PlotMaps()

        print("end of running turbofan simulation")


class PostTFSim:
    def __init__(self, simulation: TurbofanSim, post_output_dir=''):
        self.post_out_dir = simulation.output_path / post_output_dir  # Default is not creating a separate folder

        self.sim_data = pd.read_csv(simulation.output_path / 'Turbofan.csv')
        self.sim_data['TSFC'] = self.sim_data['Wf_combustor'] / (self.sim_data['FN'] * 1000) * 3600  # [kg/Nh]
        self.dp_perf = self.sim_data[self.sim_data['Mode'] == 'DP']
        self.od_perf = self.sim_data[self.sim_data['Mode'] == 'OD']

        self.map_data_dir = simulation.output_path / 'map_data'

        print()

    def fan_speed_vs_perf(self, y, lbl=None, save_name=None, row_layout=False):
        if isinstance(y, str):
            y = [y]
        if lbl is None:
            lbl = y

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
            for dp_y in self.dp_perf[y[i]]:
                ax.axhline(dp_y, color='k', ls='dashed', lw=0.8)

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
    tf = TurbofanSim('methane_fuel_sim')
    tf.set_combustor(DesignCombustor(od_sweep=(1300, 1100, -50)))
    tf.turbofan_configuration()
    # tf.run_design_point_methane()
    # tf.run_turbofan_od()
    # tf.save_post_result()

    post = PostTFSim(tf)
    post.fan_speed_vs_perf('TSFC')


    print()


