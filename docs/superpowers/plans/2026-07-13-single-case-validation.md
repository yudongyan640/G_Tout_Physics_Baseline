# Single-case Physics Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline execution selected by the user).

**Goal:** Independently compare the unchanged physics baseline with exported OGS outlet-temperature data for case 2501_26_11.

**Architecture:** `validation_single_case.py` reads only the exported CSV time series, constructs an existing `ModelConfig`, overrides only H/Q/Tin and the end time for this validation case, then calls `run_simulation`. It interpolates OGS Tout onto the baseline 30-day time grid, computes requested metrics, and writes comparison artifacts.

**Tech Stack:** Python, NumPy, Pandas, Matplotlib, existing baseline solver.

## Global Constraints

- Do not modify existing physics-model code, R_borehole, U_wall, U_pa, or PDE/ODE equations.
- Read only `井口处数据点.csv` column `Time` and `avg(temperature_BHE1 (1))` as OGS reference data.
- Use SI seconds internally and 365-day years for output.
- Do not train, calibrate, commit, push, or run batch cases.

---

### Task 1: Reference parsing and metric functions

**Files:** Create `test_validation_single_case.py`, `validation_single_case.py`.

- [ ] Write a failing unittest for `calculate_metrics()` using known arrays and for `load_ogs_outlet_data()` using a temporary CSV with `Time` and the confirmed outlet column.
- [ ] Run `conda run -n geo_pinn python -m unittest test_validation_single_case.py -v`; expect an import failure.
- [ ] Implement CSV parsing, time conversion, interpolation, MAE/RMSE/R2/Bias, and validation configuration construction.
- [ ] Re-run the unittest; expect pass.

### Task 2: Case execution and artifacts

**Files:** Create `outputs/validation/2501_26_11/physics_Tout.csv`, comparison/error PNG and SVG files, `Metrics_summary.txt`, `docs/validation_2501_26_11.md`, `results/Result8.txt`.

- [ ] Run `conda run -n geo_pinn python validation_single_case.py` once.
- [ ] Verify the CSV time grids match exactly, all four metrics are finite, and each requested artifact exists.
- [ ] Run existing and new unittest files plus `py_compile`; record all commands and results in `results/Result8.txt`.
