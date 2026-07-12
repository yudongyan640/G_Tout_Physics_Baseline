"""井筒等效热阻敏感性测试脚本。

本脚本不会被其他模块自动调用。只有用户手动运行时，才会依次计算
R_borehole = 0.05, 0.10, 0.20, 0.50 m*K/W 四个 20 年单工况。

目的：
- 检查 U_wall 对初始 Tout、长期衰减和取热功率的影响；
- 判断旧模型中只使用环空侧对流换热是否导致 U_wall 过大。
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from config import ModelConfig
from postprocess import _set_plot_style
from simulation import SimulationResult, run_simulation


def _save_compare_figure(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    """同时保存敏感性对比图的 PNG 和 SVG 文件。"""

    fig.savefig(output_dir / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.svg", bbox_inches="tight")
    plt.close(fig)


def _collect_summary_row(result: SimulationResult, borehole_resistance: float) -> dict[str, float]:
    """从单个模拟结果中提取敏感性汇总指标。"""

    return {
        "R_borehole": float(borehole_resistance),
        "U_wall": float(result.heat_transfer.U_wall),
        "final_Tout": float(result.Tout[-1]),
        "mean_Tout": float(result.Tout.mean()),
        "max_Tout": float(result.Tout.max()),
        "final_power_W": float(result.power_W[-1]),
        "mean_power_W": float(result.power_W.mean()),
        "cumulative_energy_MWh": float(result.cumulative_energy_J[-1] / 3.6e9),
    }


def main() -> None:
    """运行四个井筒热阻工况并保存对比结果。"""

    _set_plot_style()

    base_config = ModelConfig(
        H=2500.0,
        Q=30.0,
        Tin=10.0,
        t_end_years=20.0,
        dt_days=30.0,
        use_effective_borehole_resistance=True,
    )

    resistance_values = [0.05, 0.10, 0.20, 0.50]
    output_dir = Path(base_config.output_root) / "sensitivity_borehole_resistance"
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[tuple[float, SimulationResult]] = []
    summary_rows: list[dict[str, float]] = []

    for resistance in resistance_values:
        # replace 会复制基础配置，只改变当前敏感性参数。
        config = replace(base_config, borehole_resistance=resistance)
        print(f"Running R_borehole = {resistance:.3f} m*K/W ...")
        result = run_simulation(config)
        results.append((resistance, result))
        summary_rows.append(_collect_summary_row(result, resistance))

    comparison = pd.DataFrame(summary_rows)
    comparison.to_csv(output_dir / "comparison_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for resistance, result in results:
        ax.plot(result.time_years, result.Tout, linewidth=1.8, label=f"R={resistance:.2f} m*K/W")
    ax.set_xlabel("Time (years)")
    ax.set_ylabel("Outlet temperature (degC)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    _save_compare_figure(fig, output_dir, "fig_compare_Tout_Rborehole")

    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for resistance, result in results:
        ax.plot(result.time_years, result.power_W / 1000.0, linewidth=1.8, label=f"R={resistance:.2f} m*K/W")
    ax.set_xlabel("Time (years)")
    ax.set_ylabel("Heat extraction power (kW)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    _save_compare_figure(fig, output_dir, "fig_compare_power_Rborehole")

    print(f"Sensitivity outputs saved to: {output_dir}")


if __name__ == "__main__":
    main()
