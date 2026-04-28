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

    @staticmethod
    def fit_plot(x, y, poly):
        plt.plot(x, y)
        plt.plot(x, poly(x), '--')
        plt.show()

    def fit_root(self, poly, root_low=None, root_high=None):
        if root_low is None:
            root_low = self.od_perf['N1%'].min()
        if root_high is None:
            root_high = self.od_perf['N1%'].max()
        root = np.roots(poly)
        root = np.real(root[np.isreal(root)])
        return root[(root_low < root) & (root < root_high)]

    def surge_line_limit(self, map_name='core', sm_pct=0):
        match map_name:
            case 'core':
                map_name = 'Fan_Bst_map_core'
            case 'duct':
                map_name = 'Fan_Bst_map_duct'
            case 'hpc':
                map_name = 'HPC_map'
        surge_line = np.load(self.map_data_dir / f'{map_name}_surge.npy')
        sm_line = surge_line[0] * (1 + sm_pct / 100)
        sm_line_fit = np.poly1d(np.polyfit(sm_line, surge_line[1], 6))  # Fitting of the surge (margin) line
        surge_line_inv_fit = np.poly1d(np.polyfit(surge_line[1], surge_line[0], 6))

        op_line = np.load(self.map_data_dir / f'{map_name}_op_line.npy')
        op_fit = np.poly1d(np.polyfit(op_line[0], op_line[1], 6))  # Fitting of operating line

        wc_fit = np.poly1d(np.polyfit(op_line[0], self.od_perf['N1%'], 6))  # Fitting of Wc vs. N1

        if sm_pct != 0:
            with open(self.map_data_dir / f"{map_name}_plot.pickle", "rb") as f:
                map_plot = pickle.load(f)

            map_plot.axes[0].plot(surge_line[0] * (1 + sm_pct / 100), surge_line[1], lw=1.0, ls='dashed',
                                  color='red', label=f'Surge Line (margin = {sm_pct}%)')
            map_plot.savefig(self.post_out_dir / f"{map_name}_sm{sm_pct}.png", dpi=100)
            map_plot.show()

        sm_fit = op_fit - sm_line_fit  # Fitting of the surge margin value

        surge_wc = self.fit_root(sm_fit, op_line[0].min(), op_line[0].max())
        if len(surge_wc) > 0:
            for sp in surge_wc:
                surge_n1 = wc_fit(sp)
                print(f'surge @ Wc = {sp:.2f}, sm = {sm_pct}%,  N1 = {surge_n1:.2f}%')
        else:
            min_sm = (op_line[0] / surge_line_inv_fit(op_line[1]) - 1).min()
            print(f'min surge margin = {min_sm * 100:.2f}%')

        plt.plot(surge_line[0], surge_line[1])
        plt.plot(surge_line[0] * (1 + sm_pct / 100), sm_line_fit(surge_line[0] * (1 + sm_pct / 100)))
        plt.plot(op_line[0], op_line[1])
        plt.show()

        print()

    def n1_limit_at_dp_perf_fit(self, fit_perf='T4', lim_target=None, deg=6):
        if lim_target is None:
            lim_target = self.dp_perf[fit_perf][0]
        lim_fit = np.poly1d(np.polyfit(self.od_perf['N1%'], self.od_perf[fit_perf] - lim_target, deg))
        lim_target_n1 = self.fit_root(lim_fit)
        if not lim_target_n1:
            print(f'No N1 can achieve DP {fit_perf}')
            return
        print(f'Achieve DP {fit_perf} at N1 = {', '.join([f"{lim_target_n1:.2f}%"])}')

        # self.fit_plot(self.od_perf['N1%'], self.od_perf[fit_perf] - lim_target, lim_fit)

    def find_min_by_fit(self, perf_y, deg=8):
        perf_fit_c = np.polyfit(self.od_perf['N1%'], self.od_perf[perf_y], deg)
        perf_fit = np.poly1d(perf_fit_c)
        # fit_plot(od_perf['N1%'], od_perf[perf_y], np.poly1d(perf_fit_c))

        fig_grad_poly = np.poly1d(perf_fit_c[:deg] * np.arange(deg, 0, -1))
        min_point = self.fit_root(fig_grad_poly)[0]
        min_perf_y = perf_fit(min_point)
        print(f"Min {perf_y} point -> {min_perf_y:.4f} @ N1 = {min_point:.2f}%")

        return min_point

    def fit_perf_at_n1(self, n1, deg=6, dec=2, *args):
        for pi in range(0, len(args), 2):
            perf = args[pi]
            perf_lbl = args[pi + 1] if pi + 1 < len(args) else perf
            perf_fit = np.poly1d(np.polyfit(self.od_perf['N1%'], self.od_perf[perf], deg))
            perf_at_n1 = perf_fit(n1)
            if perf_lbl is None:
                perf_lbl = perf
            print(f"{perf_lbl} | {perf} @ N1 = {n1:.2f}% -> {perf_at_n1:.{dec}f}")


if __name__ == '__main__':
    tf = TurbofanSim('methane_fuel_sim')
    tf.set_combustor(DesignCombustor(od_sweep=(1600, 1100, -50)))
    tf.turbofan_configuration()
    tf.run_design_point_methane()
    tf.run_turbofan_od()
    tf.save_post_result()

    post = PostTFSim(tf)
    # post.fan_speed_vs_perf(['T4', 'T45'], ["TIT [K]", "EGT [K]"], 'turbine_temp_limit_row_plot', True)
    # post.fan_speed_vs_perf(['Wf_combustor', 'FN', 'TSFC'],
    #                        ["Fuel flow [kg/s]", "Net thrust [kN]", 'TSFC [kg/N h]'],
    #                        'fuel_efficiency')
    # post.fan_speed_vs_perf(['TSFC'], ['TSFC [kg/N h]'], 'TSFC')

    n1_target = post.find_min_by_fit('TSFC')
    post.fit_perf_at_n1(n1_target, 6, 2,
                        'T4', 'TIT',
                        'T45', 'EGT',
                        'Wf_combustor', 'fuel flow',
                        'FN', 'net thrust',
                        'TSFC')


    print()


