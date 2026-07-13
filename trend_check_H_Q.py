"""
Module name:
    trend_check_H_Q.py

Purpose:
    Perform a 3×3 H-Q trend verification using only the physics-based model.

    Eight operating points are simulated:
        H = [2000, 2500, 3000] m
        Q = [15, 30, 40] m3/h

    Verification targets:
        1. Larger H → higher Tout (stronger geothermal input).
        2. Larger Q → lower Tout (shorter residence time per kg of fluid).
        3. Larger Q → higher mean heat extraction power (higher mass flow rate).

    This is NOT a batch production script; it verifies basic physical trends.

Dependencies:
    - config.ModelConfig
    - simulation.run_simulation
    - postprocess.build_time_based_metrics
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import ModelConfig
from postprocess import build_time_based_metrics
from simulation import SimulationResult, run_simulation


H_LIST = [2000.0, 2500.0, 3000.0]
Q_LIST = [15.0, 30.0, 40.0]
TIN = 10.0
R_BOREHOLE = 0.10
OUTPUT_DIR = Path("outputs") / "trend_check_H_Q"


def expected_output_files() -> list[Path]:
    """返回本脚本应生成的全部文件，便于自动检查和人工核对。"""

    return [
        OUTPUT_DIR / "trend_summary.csv",
        OUTPUT_DIR / "fig_Tout_vs_time_H_Q.png",
        OUTPUT_DIR / "fig_Tout_vs_time_H_Q.svg",
        OUTPUT_DIR / "fig_final_Tout_heatmap.png",
        OUTPUT_DIR / "fig_final_Tout_heatmap.svg",
        OUTPUT_DIR / "fig_mean_power_heatmap.png",
        OUTPUT_DIR / "fig_mean_power_heatmap.svg",
    ]


def _set_plot_style() -> None:
    """设置图形字体和基础样式，不使用 seaborn。"""

    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 11
    plt.rcParams["axes.labelsize"] = 12
    plt.rcParams["legend.fontsize"] = 9


def _save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    """同时输出 PNG 和 SVG 两种格式。"""

    fig.savefig(output_dir / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.svg", bbox_inches="tight")
    plt.close(fig)


def _build_case_config(H: float, Q: float) -> ModelConfig:
    """根据 H 和 Q 生成单个趋势验证工况配置。"""

    return replace(
        ModelConfig(),
        H=H,
        Q=Q,
        Tin=TIN,
        borehole_resistance=R_BOREHOLE,
        use_effective_borehole_resistance=True,
        t_end_years=20.0,
        dt_days=30.0,
    )


def _collect_summary_row(result: SimulationResult) -> dict[str, float]:
    """从单个模拟结果中提取趋势验证表格所需指标。"""

    config = result.config
    time_metrics = build_time_based_metrics(result)
    return {
        "H": float(config.H),
        "Q": float(config.Q),
        "Tin": float(config.Tin),
        "R_borehole": float(config.borehole_resistance),
        "final_Tout": float(result.Tout[-1]),
        "mean_Tout": float(result.Tout.mean()),
        "mean_Tout_after_1_year": float(time_metrics["mean_Tout_after_1_year"]),
        "final_power_W": float(result.power_W[-1]),
        "mean_power_W": float(result.power_W.mean()),
        "mean_power_after_1_year": float(time_metrics["mean_power_after_1_year"]),
        "cumulative_energy_MWh": float(result.cumulative_energy_J[-1] / 3.6e9),
    }


def _plot_tout_curves(results: list[tuple[float, float, SimulationResult]], output_dir: Path) -> None:
    """绘制 9 个 H-Q 工况的 Tout(t) 对比曲线。"""

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    for H, Q, result in results:
        ax.plot(result.time_years, result.Tout, linewidth=1.5, label=f"H={H:.0f} m, Q={Q:.0f} m3/h")
    ax.set_xlabel("Time (years)")
    ax.set_ylabel("Outlet temperature (degC)")
    ax.grid(True, alpha=0.3)
    ax.legend(ncol=2)
    _save_figure(fig, output_dir, "fig_Tout_vs_time_H_Q")


def _plot_heatmap(table: pd.DataFrame, value_column: str, output_dir: Path, stem: str, colorbar_label: str) -> None:
    """绘制 H-Q 矩阵热力图。

    横轴是 Q，纵轴是 H；每个格子标注对应指标数值。
    """

    heatmap = table.pivot(index="H", columns="Q", values=value_column).loc[H_LIST, Q_LIST]
    values = heatmap.to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(5.6, 4.4))
    image = ax.imshow(values, origin="lower", aspect="auto", cmap="viridis")
    ax.set_xticks(np.arange(len(Q_LIST)), labels=[f"{q:.0f}" for q in Q_LIST])
    ax.set_yticks(np.arange(len(H_LIST)), labels=[f"{h:.0f}" for h in H_LIST])
    ax.set_xlabel("Flow rate Q (m3/h)")
    ax.set_ylabel("Depth H (m)")

    for row_index, H in enumerate(H_LIST):
        for col_index, Q in enumerate(Q_LIST):
            ax.text(col_index, row_index, f"{heatmap.loc[H, Q]:.2f}", ha="center", va="center", color="white")

    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label(colorbar_label)
    _save_figure(fig, output_dir, stem)


def save_trend_outputs(results: list[tuple[float, float, SimulationResult]], output_dir: Path = OUTPUT_DIR) -> pd.DataFrame:
    """保存趋势验证表格和图像。"""

    output_dir.mkdir(parents=True, exist_ok=True)
    _set_plot_style()

    summary = pd.DataFrame([_collect_summary_row(result) for _, _, result in results])
    summary = summary.sort_values(["H", "Q"]).reset_index(drop=True)
    summary.to_csv(output_dir / "trend_summary.csv", index=False)

    _plot_tout_curves(results, output_dir)
    _plot_heatmap(summary, "final_Tout", output_dir, "fig_final_Tout_heatmap", "Final Tout (degC)")
    _plot_heatmap(summary, "mean_power_W", output_dir, "fig_mean_power_heatmap", "Mean power (W)")
    return summary


def print_trend_report(summary: pd.DataFrame) -> None:
    """打印简短趋势报告，帮助快速判断 3x3 结果是否合理。"""

    h_checks = []
    q_tout_checks = []
    q_power_checks = []

    for Q in Q_LIST:
        subset = summary[summary["Q"] == Q].sort_values("H")
        h_checks.append(bool(np.all(np.diff(subset["final_Tout"].to_numpy()) > 0.0)))

    for H in H_LIST:
        subset = summary[summary["H"] == H].sort_values("Q")
        q_tout_checks.append(bool(np.all(np.diff(subset["final_Tout"].to_numpy()) < 0.0)))
        q_power_checks.append(bool(np.all(np.diff(subset["mean_power_W"].to_numpy()) > 0.0)))

    print("Trend check report")
    print("------------------")
    print(f"H increase raises final Tout for each Q: {all(h_checks)}")
    print(f"Q increase lowers final Tout for each H: {all(q_tout_checks)}")
    print(f"Q increase raises mean power for each H: {all(q_power_checks)}")


def main() -> None:
    """运行 3x3 H-Q 趋势验证。"""

    results: list[tuple[float, float, SimulationResult]] = []
    for H in H_LIST:
        for Q in Q_LIST:
            print(f"Running H={H:.0f} m, Q={Q:.0f} m3/h ...")
            result = run_simulation(_build_case_config(H, Q))
            results.append((H, Q, result))

    summary = save_trend_outputs(results, OUTPUT_DIR)
    print_trend_report(summary)
    print(f"Trend outputs saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
