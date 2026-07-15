# Case A Continuous Operation Validation

## 1. Case information

- Borehole depth: 2501 m
- Flow rate: 26 m3/h
- Inlet temperature: 11 degC
- Physics simulation setting: 20.0 year requested, with the existing 30-day numerical time step.
- OGS reference coverage: 0.000000 to 19.726027 year (365-day conversion).

## 2. Boundary conditions

`DBHE.prj` defines constant temperature and flow curves over 0.1 to 622080000 s: Tin=11 degC and Q=0.007222 m3/s (approximately 26 m3/h). This is a continuous-operation OGS case.

## 3. Physics baseline model

- The existing solver was called through the same `ModelConfig` and `run_simulation` path used by `run_single_case.py`.
- No PDE/ODE equation, resistance formula, `R_borehole`, `U_wall`, or `U_pa` was modified.
- Active mapped values retained for this run: `R_borehole=0.033851714 m*K/W`, `R_short_circuit=0.162288854 m*K/W`, `U_wall=29.540601556 W/(m*K)`, and `U_pa=6.161852601 W/(m*K)`.

## 4. Comparison results

`physics_Tout_caseA.csv` retains the complete baseline prediction. Physics output was also linearly interpolated to the OGS outlet-data timestamps and saved as `CaseA_aligned_comparison.csv`; the comparison therefore uses identical time nodes and contains 332 samples.

| Metric | Value |
|---|---:|
| MAE (degC) | 2.119919 |
| RMSE (degC) | 5.171563 |
| R2 | -10.153679 |
| Bias (degC) | 0.171683 |

## 5. Error analysis

The plotted error is `Physics baseline - OGS`; positive values mean the baseline prediction is higher than the OGS outlet temperature. The metrics include the complete shared OGS time span, including the initial output point.

If discrepancies are present, possible sources include the radial one-dimensional rock-model simplification, equivalent wellbore-resistance representation, initial geothermal-temperature condition, and the baseline 30-day numerical time step. This validation neither changes model parameters nor uses OGS results to infer any parameter.
