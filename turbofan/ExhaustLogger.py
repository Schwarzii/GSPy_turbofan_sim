from gspy.core.base_component import TComponent
import gspy.core.system as fsys

class ExhaustLogger(TComponent):
	def __init__(self, name):
		super().__init__(name, None, False)
		self.exhaust_dict = {}
	def Run(self, Mode, PointTime):
		self.exhaust_dict = self.get_exhaust_masses()

	def AddOutputToDict(self, Mode):
		fsys.output_dict["CO2"] = self.exhaust_dict.get("CO2", 0)
		fsys.output_dict["H2O"] = self.exhaust_dict.get("H2O", 0)

	def get_exhaust_masses(self):
		"""Post process net emission massflow of all species (hot nozzle out minus HPT in)."""
		f_out = fsys.components['HotNozzle'].GasOut.mass
		f_in = fsys.components['HPC'].GasIn.mass
		out_dict = fsys.components['HotNozzle'].GasOut.mass_fraction_dict()
		in_dict = fsys.components['HPC'].GasIn.mass_fraction_dict()
		# logic ignores species that might have been completely destroyed in the combustor
		# this is unlikely and "negative" emissions are not important anyways
		exhaust_dict = {k: out_dict.get(k, 0) * f_out - in_dict.get(k, 0) * f_in for k in out_dict.keys()}
		return exhaust_dict
	
	def PrintPerformance(self, Mode, PointTime):
		pass