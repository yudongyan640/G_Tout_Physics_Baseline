# Code Structure

## 1. Overall Architecture

The physics-based outlet temperature prediction model is organised into three layers:

```
┌──────────────────────────────────────────────────┐
│                   Entry Points                    │
│  run_single_case.py    sanity_check.py            │
│  trend_check_H_Q.py    sensitivity_borehole_resistance.py  │
│  early_time_check.py   check_ogs_mapping.py       │
└──────────────────────┬───────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────┐
│               Core Solver                         │
│  simulation.py  (main time-stepping orchestrator) │
│       ┌──────────────┴──────────────┐            │
│  fluid_bvp_solver.py    rock_solver_1d.py        │
│       │                         │                │
│  ┌────┴────┐              ┌─────┴─────┐         │
│  │ geometry│heat_transfer │  config   │         │
│  └─────────┘              └───────────┘         │
└──────────────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────┐
│            Support Modules                        │
│  borehole_resistance_calculator.py                │
│  short_circuit_resistance_calculator.py           │
│  ogs_parameter_extractor.py                       │
│  parameter_mapping.py                             │
└──────────────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────┐
│              Post-processing                      │
│  postprocess.py  (CSV, JSON, PNG, SVG)            │
└──────────────────────────────────────────────────┘
```

## 2. Module Dependency Graph

```
                    ┌─────────────┐
                    │   config    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼─────┐     │     ┌──────▼──────┐
       │  geometry  │     │     │  rock_solver │
       └──────┬─────┘     │     │   _1d.py     │
              │           │     └──────┬───────┘
       ┌──────▼───────────▼──┐         │
       │   heat_transfer     │         │
       └──────┬──────────────┘         │
              │                        │
       ┌──────▼────────────────────────▼──┐
       │         simulation               │
       │  (fluid_bvp_solver + rock)       │
       └──────┬───────────────────────────┘
              │
       ┌──────▼───────────┐
       │   postprocess    │
       └──────────────────┘

       ┌─────────────────────────────┐
       │ borehole_resistance_        │
       │ calculator.py               │
       └──────────┬──────────────────┘
                  │
       ┌──────────▼──────────────────┐
       │ short_circuit_resistance_   │
       │ calculator.py               │
       └─────────────────────────────┘

       ┌─────────────────────────────┐
       │ ogs_parameter_extractor    │
       └──────────┬──────────────────┘
                  │
       ┌──────────▼──────────────────┐
       │ parameter_mapping.py        │
       │ (uses borehole + short_circuit)│
       └──────────┬──────────────────┘
                  │
       ┌──────────▼──────────────────┐
       │ check_ogs_mapping.py        │
       └─────────────────────────────┘
```

## 3. Data Flow

### 3.1 Standard Simulation Run

```
config.py (ModelConfig)
    │
    ▼
geometry.py ──► areas, hydraulic diameters, m_dot, velocities
    │
    ▼
heat_transfer.py ──► Re, Pr, h_inner, h_outer, U_wall, U_pa
    │
    ▼
simulation.py enters time-stepping loop:
    │
    ├── fluid_bvp_solver.py
    │   ┌─ Input:  Twall(z), U_wall, U_pa, m_dot·cw
    │   └─ Output: Ta(z), Tp(z), Tout, q_wall
    │
    ├── record Tout(t), power(t), cumulative energy
    │
    └── rock_solver_1d.py
        ┌─ Input:  Ta(z), Ts_old, U_wall
        └─ Output: Ts_new (updated rock temperature field)
    │
    ▼
postprocess.py ──► CSV, JSON, PNG/SVG figures
```

### 3.2 OGS Parameter Mapping

```
OGS .prj / .gml files
    │
    ▼
ogs_parameter_extractor.py
    ┌─ geometry (H, radii, thicknesses)
    └─ materials (rock, fluid, grout properties)
    │
    ▼
parameter_mapping.py
    ├── heat_transfer.compute_prandtl()
    ├── heat_transfer.compute_reynolds()
    ├── heat_transfer.dittus_boelter_h()
    ├── borehole_resistance_calculator.calculate_borehole_wall_path()
    └── short_circuit_resistance_calculator.calculate_short_circuit_path()
    │
    ▼
outputs/baseline_physical_parameters.json
    │
    ▼ (loaded by config.py __post_init__)
ModelConfig with mapped parameters
```

### 3.3 Analysis Scripts

```
trend_check_H_Q.py
    ├── loops over H = [2000, 2500, 3000] m × Q = [15, 30, 40] m3/h
    ├── calls simulation.run_simulation() for each case
    └── saves comparison CSV + heatmap figures

sensitivity_borehole_resistance.py
    ├── loops over R_borehole = [0.05, 0.10, 0.20, 0.50] m·K/W
    ├── calls simulation.run_simulation() for each case
    └── saves comparison CSV + Tout/power figures

sanity_check.py
    ├── small mesh (Nz=51, Nr=30), 10-day duration
    ├── calls simulation.run_simulation()
    └── checks physical consistency (Tout > Tin, q_wall > 0, wall cooling)

early_time_check.py
    ├── H=2500 m, Q=30 m3/h, dt=1 day, t_end=1 year
    ├── calls simulation.run_simulation()
    └── saves fine-resolution CSV + figures for first-year analysis
```

## 4. Physical Model Implementation

### 4.1 Fluid Energy Equations

The fluid temperature distribution is governed by two coupled ODEs:

