# Physics-Based Outlet Temperature Prediction Model for Deep Coaxial Borehole Heat Exchanger

**Version**: Physics Baseline V1.0 | **Status**: Research code — physics-driven, no ML training data used

---

## English Summary

### Project Overview

This project implements a **physics-driven baseline model** for predicting the outlet fluid temperature `Tout(t)` of a **Deep Coaxial Borehole Heat Exchanger (DCBHE)**. It is part of a broader comparative study for:

- PINN (Physics-Informed Neural Network) outlet temperature prediction;
- OGS (OpenGeoSys) high-fidelity numerical simulation;
- Pure data-driven NN models.

> The baseline is built entirely on first-principles physics — it requires **no OGS training data**, no fitting, and no calibration against numerical simulation results.

### Model Features

| Feature | Description |
|---|---|
| **Physics-driven** | Quasi-steady fluid ODE/BVP + transient rock radial heat conduction PDE |
| **No OGS data required** | Solves directly from geometry, material properties, and boundary conditions |
| **Borehole resistance** | Computes `R_borehole`, `U_wall`, `U_pa`, and `R_short_circuit` |
| **Parameter mapping** | Reads and maps OGS simulation parameters (`.prj`/`.gml`) to physical model inputs |
| **H-Q trend verification** | Built-in scripts to verify expected physical trends with depth and flow rate |
| **Sensitivity analysis** | Borehole thermal resistance sensitivity study module |
| **Early-stage diagnostics** | Metrics to identify and exclude start-up period from evaluation |

### Mathematical Model

**Fluid energy equations** (quasi-steady, 1D):

Annulus (downward flow):
```
m_dot · cw · dTa/dz = U_wall · (Twall − Ta) + U_pa · (Tp − Ta)
```

Inner pipe (upward flow):
```
m_dot · cw · dTp/dz = U_pa · (Tp − Ta)
```

**Rock heat conduction** (1D radial, transient):
```
ρr · cr · ∂Ts/∂t = kr · (1/r) · ∂/∂r(r · ∂Ts/∂r)
```

**Boundary conditions**:
- Fluid: `Ta(0) = Tin`, `Tp(H) = Ta(H)`, `Tout(t) = Tp(0)`
- Rock initial: `Ts(r,z,0) = Tamb + G · z`
- Far-field: `Ts(Rout,z,t) = Tamb + G · z`
- Borehole wall: implicit Robin-type coupling `q_wall = U_wall · (Twall_new − Ta)`

### Model Pipeline

```
OGS parameters (.prj / .gml)
         ↓
   parameter_mapping.py
         ↓
  Physical parameters (geometry, properties, boundary conditions)
         ↓
  R_borehole / U_wall / U_pa / R_short_circuit
         ↓
   fluid_bvp_solver.py (quasi-steady BVP at each time step)
         ↓
   rock_solver_1d.py   (implicit radial heat conduction)
         ↓
   Tout(t) time series
         ↓
   postprocess.py (CSV, JSON, figures)
```

### How to Run

```bash
# Quick validation (small problem)
conda run -n geo_pinn python sanity_check.py

# Full single-case run (20-year default)
conda run -n geo_pinn python run_single_case.py

# Trend verification (H-Q sensitivity)
conda run -n geo_pinn python trend_check_H_Q.py

# Borehole resistance sensitivity
conda run -n geo_pinn python sensitivity_borehole_resistance.py

# OGS parameter mapping check
conda run -n geo_pinn python check_ogs_mapping.py
```

### Dependencies

See [requirements.txt](requirements.txt). Key packages: `numpy`, `scipy`, `matplotlib`.

### Repository Structure

