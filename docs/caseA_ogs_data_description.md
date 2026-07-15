# Case A OGS Data Description

## Case information

- OGS project file: `2501_26_11/DBHE.prj`
- Exported outlet-data file: `2501_26_11/optimized_results/井口参数.csv`
- Borehole depth from `DBHE.prj`: 2501 m
- Case label: Case A, continuous operation

## Boundary condition

- Temperature control curve time coordinates (s): 0.1 622080000
- Temperature control values (degC): 11 11
- Flow control curve time coordinates (s): 0.1 622080000
- Flow control values (m3/s): 0.007222 0.007222
- The curve endpoints have equal values, therefore Tin and Q are constant over the exported operating period.

## Output variable description

- Time column: `Time`, unit: s.
- Outlet-temperature column: `avg(temperature_BHE1 (1))`, unit: degC.
- Valid rows read: 332.
- Time range: 0 to 622080000 s, equivalent to 0.000000 to 19.726027 year using 365 days/year.
- Only the two columns above are read. No `.vtu`, `.pvd`, or rock-temperature-field file is read.