**Annulus (downward flow):**
```
m_dot · cw · dTa/dz = U_wall · (Twall − Ta) + U_pa · (Tp − Ta)
```

**Inner pipe (upward flow):**
```
m_dot · cw · dTp/dz = U_pa · (Tp − Ta)
```

These are solved as a boundary value problem (BVP) at each time step using
`scipy.integrate.solve_bvp`. The boundary conditions are:

- `Ta(0) = Tin` (inlet temperature at the top)
- `Tp(H) = Ta(H)` (thermal coupling at the borehole bottom)

The outlet temperature is `Tout(t) = Tp(0)` — a solution result, not a boundary
condition.

**Implementation:** `fluid_bvp_solver.py`

### 4.2 Rock Heat Conduction

The rock temperature evolution is governed by the 1D radial heat conduction
equation (solved independently at each depth z):

```
ρr · cr · ∂Ts/∂t = kr · (1/r) · ∂/∂r(r · ∂Ts/∂r)
```

**Numerical method:** Implicit finite-volume method.

- **Radial mesh:** logarithmically spaced from `Rb` to `Rout`, providing high
  resolution near the borehole wall where gradients are steepest.
- **Time integration:** fully implicit (backward Euler), stable for large time
  steps (default 30 days).
- **Borehole wall boundary:** Implicit Robin condition coupling the wall
  temperature and heat flux:
  ```
  q_wall = U_wall · (Twall_new − Ta)
  ```
  This avoids numerical oscillations under strong heat extraction.
- **Far-field boundary:** Dirichlet condition at `r = Rout`:
  ```
  Ts(Rout, z, t) = Tamb + G · z
  ```

**Implementation:** `rock_solver_1d.py`

### 4.3 Heat Transfer Coefficients

The unit-length heat transfer coefficients are computed as:

- **Reynolds number:** `Re = ρ · u · dh / μ`
- **Prandtl number:** `Pr = μ · cp / k`
- **Dittus-Boelter correlation (turbulent):** `Nu = 0.023 · Re^0.8 · Pr^0.4`
- **Convective coefficient:** `h = Nu · k / dh`

**U_wall (borehole wall → annulus):**
- Lumped model: `U_wall = 1 / R_borehole` (when `use_effective_borehole_resistance=True`)
- Legacy model: `U_wall = 2π · Rb · h_wall` (annulus convection only)

**U_pa (inner pipe → annulus):**
- `1/U_pa = 1/(2π·r_in·h_in) + ln(r_out/r_in)/(2π·λ_ins) + 1/(2π·r_out·h_out)`

**Implementation:** `heat_transfer.py`, `borehole_resistance_calculator.py`,
`short_circuit_resistance_calculator.py`

### 4.4 Thermal Resistance Models

Two dedicated modules compute the equivalent thermal resistances from
detailed borehole geometry:

**Borehole wall path (rock → grout → casing → annulus):**

```
R_borehole = R_ann_conv + R_outer_pipe + R_grout
```

**Short-circuit path (inner pipe → insulation → annulus):**

```
R_short_circuit = R_center_conv + R_insulation + R_ann_conv
```

The unit-length cylindrical conduction resistance is:
```
R_cyl = ln(r_outer / r_inner) / (2π · k)
```

The unit-length convective resistance is:
```
R_conv = 1 / (2π · r · h)
```

**Implementation:** `borehole_resistance_calculator.py`,
`short_circuit_resistance_calculator.py`

### 4.5 Overall Simulation Loop

At each time step `t_n → t_{n+1}`:

1. Extract the current borehole wall temperature: `Twall(z) = Ts(r=Rb, z, t_n)`
2. Solve the fluid BVP to obtain `Ta(z)`, `Tp(z)`, `Tout`.
3. Compute heat extraction power: `P = m_dot · cw · (Tout − Tin)`.
4. Advance the rock temperature `Ts(r, z, t_n) → Ts(r, z, t_{n+1})` using
   the implicit Robin wall condition.
5. Set `n = n + 1`, repeat until the final time.

**Implementation:** `simulation.py`

## 5. Key Design Decisions

| Decision | Rationale |
|---|---|
| **Quasi-steady fluid** | Fluid thermal inertia is negligible compared to the rock thermal mass on the typical time scale (days to years). |
| **No axial rock conduction** | The dominant heat flow in the rock is radial; axial gradients are small in deep boreholes. First-order simplification. |
| **Implicit time integration** | Allows large time steps (30 days) without stability constraints that would apply to explicit schemes. |
| **Logarithmic radial mesh** | High near-wall resolution where temperature gradients are largest, without excessive total node count. |
| **Dittus-Boelter correlation** | Widely used turbulent internal-flow correlation; covers the typical operating range. A warning is issued for low Re. |
| **Lumped R_borehole** | Avoids over-parameterisation in the first version; a detailed layer-by-layer model is available as a separate module. |

## 6. Test Files

| File | Tests |
|---|---|
| `test_borehole_resistance_calculator.py` | Cylindrical layer and convective resistance calculations |
| `test_check_ogs_mapping.py` | OGS mapping validation logic |
| `test_early_time_check_contract.py` | Early-time check output contract |
| `test_ogs_config_loading.py` | XML parameter extraction |
| `test_ogs_parameter_extractor.py` | OGS parameter parsing |
| `test_parameter_mapping.py` | Parameter mapping correctness |
| `test_postprocess_summary_metrics.py` | Diagnostic metric formatting |
| `test_trend_check_contract.py` | Trend check output contract |