```
G_Tout_Physics_Baseline/
├── config.py                          # Model configuration
├── geometry.py                        # Geometric calculations
├── heat_transfer.py                   # Heat transfer coefficients
├── fluid_bvp_solver.py                # Fluid BVP solver
├── rock_solver_1d.py                  # Rock radial conduction solver
├── simulation.py                      # Main simulation orchestrator
├── borehole_resistance_calculator.py  # Borehole thermal resistance
├── short_circuit_resistance_calculator.py  # Short-circuit resistance
├── ogs_parameter_extractor.py         # OGS parameter reader
├── parameter_mapping.py               # OGS → physical mapping
├── check_ogs_mapping.py               # Mapping validation
├── run_single_case.py                 # Run entry point
├── postprocess.py                     # Output and plotting
├── sanity_check.py                    # Smoke test
├── trend_check_H_Q.py                 # H-Q trend verification
├── sensitivity_borehole_resistance.py # Sensitivity analysis
├── early_time_check.py                # Start-up diagnostics
├── test_*.py                          # Unit tests
├── docs/                              # Design docs and plans
└── requirements.txt                   # Python dependencies
```

### Current Status and Next Steps

- **V1.0 complete**: Quasi-steady fluid solver, 1D radial rock conduction, borehole resistance calculation, OGS parameter mapping, trend verification, sensitivity analysis.
- **Planned**: OGS validation comparison → PINN residual formulation → r-z axisymmetric rock conduction → temperature-dependent material properties → optimization.

---

## 中文详细说明

本项目用于建立一个不依赖 OGS 训练数据的 physics-based baseline，预测中深层同轴套管地埋管换热器出口水温 `Tout(t)`。

本项目不读取、不调用、不拟合任何 OGS 计算结果；第一版只使用 `H`、`Q`、`Tin`、几何参数、流体物性、岩土物性和地温梯度。

## 项目目的

该 baseline 后续用于和以下模型对比：

- 纯 NN 出口水温预测模型；
- OGS 高保真数值模拟；
- 后续数据 + 物理约束 PINN 出口水温模型。

第一版目标不是追求和 OGS 完全一致，而是先建立物理趋势正确、代码结构清晰、便于扩展的纯物理求解器。

## 物理假设

坐标定义：井口 `z=0`，井底 `z=H`，`z` 向下为正。

主要变量：

- `Ta(z,t)`：环空下降流体温度；
- `Tp(z,t)`：中心管上升流体温度；
- `Ts(r,z,t)`：岩土温度；
- `Twall(z,t)=Ts(Rb,z,t)`：井壁岩土温度；
- `Tout(t)=Tp(0,t)`：出口水温。

第一版采用“准稳态流体一维 ODE/BVP + 瞬态岩土径向导热 PDE”：

- 流体忽略储热项和轴向导热项；
- 岩土在每个 `z` 位置独立求解一维径向导热；
- 第一版不考虑岩土轴向导热；
- 水和岩土物性取常数；
- 几何参数是占位默认值，后续应替换为 OGS 模型或实际工程尺寸。

## 控制方程

环空下降流体：

```text
m_dot * cw * dTa/dz = U_wall * (Twall - Ta) + U_pa * (Tp - Ta)
```

中心管上升流体：

```text
m_dot * cw * dTp/dz = U_pa * (Tp - Ta)
```

岩土径向导热：

```text
rho_r * cr * dTs/dt = kr * 1/r * d/dr(r * dTs/dr)
```

## 边界条件

流体边界条件：

```text
Ta(0) = Tin
Tp(H) = Ta(H)
Tout(t) = Tp(0)
```

岩土初始条件：

```text
Ts(r,z,0) = Tamb + G*z
```

岩土远场边界：

```text
Ts(Rout,z,t) = Tamb + G*z
```

井壁耦合热流：

```text
q_wall(z,t) = U_wall * (Twall - Ta)
```

当 `q_wall > 0` 时，表示岩土向环空流体放热，近井岩土温度应随时间下降。

数值实现中保留了显式 `q_wall` 更新函数，便于检查符号；主模拟默认使用更稳定的隐式井壁 Robin 边界：

```text
q_wall = U_wall * (Twall_new - Ta)
```

也就是说，井壁热流和新时刻井壁温度一起进入岩土隐式矩阵，避免强换热条件下把旧时刻热流一次性施加到很薄的近井控制体而导致非物理过冷。

## 文件结构

