"""中深层同轴井纯物理 baseline 的单工况独立验证。

本脚本仅将 OGS 导出的井口 ``Tout(t)`` 作为参考序列，不读取 VTK/PVD 文件，
不训练、不校准也不修改任何物理模型参数。计算仍完全调用现有 baseline 求解器。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import ModelConfig
from simulation import run_simulation


# 经井口点 CSV 与 OGS 控制曲线共同确认：分量 0 是入口，分量 1 是出口水温。
OUTLET_COLUMN = "avg(temperature_BHE1 (1))"
SECONDS_PER_YEAR = 365.0 * 24.0 * 3600.0
CASE_NAME = "2501_26_11"
OGS_CSV_PATH = Path(r"E:\newdesktop\PINN\OGS_data\all_data\2501_26_11\井口处数据点.csv")
OUTPUT_DIR = Path("outputs") / "validation" / CASE_NAME


def load_ogs_outlet_data(csv_path: Path | str) -> pd.DataFrame:
    """读取导出的 OGS 时间与确认的出口温度列，并统一为秒和年。

    CSV 中可能还有土壤温度、入口温度和统计列；本函数故意只使用 ``Time`` 与
    ``avg(temperature_BHE1 (1))``，以保持参考数据范围与本次验证任务一致。
    """

    csv_path = Path(csv_path)
    data = pd.read_csv(csv_path, usecols=["Time", OUTLET_COLUMN])
    data = data.rename(columns={"Time": "time_s", OUTLET_COLUMN: "ogs_Tout_degC"})
    data["time_s"] = pd.to_numeric(data["time_s"], errors="coerce")
    data["ogs_Tout_degC"] = pd.to_numeric(data["ogs_Tout_degC"], errors="coerce")
    data = data.dropna().sort_values("time_s").drop_duplicates("time_s").reset_index(drop=True)
    if data.empty:
        raise ValueError("OGS CSV 中没有可用的 Time 和出口水温数据。")
    if not data["time_s"].is_monotonic_increasing:
        raise ValueError("OGS 时间序列无法按时间递增排序。")
    data["time_years"] = data["time_s"] / SECONDS_PER_YEAR
    return data


def calculate_metrics(predicted: np.ndarray, reference: np.ndarray) -> dict[str, float]:
    """按任务指定公式计算 MAE、RMSE、R2 和 Bias。"""

    predicted = np.asarray(predicted, dtype=float)
    reference = np.asarray(reference, dtype=float)
    if predicted.shape != reference.shape or predicted.size == 0:
        raise ValueError("预测值和参考值必须为相同长度的非空数组。")
    if not np.isfinite(predicted).all() or not np.isfinite(reference).all():
        raise ValueError("预测值或参考值含有非有限数值。")

    error = predicted - reference
    sse = float(np.sum(error**2))
    sst = float(np.sum((reference - np.mean(reference)) ** 2))
    return {
        "MAE_degC": float(np.mean(np.abs(error))),
        "RMSE_degC": float(np.sqrt(np.mean(error**2))),
        "Bias_degC": float(np.mean(error)),
        "R2": float(1.0 - sse / sst) if sst > 0.0 else float("nan"),
    }


def build_validation_config(ogs_end_time_s: float) -> ModelConfig:
    """创建验证工况配置，只覆盖用户指定的 H/Q/Tin 与结束时间。

    ``ModelConfig()`` 先读取当前已验证的 OGS 物理参数映射，其中包括既有
    R_borehole、U_wall 和 U_pa 对应的热阻设置；随后仅设置本验证算例的工况。
    """

    config = ModelConfig()
    config.H = 2501.0
    config.Q = 26.0
    config.Tin = 11.0
    config.t_end_years = float(ogs_end_time_s) / SECONDS_PER_YEAR
    return config


def _set_plot_style() -> None:
    """设置英文科研绘图字体和清晰的高分辨率输出样式。"""

    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 11


def _save_figure(figure: plt.Figure, stem: str) -> None:
    """同时保存验证图的 PNG 与 SVG 格式。"""

    figure.savefig(OUTPUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")
    figure.savefig(OUTPUT_DIR / f"{stem}.svg", bbox_inches="tight")
    plt.close(figure)


def _write_metrics(metrics: dict[str, float], sample_count: int) -> None:
    """将四项指标以可直接查看的文本格式写入验证目录。"""

    (OUTPUT_DIR / "Metrics_summary.txt").write_text(
        "\n".join(
            [
                f"Case: {CASE_NAME}",
                f"Aligned samples: {sample_count}",
                f"MAE: {metrics['MAE_degC']:.6f} degC",
                f"RMSE: {metrics['RMSE_degC']:.6f} degC",
                f"R2: {metrics['R2']:.6f}",
                f"Bias: {metrics['Bias_degC']:.6f} degC",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _write_report(metrics: dict[str, float], aligned: pd.DataFrame, config: ModelConfig) -> None:
    """生成客观的 Markdown 验证报告，不预设模型优劣结论。"""

    report_path = Path("docs") / f"validation_{CASE_NAME}.md"
    report_path.write_text(
        f"""# Physics Baseline Validation: {CASE_NAME}

