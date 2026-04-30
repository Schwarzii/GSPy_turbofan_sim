from gspy.core.base_component import TComponent
import gspy.core.system as fsys

class EmissionMonitor(TComponent):
	def __init__(self, name, tracked_gases = ["CO2", "H2O"]):
		super().__init__(name, None, False)
		self.exhaust_dict = {}
		self.tracked_gases = tracked_gases

	def Run(self, Mode, PointTime):
		self.exhaust_dict = self.get_exhaust_masses()

	def AddOutputToDict(self, Mode):
		f_out = fsys.components['combustor1'].GasOut.mass
		for gas in self.tracked_gases:
			fsys.output_dict.update({gas: self.exhaust_dict.get(gas, 0)})
			fsys.output_dict.update({f'{gas}_rel': self.exhaust_dict.get(gas, 0) / f_out})

	def get_exhaust_masses(self):
		"""Post process net emission massflow of all species (combustor out minus combustor in)."""
		f_out = fsys.components['combustor1'].GasOut.mass
		f_in = fsys.components['combustor1'].GasIn.mass
		out_dict = fsys.components['combustor1'].GasOut.mass_fraction_dict()
		in_dict = fsys.components['combustor1'].GasIn.mass_fraction_dict()
		# logic ignores species that might have been completely destroyed in the combustor
		# this is unlikely and "negative" emissions are not important anyways
		exhaust_dict = {k: out_dict.get(k, 0) * f_out - in_dict.get(k, 0) * f_in for k in out_dict.keys()}
		return exhaust_dict
	
	def PrintPerformance(self, Mode, PointTime):
		pass