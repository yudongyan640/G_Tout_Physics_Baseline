# Changelog

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
