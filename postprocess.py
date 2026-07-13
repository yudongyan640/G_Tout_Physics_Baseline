"""
Module name:
    postprocess.py

Purpose:
    Save simulation results to CSV, JSON, and generate publication-quality
    figures in both PNG and SVG formats.

    All plots use matplotlib (no seaborn) with Times New Roman fonts for
    English text and numbers, following scientific figure conventions.

Dependencies:
    - config.ModelConfig
    - simulation.SimulationResult
    - matplotlib, numpy, pandas

Outputs:
    - tout_timeseries.csv
    - fluid_profiles.csv
    - diagnostics.json
    - summary.json
    - Multiple PNG and SVG figures (Tout vs time, power vs time,
      fluid temperature profiles, rock radial profiles).
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import ModelConfig
from simulation import SimulationResult


def get_case_output_dir(config: ModelConfig) -> Path:
    """返回当前工况输出目录，并确保目录存在。"""

    output_dir = Path(config.output_root) / config.case_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _set_plot_style() -> None:
    """设置科研绘图风格。"""

    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 11
    plt.rcParams["axes.labelsize"] = 12
    plt.rcParams["legend.fontsize"] = 10


def _save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    """同时保存 PNG 和 SVG 图片。"""

    fig.savefig(output_dir / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.svg", bbox_inches="tight")
    plt.close(fig)


def build_diagnostics(result: SimulationResult) -> dict[str, float | bool]:
    """Generate heat-transfer and flow diagnostics.

    These quantities help verify whether U_wall is reasonable, flow velocities
    are physically plausible, and the Dittus-Boelter correlation is operating
    within its turbulent range.

    Parameters
    ----------
    result : SimulationResult
        Complete simulation output.

    Returns
    -------
    dict
        Diagnostic metrics including mass flow rate, areas, velocities,
        Reynolds numbers, convective coefficients, and U_wall/U_pa.
    """

    heat_transfer = result.heat_transfer
    geometry = heat_transfer.geometry
    config = result.config
    return {
        "mass_flow_rate": float(geometry.m_dot),
        "annulus_area": float(geometry.annulus_area),
        "center_pipe_area": float(geometry.center_area),
        "annulus_velocity": float(geometry.annulus_velocity),
        "center_velocity": float(geometry.center_velocity),
        "Re_annulus": float(heat_transfer.Re_annulus),
        "Re_center": float(heat_transfer.Re_center),
        "h_annulus": float(heat_transfer.h_outer),
        "h_center": float(heat_transfer.h_inner),
        "U_wall": float(heat_transfer.U_wall),
        "U_pa": float(heat_transfer.U_pa),
        "use_effective_borehole_resistance": bool(config.use_effective_borehole_resistance),
        "borehole_resistance": float(config.borehole_resistance),
    }


def format_diagnostics_text(diagnostics: dict[str, float | bool]) -> str:
    """把诊断参数整理成适合终端打印的文本。"""

    lines = ["Heat-transfer diagnostics", "-------------------------"]
    for key, value in diagnostics.items():
        if isinstance(value, bool):
            lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {value:.6g}")
    return "\n".join(lines)


def _nearest_index(values: np.ndarray, target: float) -> int:
    """返回最接近目标时间的数组下标。"""

    return int(np.argmin(np.abs(values - target)))


def _mean_after_threshold(values: np.ndarray, time_days: np.ndarray, threshold_days: float) -> float:
    """计算指定天数之后的平均值。

    如果模拟总时长短于阈值，就退回使用最后一个时间点，避免短测试输出 NaN。
    """

    mask = time_days >= threshold_days
    if not np.any(mask):
        return float(values[-1])
    return float(np.mean(values[mask]))


def _max_after_threshold(values: np.ndarray, time_days: np.ndarray, threshold_days: float) -> float:
    """计算指定天数之后的最大值，用于减弱启动峰值对 max 指标的影响。"""

    mask = time_days >= threshold_days
    if not np.any(mask):
        return float(values[-1])
    return float(np.max(values[mask]))


def build_time_based_metrics(result: SimulationResult) -> dict[str, float]:
    """生成固定时间点和去启动期评价指标。

    固定时间点不要求恰好落在模拟时间步上；如果没有完全对应的数据，
    使用最接近的时间点，并同时记录实际采用的 time_days 或 time_years。
    """

    metrics: dict[str, float] = {}
    day_targets = {
        "day_1": 1.0,
        "day_7": 7.0,
        "day_30": 30.0,
        "day_90": 90.0,
    }
    year_targets = {
        "year_1": 1.0,
        "year_5": 5.0,
        "year_10": 10.0,
        "year_20": 20.0,
    }

    for label, target_day in day_targets.items():
        index = _nearest_index(result.time_days, target_day)
        actual_day = float(result.time_days[index])
        metrics[f"Tout_{label}"] = float(result.Tout[index])
        metrics[f"Tout_{label}_actual_time_days"] = actual_day
        metrics[f"power_{label}"] = float(result.power_W[index])
        metrics[f"power_{label}_actual_time_days"] = actual_day

    for label, target_year in year_targets.items():
        index = _nearest_index(result.time_years, target_year)
        actual_year = float(result.time_years[index])
        metrics[f"Tout_{label}"] = float(result.Tout[index])
        metrics[f"Tout_{label}_actual_time_years"] = actual_year
        metrics[f"power_{label}"] = float(result.power_W[index])
        metrics[f"power_{label}_actual_time_years"] = actual_year

    metrics["mean_Tout_after_30_days"] = _mean_after_threshold(result.Tout, result.time_days, 30.0)
    metrics["mean_Tout_after_1_year"] = _mean_after_threshold(result.Tout, result.time_days, 365.0)
    metrics["mean_power_after_30_days"] = _mean_after_threshold(result.power_W, result.time_days, 30.0)
    metrics["mean_power_after_1_year"] = _mean_after_threshold(result.power_W, result.time_days, 365.0)
    metrics["max_Tout_after_30_days"] = _max_after_threshold(result.Tout, result.time_days, 30.0)
    metrics["max_power_after_30_days"] = _max_after_threshold(result.power_W, result.time_days, 30.0)

    return metrics


def _build_summary(result: SimulationResult) -> dict[str, object]:
    """生成 summary.json 所需的关键指标。"""

    config = result.config
    summary = {
        "H": config.H,
        "Q": config.Q,
        "Tin": config.Tin,
        "Tamb": config.Tamb,
        "G": config.G,
        "t_end_years": config.t_end_years,
        "final_Tout": float(result.Tout[-1]),
        "max_Tout": float(result.Tout.max()),
        "mean_Tout": float(result.Tout.mean()),
        "final_power_W": float(result.power_W[-1]),
        "mean_power_W": float(result.power_W.mean()),
        "cumulative_energy_J": float(result.cumulative_energy_J[-1]),
        "cumulative_energy_MWh": float(result.cumulative_energy_J[-1] / 3.6e9),
        "diagnostics": build_diagnostics(result),
    }
    summary.update(build_time_based_metrics(result))
    return summary


def _plot_rock_radial_profiles(result: SimulationResult, output_dir: Path) -> None:
    """绘制 H/4、H/2、H 处岩土径向温度剖面。

    每张图包含第 0、1、5、10、20 年附近保存的 Ts(r)。
    如果模拟时间短于某些年份，则自动跳过缺失年份。
    """

    depth_cases = [
        (0.25 * result.config.H, "H_over_4"),
        (0.50 * result.config.H, "H_over_2"),
        (1.00 * result.config.H, "H"),
    ]

    for target_depth, file_suffix in depth_cases:
        z_index = int(abs(result.grid.z - target_depth).argmin())
        actual_depth = float(result.grid.z[z_index])

        fig, ax = plt.subplots(figsize=(6.2, 4.2))
        for target_year in sorted(result.rock_temperature_snapshots):
            Ts_snapshot = result.rock_temperature_snapshots[target_year]
            actual_year = result.rock_snapshot_actual_years.get(target_year, target_year)
            label = f"{target_year:g} yr (actual {actual_year:.2f})"
            ax.semilogx(result.grid.r, Ts_snapshot[:, z_index], linewidth=1.8, label=label)

        ax.set_xlabel("Radius r (m)")
        ax.set_ylabel("Rock temperature (degC)")
        ax.set_title(f"Radial rock temperature at z = {actual_depth:.0f} m")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend()
        _save_figure(fig, output_dir, f"fig_rock_radial_profiles_{file_suffix}")


def save_outputs(result: SimulationResult, config: ModelConfig | None = None) -> Path:
    """Save simulation results (CSV, JSON) and figures (PNG, SVG).

    Parameters
    ----------
    result : SimulationResult
        Complete simulation output.
    config : ModelConfig or None
        Configuration (defaults to result.config if None).

    Returns
    -------
    Path
        Output directory containing all saved files.
    """

    if config is None:
        config = result.config

    _set_plot_style()
    output_dir = get_case_output_dir(config)

    timeseries = pd.DataFrame(
        {
            "time_s": result.time_s,
            "time_days": result.time_days,
            "time_years": result.time_years,
            "Tout_degC": result.Tout,
            "power_W": result.power_W,
            "cumulative_energy_J": result.cumulative_energy_J,
        }
    )
    timeseries.to_csv(output_dir / "tout_timeseries.csv", index=False)

    fluid_profiles = pd.DataFrame(
        {
            "z_m": result.grid.z,
            "Ta_degC": result.final_Ta,
            "Tp_degC": result.final_Tp,
            "Twall_initial_degC": result.initial_Twall,
            "Twall_final_degC": result.final_Twall,
            "q_wall_W_per_m": result.final_q_wall,
        }
    )
    fluid_profiles.to_csv(output_dir / "fluid_profiles.csv", index=False)

    diagnostics = build_diagnostics(result)
    with (output_dir / "diagnostics.json").open("w", encoding="utf-8") as f:
        json.dump(diagnostics, f, ensure_ascii=False, indent=2)

    summary = _build_summary(result)
    with (output_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.plot(result.time_years, result.Tout, color="tab:red", linewidth=2.0)
    ax.set_xlabel("Time (years)")
    ax.set_ylabel("Outlet temperature (degC)")
    ax.grid(True, alpha=0.3)
    _save_figure(fig, output_dir, "fig_tout_vs_time")

    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.plot(result.time_years, result.power_W / 1000.0, color="tab:blue", linewidth=2.0)
    ax.set_xlabel("Time (years)")
    ax.set_ylabel("Heat extraction power (kW)")
    ax.grid(True, alpha=0.3)
    _save_figure(fig, output_dir, "fig_power_vs_time")

    fig, ax = plt.subplots(figsize=(5.0, 6.0))
    ax.plot(result.final_Ta, result.grid.z, label="Annulus Ta", linewidth=2.0)
    ax.plot(result.final_Tp, result.grid.z, label="Center pipe Tp", linewidth=2.0)
    ax.plot(result.final_Twall, result.grid.z, label="Wall Twall", linewidth=1.8, linestyle="--")
    ax.invert_yaxis()
    ax.set_xlabel("Temperature (degC)")
    ax.set_ylabel("Depth z (m)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    _save_figure(fig, output_dir, "fig_fluid_profiles")

    _plot_rock_radial_profiles(result, output_dir)

    return output_dir