```text
G_Tout_Physics_Baseline
├── config.py
├── geometry.py
├── heat_transfer.py
├── fluid_bvp_solver.py
├── rock_solver_1d.py
├── simulation.py
├── run_single_case.py
├── postprocess.py
├── sanity_check.py
├── requirements.txt
├── README.md
└── outputs
    └── .gitkeep
```

文件作用：

- `config.py`：定义 `ModelConfig`，集中管理工况、几何、物性、网格和输出路径；
- `geometry.py`：计算中心管面积、环空面积、水力直径、质量流量和流速；
- `heat_transfer.py`：计算 `Re`、`Pr`、Dittus-Boelter 对流换热系数、`U_wall` 和 `U_pa`；
- `fluid_bvp_solver.py`：使用 `scipy.integrate.solve_bvp` 求解流体边值问题；
- `rock_solver_1d.py`：实现对数径向网格和隐式岩土径向导热更新；
- `simulation.py`：组织主模拟流程；
- `run_single_case.py`：默认 20 年单工况运行入口；
- `postprocess.py`：保存 CSV、JSON，并绘制 PNG/SVG 图；
- `sanity_check.py`：短时间 smoke test。
- `sensitivity_borehole_resistance.py`：井筒等效热阻敏感性测试脚本。

## 安装依赖

```bash
conda run -n geo_pinn python -m pip install -r requirements.txt
```

如果你使用其他 Python 3.10 环境，可以把 `geo_pinn` 换成自己的环境名。

## 先运行 sanity check

```bash
conda run -n geo_pinn python sanity_check.py
```

该脚本使用较小问题：

- `H=1000 m`
- `t_end=10 days`
- `dt=1 day`
- `Nz=51`
- `Nr=30`

检查内容：

- 程序能否正常跑完；
- `Tout > Tin`；
- `q_wall` 大多数位置为正；
- 近井岩土温度下降；
- 输出简短文本报告。

## 运行默认 20 年单工况

确认 sanity check 通过后，再手动运行：

```bash
conda run -n geo_pinn python run_single_case.py
```

默认参数：

- `H = 2500 m`
- `Q = 30 m3/h`
- `Tin = 10 degC`
- `Tamb = 15 degC`
- `G = 0.035 K/m`
- `t_end_years = 20`
- `dt_days = 30`
- `Nz = 201`
- `Nr = 80`

默认还启用井筒等效热阻：

- `use_effective_borehole_resistance = True`
- `borehole_resistance = 0.10 m*K/W`

启用时：

```text
U_wall = 1 / borehole_resistance
```

这相当于把水泥环、套管、接触热阻等综合进井筒等效热阻。若设置
`use_effective_borehole_resistance=False`，则退回旧写法：

```text
U_wall = 2*pi*Rb*h_wall
```

旧写法只考虑环空侧对流换热，可能使 `U_wall` 偏大，从而导致初始 `Tout`
偏高、前期取热功率过大、近井岩土冷却过快。

注意：这是 20 年长周期计算，本次项目创建过程中没有主动执行。

## 输出文件

默认输出目录：

```text
outputs/case_H2500_Q30_Tin10
```

输出包括：

- `tout_timeseries.csv`
- `fluid_profiles.csv`
- `summary.json`
- `fig_tout_vs_time.png`
- `fig_tout_vs_time.svg`
- `fig_power_vs_time.png`
- `fig_power_vs_time.svg`
- `fig_fluid_profiles.png`
- `fig_fluid_profiles.svg`
- `diagnostics.json`
- `fig_rock_radial_profiles_H_over_4.png`
- `fig_rock_radial_profiles_H_over_4.svg`
- `fig_rock_radial_profiles_H_over_2.png`
- `fig_rock_radial_profiles_H_over_2.svg`
- `fig_rock_radial_profiles_H.png`
- `fig_rock_radial_profiles_H.svg`

绘图使用 matplotlib，不使用 seaborn；英文和数字字体设置为 Times New Roman；所有图同时输出 PNG 和 SVG。

`diagnostics.json` 和 `summary.json` 中包含以下换热诊断参数：

