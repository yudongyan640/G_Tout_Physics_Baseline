# Changelog

## v1.1.0

Date: 2026-07-15

### Added

- Independent continuous-operation validation against OGS.
- Outlet temperature comparison workflow.
- MAE, RMSE, R2 and Bias evaluation.
- Validation documentation and figures.

### Validation case

Case: 2501_26_11

Conditions:

- H=2501 m
- Q=26 m3/h
- Tin=11 ℃

Results:

- MAE: 2.12 ℃
- RMSE: 5.17 ℃
- Bias: 0.17 ℃

### Notes

No physical parameters were calibrated.
No OGS temperature field data were used.

## v1.0.0

Date: 2026-07-13

### Added

- Physics-based outlet temperature prediction framework for deep coaxial borehole heat exchanger.
- Fluid energy balance BVP solver.
- 1D radial transient rock heat conduction solver.
- OGS parameter extraction from .prj and .gml files.
- Physical parameter mapping module.
- Borehole thermal resistance calculation.
- Short-circuit resistance calculation.
- H-Q trend verification.
- Borehole resistance sensitivity analysis.

### Model Description

Physics baseline predicts `Tout(t)` using only:

- Geometry parameters
- Material properties
- Fluid properties
- Physical governing equations

The model does NOT use:

- OGS .vtu files
- OGS .pvd files
- OGS temperature fields
- Machine learning training data

### Status

Current version is ready for OGS outlet temperature validation.
