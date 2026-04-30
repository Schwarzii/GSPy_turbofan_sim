import pandas as pd
from matplotlib import axes
from cycler import cycler
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns

from turbofan_fuel import FUEL_DICT

# Ensure colorblind scheme
sns.set_palette("colorblind")
current_palette = sns.color_palette()

BASE_PATH = Path(__file__).resolve().parent

def get_file(fuel_name, top10=False):
	"""Get the correct input csv"""
	if not top10:
		return BASE_PATH / "output" / f"{fuel_name}.csv"
	else:
		return BASE_PATH / "output" / f"{fuel_name}_top10_species.csv"

def plot_a_vs_b(a: str, b: str, ax: axes.Axes, exclude_dp = True):
	"""Line plot of column b against column a"""
	for fuel in FUEL_DICT.keys():
		df = pd.read_csv(get_file(fuel))
		if exclude_dp:
			df = df[df["Mode"] == "OD"]
		ax.plot(df.get(a), df.get(b), label=fuel_disp(fuel))

def plot_emission(gas: str, ax: axes.Axes):
	"""Plot emissions against net thrust"""
	plot_a_vs_b("FN", gas, ax)
	ax.set_xlabel("Net thrust [kN]")
	ax.set_ylabel(f"Net {gas} emission [kg/s]")
	ax.grid()
	ax.legend()

def plot_rel_emission(gas: str, ax: axes.Axes):
	"""Plot combustor massflow normalized emissions against net thrust"""
	plot_a_vs_b("FN", f'{gas}_rel', ax)
	ax.set_xlabel("Net thrust [kN]")
	ax.set_ylabel(f"Net {gas} emission per combustor massflow [-]")
	ax.grid()
	ax.legend()

def plot_fuel_use(ax: axes.Axes):
	"""Plot fuel use against net thurst"""
	plot_a_vs_b("FN", "WF", ax)
	ax.set_xlabel("Net thrust [kN]")
	ax.set_ylabel(f"Fuel burn [kg/s]")
	ax.grid()
	ax.legend()

def plot_top(fuel: str, ax: axes.Axes, group_threshold: float = 0.1, palette: list = current_palette):
	"""Plot top 10 emitted gases (gases with relative content < group threshold are grouped in "other")"""
	# Load the data
	df = pd.read_csv(get_file(fuel, True), index_col=0)
	
	# Calculate relative values (percentages)
	# Identify rows where the flowrate is less than the threshold
	# Rename those specific index labels to 'Other'
	total_flow = df["flowrate"].sum()
	low_val_mask = (df["flowrate"] / total_flow) > group_threshold
	df.index = df.index.where(low_val_mask, 'Other')
	
	# Group by the new index (merging all 'Other' rows) and sum
	df_plotted = df.groupby(level=0).sum()
	
	# Plot the result
	ax.pie(
		df_plotted["flowrate"], 
		autopct='%1.2f%%',
		pctdistance=1.25,
		startangle=90,
		colors=palette
	)
	
	# Set the individual title
	ax.set_title(fuel_disp(fuel), pad=20) 
	
	# Create the label
	ax.legend(
        df_plotted.index,
        loc="upper center",
        bbox_to_anchor=(0.5, 0),
        ncol=len(df_plotted.index)
    )

def fuel_disp(fuel: str) -> str:
	"""Convert internal fuel names to diplayable names"""
	match fuel:
		case "jet":
			return "Jet fuel"
		case "H2":
			return "Hydrogen"
		case "naturalgas":
			return "Natural gas"
		case _:
			return fuel

if __name__ == "__main__":
	fig1, ax1 = plt.subplots(1, 3, figsize=(10, 4))
	for i, fuel in enumerate(FUEL_DICT.keys()):
		# Collect the colors used in this specific subplot
		if fuel == "H2":
			# Make H2O appear the same color as on the other plots
			plot_top(fuel, ax1[i], 0.05, palette=current_palette[1:])
		else:
			plot_top(fuel, ax1[i], 0.05)

	fig2, ax2 = plt.subplots(1, 3, sharey=True, figsize=(10, 4))
	plot_fuel_use(ax2[0])
	plot_emission("CO2", ax2[1])
	plot_emission("H2O", ax2[2])

	fig3, ax3 = plt.subplots(1, 2, sharey=True, figsize=(10, 4))
	plot_rel_emission("CO2", ax3[0])
	plot_rel_emission("H2O", ax3[1])


	plt.tight_layout()
	plt.show()