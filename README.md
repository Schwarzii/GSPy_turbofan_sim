# GSPy_turbofan_sim task 3 to 6

This version of the file tree includes the code for solving task 3 to 6 in the report.
To run the code, you will need the dependencies in `pyproject.toml`. We recommend using [uv](https://docs.astral.sh/uv/):

```uv sync```

to isntall the packages. Then you can run the files via

```uv run file_to_run.py```

## Important files

The file tree includes the entirety of gspy and some unnecessary files. The collection of files that were actually created or modified by us to generate the results for the report is listed below.
```
turbofan/
├── turbofan_fuel.py - modification of the turbofan example with thrust sweep, emission monitoring and fuel change capability
├── EmissionMonitor.py - new TComponent to calculate and log emissions inside a gas turbine
└── create_plots.py - helper to create the emission plots found in the report for task 6
```
