# GSPy_turbofan_sim

**This branch uses GSPy v2.0 to finish task Q1 and Q2 of the assignment.**

Run
---
To run the simulation, open `turbofan_design.py` and directly run it.
The plots will be saved to a separate folder `methane_fuel_sim`, which will be automatically created if not existed.


If running the default workflow of the `turbofan_design.py` script, the console will print the OD performance at the minimum TSFC point. 
The plot folder (`methane_fuel_sim`) will contain the following:
- `map` folder: compressor and turbine maps with operating line
- `map_data` folder: `.npy` stores the points of surge and operating lines, `.pickle` stores the map plotting object for redrawing
- `map_dual` folder: duel compressor and turbine maps

Due to the setting of curve fitting order, the OD performance may be slightly different from the values in the report.

**Note that this version does _not_ implement the OD simulation of combustor with alternative fuel**