## 1. Case information

- Borehole depth: {config.H:.0f} m
- Flow rate: {config.Q:.0f} m3/h
- Inlet temperature: {config.Tin:.0f} degC
- Comparison period: 0 to {aligned['time_years'].iloc[-1]:.6f} year
- Aligned samples: {len(aligned)}

## 2. Physics baseline configuration

- The existing physics solver was used without changes to its PDE/ODE equations.
- Existing mapped resistance settings were retained: `R_borehole={config.borehole_resistance:.9f} m*K/W` and `R_short_circuit={config.short_circuit_resistance:.9f} m*K/W`.
- The requested case inputs were set to H=2501 m, Q=26 m3/h, and Tin=11 degC.

## 3. OGS reference data

- Source: `E:/newdesktop/PINN/OGS_data/all_data/2501_26_11/井口处数据点.csv`
- Time column: `Time` in seconds, converted using 365 days/year.
- Outlet-temperature column: `avg(temperature_BHE1 (1))` in degC.
- OGS values were linearly interpolated onto the baseline 30-day time grid; no OGS field data was read.

## 4. Comparison results

| Metric | Value |
|---|---:|
| MAE (degC) | {metrics['MAE_degC']:.6f} |
| RMSE (degC) | {metrics['RMSE_degC']:.6f} |
| R2 | {metrics['R2']:.6f} |
| Bias (degC) | {metrics['Bias_degC']:.6f} |

## 5. Error analysis

The error curve is defined as `Physics baseline - OGS`. Positive values mean the physics baseline predicts a higher outlet temperature than the OGS reference at the aligned time point; negative values mean the opposite.

## 6. Possible reasons

- The OGS reference includes its prescribed on/off operating schedule, while the current physics baseline is a continuous single-operating-condition solver.
- The physics baseline uses one-dimensional radial rock conduction and simplified fluid heat-transfer correlations.
- The two models use different spatial representations and boundary-condition implementations.

These items are possible structural differences, not parameter adjustments or calibration actions.
""",
        encoding="utf-8",
    )


def run_validation() -> dict[str, Any]:
    """执行一次完整验证并返回指标、路径与对齐数据量。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ogs = load_ogs_outlet_data(OGS_CSV_PATH)
    config = build_validation_config(float(ogs["time_s"].iloc[-1]))
    result = run_simulation(config)

    # OGS 输出时间点更密；插值到 baseline 时间网格使每一行一一对应。
    ogs_on_physics_grid = np.interp(result.time_s, ogs["time_s"], ogs["ogs_Tout_degC"])
    aligned = pd.DataFrame(
        {
            "time_s": result.time_s,
            "time_years": result.time_years,
            "physics_Tout_degC": result.Tout,
            "ogs_Tout_degC": ogs_on_physics_grid,
        }
    )
    aligned["temperature_error_degC"] = aligned["physics_Tout_degC"] - aligned["ogs_Tout_degC"]
    aligned.to_csv(OUTPUT_DIR / "physics_Tout.csv", index=False)
    metrics = calculate_metrics(aligned["physics_Tout_degC"].to_numpy(), aligned["ogs_Tout_degC"].to_numpy())

    _set_plot_style()
    figure, axis = plt.subplots(figsize=(7.2, 4.5))
    axis.plot(aligned["time_years"], aligned["ogs_Tout_degC"], label="OGS", linewidth=2.0, color="#1f77b4")
    axis.plot(aligned["time_years"], aligned["physics_Tout_degC"], label="Physics baseline", linewidth=2.0, color="#d62728")
    axis.set_xlabel("Time (year)")
    axis.set_ylabel("Outlet temperature (°C)")
    axis.grid(True, alpha=0.3)
    axis.legend()
    _save_figure(figure, "Tout_comparison")

    figure, axis = plt.subplots(figsize=(7.2, 4.5))
    axis.axhline(0.0, color="black", linewidth=1.0)
    axis.plot(aligned["time_years"], aligned["temperature_error_degC"], linewidth=1.8, color="#9467bd")
    axis.set_xlabel("Time (year)")
    axis.set_ylabel("Temperature error (°C)")
    axis.grid(True, alpha=0.3)
    _save_figure(figure, "Error_curve")

    _write_metrics(metrics, len(aligned))
    _write_report(metrics, aligned, config)
    return {"metrics": metrics, "output_dir": OUTPUT_DIR, "samples": len(aligned)}


def main() -> None:
    """命令行入口：执行一次指定工况验证并打印指标。"""

    validation = run_validation()
    print(f"Validation outputs saved to: {validation['output_dir']}")
    print(f"Aligned samples: {validation['samples']}")
    for name, value in validation["metrics"].items():
        print(f"{name}: {value:.6f}")


if __name__ == "__main__":
    main()