- `mass_flow_rate`
- `annulus_area`
- `center_pipe_area`
- `annulus_velocity`
- `center_velocity`
- `Re_annulus`
- `Re_center`
- `h_annulus`
- `h_center`
- `U_wall`
- `U_pa`

## 井筒热阻敏感性测试

如需比较不同井筒等效热阻，可手动运行：

```bash
conda run -n geo_pinn python sensitivity_borehole_resistance.py
```

该脚本会运行：

- `R_borehole = 0.05 m*K/W`
- `R_borehole = 0.10 m*K/W`
- `R_borehole = 0.20 m*K/W`
- `R_borehole = 0.50 m*K/W`

输出目录：

```text
outputs/sensitivity_borehole_resistance
```

输出文件：

- `comparison_summary.csv`
- `fig_compare_Tout_Rborehole.png`
- `fig_compare_Tout_Rborehole.svg`
- `fig_compare_power_Rborehole.png`
- `fig_compare_power_Rborehole.svg`

## 预期物理趋势

1. `H` 增大，`Tout` 通常升高；
2. `Q` 增大，`Tout` 可能降低，但取热功率可能升高；
3. `Tin` 升高，`Tout` 升高，但温升 `Tout-Tin` 可能降低；
4. `lambda_ins` 增大，中心管向环空热短路增强，`Tout` 降低；
5. 运行时间增加，岩土热衰减增强，`Tout(t)` 通常逐渐下降并趋于稳定；
6. 岩土导热系数 `kr` 增大，长期供热能力增强，出口温度衰减减缓。

## 第一版主要简化

- 流体为准稳态，不考虑流体储热；
- 流体不考虑轴向导热；
- 岩土只做每个深度独立的一维径向导热，不考虑岩土轴向导热；
- 岩土井壁边界在主模拟中采用隐式 Robin 近似，`Ta` 使用当前时间步流体解；
- 井壁到环空换热系数用环空侧对流换热系数近似；
- 水物性取常数，不随温度变化；
- Dittus-Boelter 公式默认湍流，低 Re 时只 warning；
- 同轴套管几何和保温层参数是占位默认值。

## 后续扩展方向

- 将岩土导热从一维径向扩展到二维 `r-z` 轴对称 PDE；
- 引入温度相关水物性；
- 更精细地区分井壁热阻、套管热阻、水泥环热阻和环空换热；
- 加入季节性入口温度或运行策略；
- 将流体和岩土方程整理为 PINN 残差；
- 与 OGS 高保真模拟和纯 NN 结果做统一对比后处理。

## 如何由真实井筒结构计算 R_borehole

`R_borehole` 不是训练参数，也不应该通过拟合 OGS 结果来得到。它表示单位长度井筒等效热阻，单位为 `m*K/W`，应根据真实井筒几何、材料导热系数和流体对流换热系数估算。

第一版可以把井筒到环空流体之间的传热路径拆成若干串联热阻：

```text
R_borehole = R_conv,1 + R_layer,1 + R_layer,2 + ... + R_conv,n
```

常用单位长度圆筒导热热阻为：

```text
R_layer = ln(r_outer / r_inner) / (2*pi*k)
```

其中 `r_inner` 和 `r_outer` 为该材料层内外半径，单位 `m`；`k` 为材料导热系数，单位 `W/(m*K)`。

圆柱面对流换热热阻为：

```text
R_conv = 1 / (2*pi*r*h)
```

其中 `r` 为对流换热半径，单位 `m`；`h` 为对流换热系数，单位 `W/(m2*K)`。

本项目新增了 `borehole_resistance_calculator.py` 作为计算框架：

```bash
conda run -n geo_pinn python borehole_resistance_calculator.py
```

脚本中提供了三个核心函数：

- `compute_cylindrical_layer_resistance(r_inner, r_outer, k)`
- `compute_convective_resistance(radius, h)`
- `compute_total_borehole_resistance(layers, convective_terms)`

使用真实工程参数时，应把示例半径、材料导热系数和对流换热系数替换为真实井筒结构数据。计算得到的 `R_borehole` 可以再手动填入 `config.py` 的 `borehole_resistance`，当前脚本不会自动修改默认配置。
