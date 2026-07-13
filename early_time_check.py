"""
Module name:
    early_time_check.py

Purpose:
    Examine the rapid outlet temperature drop during the first year by using
    a finer time step (1 day instead of the default 30 days).

    This script runs only the physics-based baseline and does NOT read any
    OGS output files. Results help determine whether the initial Tout decline
    is primarily caused by a coarse time step.

Dependencies:
    - config.ModelConfig
    - simulation.run_simulation
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from config import ModelConfig
from simulation import SimulationResult, run_simulation


# 本检查任务固定输出到 outputs/early_time_check，避免和 20 年默认工况混在一起。
OUTPUT_DIR = Path("outputs") / "early_time_check"


def build_early_time_config() -> ModelConfig:
    """构造前 1 年时间步敏感性检查所需的固定工况。

    参数含义：
    - H=2500 m：井深与默认单工况一致；
    - Q=30 m3/h：入口体积流量与默认单工况一致；
    - Tin=10 degC：入口水温与默认单工况一致；
    - t_end_years=1：只看前 1 年，不做长期批量计算；
    - dt_days=1：把时间步缩小到 1 天；
    - Nz=201, Nr=80：使用用户指定的轴向和径向网格。
    """

    return replace(
        ModelConfig(),
        H=2500.0,
        Q=30.0,
        Tin=10.0,
        t_end_years=1.0,
        dt_days=1.0,
        Nz=201,
        Nr=80,
    )


def expected_output_files() -> list[Path]:
    """返回本脚本应该生成的全部文件路径，便于人工检查和自动测试。"""

    return [
        OUTPUT_DIR / "tout_timeseries.csv",
        OUTPUT_DIR / "fig_tout_first_year.png",
        OUTPUT_DIR / "fig_tout_first_year.svg",
        OUTPUT_DIR / "fig_power_first_year.png",
        OUTPUT_DIR / "fig_power_first_year.svg",
    ]


def _set_plot_style() -> None:
    """设置科研绘图风格，确保英文和数字优先使用 Times New Roman。"""

    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 11
    plt.rcParams["axes.labelsize"] = 12
    plt.rcParams["legend.fontsize"] = 10


def _save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    """同时保存 PNG 和 SVG，满足论文图和后续编辑两类需求。"""

    fig.savefig(output_dir / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.svg", bbox_inches="tight")
    plt.close(fig)


def save_early_time_outputs(result: SimulationResult, output_dir: Path = OUTPUT_DIR) -> None:
    """保存前 1 年检查所需的 CSV 和图像。

    这里只输出任务指定文件，不调用 postprocess.save_outputs，
    因为通用后处理会额外写入流体剖面、summary 和岩土剖面图。
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    _set_plot_style()

    # 保存逐时间步序列，后续可直接与 30 天时间步结果对比。
    timeseries = pd.DataFrame(
        {
            "time_s": result.time_s,
            "time_days": result.time_days,
            "time_years": result.time_years,
            "Tout_degC": result.Tout,
            "power_W": result.power_W,
            "cumulative_energy_J": result.cumulative_energy_J,
            "cumulative_energy_MWh": result.cumulative_energy_J / 3.6e9,
        }
    )
    timeseries.to_csv(output_dir / "tout_timeseries.csv", index=False)

    # 出口水温图：横坐标用天，便于观察前期快速下降阶段。
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot(result.time_days, result.Tout, color="tab:red", linewidth=2.0)
    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Outlet temperature (degC)")
    ax.grid(True, alpha=0.3)
    _save_figure(fig, output_dir, "fig_tout_first_year")

    # 取热功率图：单位换成 kW，数值更直观。
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot(result.time_days, result.power_W / 1000.0, color="tab:blue", linewidth=2.0)
    ax.set_xlabel("Time (days)")
    ax.set_ylabel("Heat extraction power (kW)")
    ax.grid(True, alpha=0.3)
    _save_figure(fig, output_dir, "fig_power_first_year")


def print_early_time_summary(result: SimulationResult, output_dir: Path = OUTPUT_DIR) -> None:
    """在终端打印关键数值，帮助快速判断前 1 年衰减幅度。"""

    initial_tout = float(result.Tout[0])
    final_tout = float(result.Tout[-1])
    max_tout = float(result.Tout.max())
    mean_tout = float(result.Tout.mean())
    final_power = float(result.power_W[-1])
    mean_power = float(result.power_W.mean())
    cumulative_energy_mwh = float(result.cumulative_energy_J[-1] / 3.6e9)

    print("Early-time check summary")
    print("------------------------")
    print(f"Output directory: {output_dir}")
    print(f"Initial Tout: {initial_tout:.6f} degC")
    print(f"Final Tout: {final_tout:.6f} degC")
    print(f"Max Tout: {max_tout:.6f} degC")
    print(f"Mean Tout: {mean_tout:.6f} degC")
    print(f"Tout drop in first year: {initial_tout - final_tout:.6f} K")
    print(f"Final power: {final_power:.6f} W")
    print(f"Mean power: {mean_power:.6f} W")
    print(f"Cumulative energy: {cumulative_energy_mwh:.6f} MWh")


def main() -> None:
    """运行前 1 年、1 天时间步的纯物理检查工况。"""

    config = build_early_time_config()
    result = run_simulation(config)
    save_early_time_outputs(result, OUTPUT_DIR)
    print_early_time_summary(result, OUTPUT_DIR)


if __name__ == "__main__":
    main()
