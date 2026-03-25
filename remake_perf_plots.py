import pickle
from typing import Iterable

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sim_data = pd.read_csv("turbofan/output/turbofan.csv")
sim_data['TSFC'] = sim_data['Wf_combustor1'] / (sim_data['FN'] * 1000) * 3600
dp_perf = sim_data[sim_data['Mode'] == 'DP']
od_perf = sim_data[sim_data['Mode'] == 'OD']


def fan_speed_vs_perf(y, lbl, save_name=None, row_layout=False):
    figure_setting = (len(y), 1, 8, len(y) * 3 + 2 * 1 / (len(y)))
    if row_layout:
        figure_setting = (1, len(y), 10, 4)
    fig, axes = plt.subplots(figure_setting[0], figure_setting[1], figsize=figure_setting[2:4])
    if not isinstance(axes, Iterable):
        axes = [axes]
    for i, ax in enumerate(axes):
        ax.plot(od_perf['N1%'], od_perf[y[i]])
        ax.scatter(
            dp_perf['N1%'], dp_perf[y[i]],
            s=40,  # points^2, screen-fixed size
            marker="s",
            facecolors="yellow",
            edgecolors="black",
            linewidths=0.8,
            zorder=1,
            label="Design point" if i == 0 else None  # add legend label once
        )
        for dpy in dp_perf[y[i]]:
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
        plt.savefig(f"OD_perf_plots/{save_name}.png", dpi=100)
    plt.show()

    print(sim_data.head())


def fit_plot(x, y, poly):
    plt.plot(x, y)
    plt.plot(x, poly(x), '--')
    plt.show()


def fit_root(poly, root_low=None, root_high=None):
    if root_low is None:
        root_low = od_perf['N1%'].min()
    if root_high is None:
        root_high = od_perf['N1%'].max()
    root = np.roots(poly)
    root = np.real(root[np.isreal(root)])
    return root[(root_low < root) & (root < root_high)]


def n1_limit_fit(fit_perf='T4', lim_target=None, deg=6):
    if lim_target is None:
        lim_target = dp_perf[fit_perf][0]
    lim_fit = np.poly1d(np.polyfit(od_perf['N1%'], od_perf[fit_perf] - lim_target, deg))
    lim_target_n1 = fit_root(lim_fit)
    print(lim_target_n1)

    fit_plot(od_perf['N1%'], od_perf[fit_perf] - lim_target, lim_fit)

    print()


def surge_line_limit(map_name='core', sm_pct=0):
    match map_name:
        case 'core':
            map_name = 'FAN_BST_map_core'
        case 'duct':
            map_name = 'FAN_BST_map_duct'
        case 'hpc': map_name = 'HPC_map'
    surge_line = np.load(f'turbofan/{map_name}_surge.npy')
    sm_line = surge_line[0] * (1 + sm_pct / 100)
    surge_fit = np.poly1d(np.polyfit(sm_line, surge_line[1], 6))
    surge_inv_fit = np.poly1d(np.polyfit(surge_line[1], surge_line[0], 6))

    op_line = np.load(f'turbofan/{map_name}_op_line.npy')
    op_fit = np.poly1d(np.polyfit(op_line[0], op_line[1], 6))

    wc_fit = np.poly1d(np.polyfit(op_line[0], od_perf['N1%'], 6))
    # fit_plot(op_line[0], od_perf['N1%'], wc_fit)

    if sm_pct != 0:
        with open(f"turbofan/{map_name}_plot.pickle", "rb") as f:
            map_plot = pickle.load(f)

        map_plot.axes[0].plot(surge_line[0] * (1 + sm_pct / 100), surge_line[1], lw=1.0, ls='dashed',
                              color='red', label=f'Surge Line (margin = {sm_pct}%)')
        map_plot.savefig(f"OD_perf_plots/{map_name}_sm{sm_pct}.png", dpi=100)
        map_plot.show()

    sm_fit = op_fit - surge_fit

    surge_wc = fit_root(sm_fit, op_line[0].min(), op_line[0].max())
    if len(surge_wc) > 0:
        for sp in surge_wc:
            surge_n1 = wc_fit(sp)
            print(f'surge @ Wc = {sp:.2f}, sm = {sm_pct}%,  N1 = {surge_n1:.2f}%')
    else:
        min_sm = (op_line[0] / surge_inv_fit(op_line[1]) - 1).min()
        print(f'min surge margin = {min_sm * 100:.2f}%')

    plt.plot(surge_line[0], surge_line[1])
    plt.plot(surge_line[0] * (1 + sm_pct / 100), surge_fit(surge_line[0] * (1 + sm_pct / 100)))
    plt.plot(op_line[0], op_line[1])
    plt.show()

    # fit_plot(surge_line[0], surge_line[1], surge_fit)
    # fit_plot(op_line[0], op_line[1], op_fit)

    print()


def min_fit(perf_y, deg=8):
    perf_fit_c = np.polyfit(od_perf['N1%'], od_perf[perf_y], deg)
    perf_fit = np.poly1d(perf_fit_c)
    # fit_plot(od_perf['N1%'], od_perf[perf_y], np.poly1d(perf_fit_c))

    fig_grad_poly = np.poly1d(perf_fit_c[:deg] * np.arange(deg, 0, -1))
    min_point = fit_root(fig_grad_poly)[0]
    min_perf_y = perf_fit(min_point)
    print(f"Min {perf_y} point -> {min_perf_y:.4f} @ N1 = {min_point:.2f}%")

    return min_point


def fit_n1_perf(n1, perf, perf_lbl=None, deg=6, dec=2):
    perf_fit = np.poly1d(np.polyfit(od_perf['N1%'], od_perf[perf],deg))
    perf_at_n1 = perf_fit(n1)
    if perf_lbl is None:
        perf_lbl = perf
    print(f"{perf_lbl} | {perf} @ N1 = {n1:.2f}% -> {perf_at_n1:.{dec}f}")


if __name__ == '__main__':
    fan_speed_vs_perf(['T4', 'T45'], ["TIT [K]", "EGT [K]"], 'turbine_temp_limit_row_plot', True)
    # fan_speed_vs_perf(['Wf_combustor1', 'FN', 'TSFC'],
    #                   ["Fuel flow [kg/s]", "Net thrust [kN]", 'TSFC [kg/N h]'],
    #                   'fuel_efficiency')
    # fan_speed_vs_perf(['TSFC'], ['TSFC [kg/N h]'], 'TSFC')

    # n1_limit_fit('T4')
    # n1_limit_fit('T45')

    # n1_limit_fit()
    # for m in ['core', 'duct', 'hpc']:
    #     surge_line_limit(m, sm_pct=5)

    n1_target = min_fit('TSFC')

    fit_n1_perf(n1_target, 'T4', 'TIT')
    fit_n1_perf(n1_target, 'T45', 'EGT')
    fit_n1_perf(n1_target, 'Wf_combustor1', 'fuel flow')
    fit_n1_perf(n1_target, 'FN', 'net thrust')
    fit_n1_perf(n1_target, 'TSFC')

    print()

