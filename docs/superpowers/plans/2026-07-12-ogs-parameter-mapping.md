# OGS Parameter Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse DBHE XML parameters and use them as the baseline's physical configuration without reading OGS results.

**Architecture:** Keep XML extraction, thermal-resistance calculation, mapping, configuration loading, and reporting in separate modules. Preserve the existing PDE/ODE solver; only supply its existing physical inputs and the new annulus geometry boundary.

**Tech Stack:** Python 3.10, standard-library `xml.etree.ElementTree`, `json`, `dataclasses`, existing NumPy/SciPy baseline.

## Global Constraints

- Read only `DBHE.prj` and `DBHE.gml`; never read `.vtu`, `.pvd`, or OGS result data.
- All new code has detailed Chinese comments.
- `R_borehole` excludes center-pipe insulation; `R_short_circuit` contains it.
- Do not change the PDE/ODE solvers or execute batch cases.

---

### Task 1: XML extraction and raw JSON

**Files:** Create `test_ogs_parameter_extractor.py`, `ogs_parameter_extractor.py`.

- [ ] Write failing tests that call `extract_ogs_parameters(PRJ_PATH, GML_PATH)` and assert H=2500, Rb=0.1208, medium-0 rock properties, refrigerant properties, Tamb=14.8, G=0.033, and no result-file paths.
- [ ] Run `conda run -n geo_pinn python -m unittest test_ogs_parameter_extractor.py -v`; expect import failure before implementation.
- [ ] Implement standard-library XML parsing and `write_raw_parameters()` with detailed Chinese comments.
- [ ] Re-run the test; expect pass.

### Task 2: Independent resistance calculators and mapping

**Files:** Create `test_parameter_mapping.py`, `short_circuit_resistance_calculator.py`, `parameter_mapping.py`; modify `borehole_resistance_calculator.py`.

- [ ] Write failing tests for nonzero finite wall and short-circuit resistances and for required mapping JSON keys.
- [ ] Run `conda run -n geo_pinn python -m unittest test_parameter_mapping.py -v`; expect import failure before implementation.
- [ ] Implement named wall-path and short-circuit-path calculation functions, map extracted parameters, and write `outputs/baseline_physical_parameters.json`.
- [ ] Re-run the test; expect pass.

### Task 3: Configuration loading and report

**Files:** Create `test_ogs_config_loading.py`, `check_ogs_mapping.py`; modify `config.py`.

- [ ] Write failing tests that construct `ModelConfig(use_ogs_parameters=True, ogs_parameters_path=...)` and assert mapped H, Rb, U-wall resistance, U-pa resistance, and annulus radius are applied.
- [ ] Run `conda run -n geo_pinn python -m unittest test_ogs_config_loading.py -v`; expect failure before implementation.
- [ ] Implement JSON override in `ModelConfig.__post_init__`, add the mapping checker, and retain all existing defaults when disabled.
- [ ] Re-run the new and pre-existing tests; expect pass.

### Task 4: Integration verification

**Files:** Create `results/Result7.txt`; generate `outputs/ogs_raw_parameters.json`, `outputs/baseline_physical_parameters.json`, and the normal single-case output directory.

- [ ] Run `conda run -n geo_pinn python check_ogs_mapping.py` and inspect values, SI checks, missing fields, and anomalies.
- [ ] Run `conda run -n geo_pinn python run_single_case.py` once.
- [ ] Run all `test_*.py` files with unittest discovery, then record commands and outcomes in `results/Result7.txt`.
