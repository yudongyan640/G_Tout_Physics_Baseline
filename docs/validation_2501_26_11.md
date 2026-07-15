# Physics Baseline Validation: 2501_26_11

## 1. Case information

- Borehole depth: 2501 m
- Flow rate: 26 m3/h
- Inlet temperature: 11 degC
- Comparison period: 0 to 19.726027 year
- Aligned samples: 241

## 2. Physics baseline configuration

- The existing physics solver was used without changes to its PDE/ODE equations.
- Existing mapped resistance settings were retained: `R_borehole=0.033851714 m*K/W` and `R_short_circuit=0.162288854 m*K/W`.
- The requested case inputs were set to H=2501 m, Q=26 m3/h, and Tin=11 degC.

## 3. OGS reference data

- Source: `E:/newdesktop/PINN/OGS_data/all_data/2501_26_11/井口处数据点.csv`
- Time column: `Time` in seconds, converted using 365 days/year.
- Outlet-temperature column: `avg(temperature_BHE1 (1))` in degC.
- OGS values were linearly interpolated onto the baseline 30-day time grid; no OGS field data was read.

## 4. Comparison results

| Metric | Value |
|---|---:|
| MAE (degC) | 12.903773 |
| RMSE (degC) | 14.579997 |
| R2 | -1.189737 |
| Bias (degC) | 10.899657 |

## 5. Error analysis

The error curve is defined as `Physics baseline - OGS`. Positive values mean the physics baseline predicts a higher outlet temperature than the OGS reference at the aligned time point; negative values mean the opposite.

## 6. Possible reasons

- The OGS reference includes its prescribed on/off operating schedule, while the current physics baseline is a continuous single-operating-condition solver.
- The physics baseline uses one-dimensional radial rock conduction and simplified fluid heat-transfer correlations.
- The two models use different spatial representations and boundary-condition implementations.

These items are possible structural differences, not parameter adjustments or calibration actions.
