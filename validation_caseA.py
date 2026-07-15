"""Case A（全年连续运行）Physics baseline 独立验证。

本脚本仅读取 OGS 在井口导出的 ``Time`` 和
``avg(temperature_BHE1 (1))`` 两列作为验证参考；不会读取 .vtu、.pvd
或任何岩土温度场数据，也不会改写 Physics baseline 的物理模型参数。
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import ModelConfig
from simulation import run_simulation


# 只允许读取用户指定的 OGS 井口导出列，避免接触温度场信息。
OUTLET_COLUMN = "avg(temperature_BHE1 (1))"
SECONDS_PER_YEAR = 365.0 * 24.0 * 3600.0
CASE_NAME = "caseA_2501_26_11"
CASE_ROOT = Path("2501_26_11")
OGS_PROJECT_PATH = CASE_ROOT / "DBHE.prj"
OGS_CSV_PATH = CASE_ROOT / "optimized_results" / "井口参数.csv"
OUTPUT_DIR = Path("outputs") / "validation" / CASE_NAME
DATA_DESCRIPTION_PATH = Path("docs") / "caseA_ogs_data_description.md"
REPORT_PATH = Path("docs") / "validation_caseA_2501_26_11.md"


def load_ogs_outlet_data(csv_path: Path | str) -> pd.DataFrame:
    """读取 OGS 导出的时间与出口水温，并统一时间单位为 year。

    通过 ``usecols`` 明确限制 pandas 只访问允许的两列。返回表格按时间
    升序排列，列名统一为 ``time_s``、``time_years`` 和 ``ogs_Tout_degC``。
    """

    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"未找到 OGS 出口水温 CSV：{csv_path}")

    try:
        data = pd.read_csv(csv_path, usecols=["Time", OUTLET_COLUMN])
    except ValueError as error:
        raise ValueError(
            "OGS CSV 缺少验证所需列：Time 或 "
            f"{OUTLET_COLUMN!r}；未读取其他数据，也未猜测数据格式。"
        ) from error

    data = data.rename(columns={"Time": "time_s", OUTLET_COLUMN: "ogs_Tout_degC"})
    data["time_s"] = pd.to_numeric(data["time_s"], errors="coerce")
    data["ogs_Tout_degC"] = pd.to_numeric(data["ogs_Tout_degC"], errors="coerce")
    data = data.dropna().sort_values("time_s").drop_duplicates("time_s").reset_index(drop=True)
    if data.empty:
        raise ValueError("OGS CSV 中没有可用的时间和出口水温数据。")
    if not data["time_s"].is_monotonic_increasing:
        raise ValueError("OGS 时间序列无法按升序整理。")

    data["time_years"] = data["time_s"] / SECONDS_PER_YEAR
    return data[["time_s", "time_years", "ogs_Tout_degC"]]


def build_caseA_config() -> ModelConfig:
    """构建 Case A 的 20 年连续运行配置，不改变任何已映射物理参数。

    ``ModelConfig()`` 仍先加载当前 ``config.py`` 中启用的 OGS 参数映射。
    本函数只覆盖用户指定的运行工况 H、Q、Tin 和 20 年模拟时长；热阻及
    PDE/ODE 求解设置均保持原始状态。
    """

    config = ModelConfig()
    config.H = 2501.0
    config.Q = 26.0
    config.Tin = 11.0
    config.t_end_years = 20.0
    return config


def calculate_metrics(predicted: np.ndarray, reference: np.ndarray) -> dict[str, float]:
    """按任务给定公式计算 MAE、RMSE、R2 与 Bias。"""

    predicted = np.asarray(predicted, dtype=float)
    reference = np.asarray(reference, dtype=float)
    if predicted.shape != reference.shape or predicted.size == 0:
        raise ValueError("预测值与参考值必须为长度相同的非空数组。")
    if not np.isfinite(predicted).all() or not np.isfinite(reference).all():
        raise ValueError("预测值或参考值含有非有限数。")

    error = predicted - reference
    sse = float(np.sum(error**2))
    sst = float(np.sum((reference - np.mean(reference)) ** 2))
    return {
        "MAE_degC": float(np.mean(np.abs(error))),
        "RMSE_degC": float(np.sqrt(np.mean(error**2))),
        "R2": float(1.0 - sse / sst) if sst > 0.0 else float("nan"),
        "Bias_degC": float(np.mean(error)),
    }


def _read_project_boundary_conditions(project_path: Path) -> dict[str, str]:
    """从 OGS 项目 XML 读取 Case A 的井深与恒定控制曲线。"""

    if not project_path.exists():
        raise FileNotFoundError(f"未找到 OGS 项目文件：{project_path}")
    root = ET.parse(project_path).getroot()
    depth = root.findtext(".//borehole/length")
    curves: dict[str, tuple[str, str]] = {}
    for curve in root.findall(".//curves/curve"):
        name = curve.findtext("name")
        coords = curve.findtext("coords")
        values = curve.findtext("values")
        if name and coords and values:
            curves[name] = (" ".join(coords.split()), " ".join(values.split()))

    if depth is None or "temperature_curve" not in curves or "flow_rate_curve" not in curves:
        raise ValueError("DBHE.prj 缺少 Case A 所需 borehole 或控制曲线定义。")
    return {
        "depth_m": depth.strip(),
        "temperature_coords_s": curves["temperature_curve"][0],
        "temperature_values_degC": curves["temperature_curve"][1],
        "flow_coords_s": curves["flow_rate_curve"][0],
        "flow_values_m3s": curves["flow_rate_curve"][1],
    }


def _set_plot_style() -> None:
    """设置英文和数字均使用 Times New Roman 的论文绘图风格。"""

    plt.rcParams["font.family"] = "Times New Roman"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 11
    plt.rcParams["axes.labelsize"] = 12
    plt.rcParams["legend.fontsize"] = 10


def _save_figure(figure: plt.Figure, stem: str) -> None:
    """以 PNG 和 SVG 两种格式保存单张验证图。"""

    figure.savefig(OUTPUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")
    figure.savefig(OUTPUT_DIR / f"{stem}.svg", bbox_inches="tight")
    plt.close(figure)


def _write_data_description(ogs: pd.DataFrame, boundary: dict[str, str]) -> None:
    """记录 OGS 案例、连续边界条件与实际读取的数据列。"""

    DATA_DESCRIPTION_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_DESCRIPTION_PATH.write_text(
        f"""# Case A OGS Data Description

## Case information

- OGS project file: `{OGS_PROJECT_PATH.as_posix()}`
- Exported outlet-data file: `{OGS_CSV_PATH.as_posix()}`
- Borehole depth from `DBHE.prj`: {boundary['depth_m']} m
- Case label: Case A, continuous operation

## Boundary condition

- Temperature control curve time coordinates (s): {boundary['temperature_coords_s']}
- Temperature control values (degC): {boundary['temperature_values_degC']}
- Flow control curve time coordinates (s): {boundary['flow_coords_s']}
- Flow control values (m3/s): {boundary['flow_values_m3s']}
- The curve endpoints have equal values, therefore Tin and Q are constant over the exported operating period.

## Output variable description

- Time column: `Time`, unit: s.
- Outlet-temperature column: `{OUTLET_COLUMN}`, unit: degC.
- Valid rows read: {len(ogs)}.
- Time range: {ogs['time_s'].iloc[0]:.0f} to {ogs['time_s'].iloc[-1]:.0f} s, equivalent to {ogs['time_years'].iloc[0]:.6f} to {ogs['time_years'].iloc[-1]:.6f} year using 365 days/year.
- Only the two columns above are read. No `.vtu`, `.pvd`, or rock-temperature-field file is read.
""",
        encoding="utf-8",
    )


def _write_metrics(metrics: dict[str, float], sample_count: int) -> None:
    """写出用户指定字段的简明指标文件。"""

    (OUTPUT_DIR / "CaseA_metrics_summary.txt").write_text(
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


def _write_report(
    aligned: pd.DataFrame, metrics: dict[str, float], config: ModelConfig, result: Any
) -> None:
    """生成仅基于本次比较结果的客观验证报告。"""

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        f"""# Case A Continuous Operation Validation

## 1. Case information

- Borehole depth: {config.H:.0f} m
- Flow rate: {config.Q:.0f} m3/h
- Inlet temperature: {config.Tin:.0f} degC
- Physics simulation setting: 20.0 year requested, with the existing 30-day numerical time step.
- OGS reference coverage: {aligned['time_years'].iloc[0]:.6f} to {aligned['time_years'].iloc[-1]:.6f} year (365-day conversion).

## 2. Boundary conditions

`DBHE.prj` defines constant temperature and flow curves over 0.1 to 622080000 s: Tin=11 degC and Q=0.007222 m3/s (approximately 26 m3/h). This is a continuous-operation OGS case.

## 3. Physics baseline model

- The existing solver was called through the same `ModelConfig` and `run_simulation` path used by `run_single_case.py`.
- No PDE/ODE equation, resistance formula, `R_borehole`, `U_wall`, or `U_pa` was modified.
- Active mapped values retained for this run: `R_borehole={config.borehole_resistance:.9f} m*K/W`, `R_short_circuit={config.short_circuit_resistance:.9f} m*K/W`, `U_wall={result.heat_transfer.U_wall:.9f} W/(m*K)`, and `U_pa={result.heat_transfer.U_pa:.9f} W/(m*K)`.

## 4. Comparison results

`physics_Tout_caseA.csv` retains the complete baseline prediction. Physics output was also linearly interpolated to the OGS outlet-data timestamps and saved as `CaseA_aligned_comparison.csv`; the comparison therefore uses identical time nodes and contains {len(aligned)} samples.

| Metric | Value |
|---|---:|
| MAE (degC) | {metrics['MAE_degC']:.6f} |
| RMSE (degC) | {metrics['RMSE_degC']:.6f} |
| R2 | {metrics['R2']:.6f} |
| Bias (degC) | {metrics['Bias_degC']:.6f} |

## 5. Error analysis

The plotted error is `Physics baseline - OGS`; positive values mean the baseline prediction is higher than the OGS outlet temperature. The metrics include the complete shared OGS time span, including the initial output point.

If discrepancies are present, possible sources include the radial one-dimensional rock-model simplification, equivalent wellbore-resistance representation, initial geothermal-temperature condition, and the baseline 30-day numerical time step. This validation neither changes model parameters nor uses OGS results to infer any parameter.
""",
        encoding="utf-8",
    )


def run_validation() -> dict[str, Any]:
    """运行一次 20 年 Case A baseline，并生成全部验证产物。"""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ogs = load_ogs_outlet_data(OGS_CSV_PATH)
    boundary = _read_project_boundary_conditions(OGS_PROJECT_PATH)
    config = build_caseA_config()

    # 不修改 run_single_case.py；这里调用其相同的核心求解入口，以便传入 Case A 工况。
    result = run_simulation(config)

    # 先保存完整 20 年 baseline 预测，保证该文件不因 OGS 的较短输出范围而截断。
    physics_output = pd.DataFrame(
        {
            "time_s": result.time_s,
            "time_years": result.time_years,
            "physics_Tout_degC": result.Tout,
        }
    )
    physics_output.to_csv(OUTPUT_DIR / "physics_Tout_caseA.csv", index=False)

    # OGS 时间点是验证参考，故将 Physics Tout 插值至这些时间节点；不外推任何 OGS 数据。
    common_ogs = ogs.loc[ogs["time_s"] <= float(result.time_s[-1])].copy()
    if common_ogs.empty:
        raise ValueError("Physics 模拟与 OGS 参考没有重叠时间范围。")
    common_ogs["physics_Tout_degC"] = np.interp(
        common_ogs["time_s"].to_numpy(), result.time_s, result.Tout
    )
    aligned = common_ogs[["time_s", "time_years", "physics_Tout_degC", "ogs_Tout_degC"]].copy()
    aligned["temperature_error_degC"] = aligned["physics_Tout_degC"] - aligned["ogs_Tout_degC"]
    aligned.to_csv(OUTPUT_DIR / "CaseA_aligned_comparison.csv", index=False)

    metrics = calculate_metrics(
        aligned["physics_Tout_degC"].to_numpy(), aligned["ogs_Tout_degC"].to_numpy()
    )
    _set_plot_style()

    figure, axis = plt.subplots(figsize=(7.2, 4.5))
    axis.plot(aligned["time_years"], aligned["ogs_Tout_degC"], label="OGS", linewidth=2.0, color="#1f77b4")
    axis.plot(
        aligned["time_years"],
        aligned["physics_Tout_degC"],
        label="Physics baseline",
        linewidth=2.0,
        color="#d62728",
    )
    axis.set_xlabel("Time (year)")
    axis.set_ylabel("Outlet temperature (°C)")
    axis.grid(True, alpha=0.30)
    axis.legend(frameon=False)
    _save_figure(figure, "CaseA_Tout_comparison")

    figure, axis = plt.subplots(figsize=(7.2, 4.5))
    axis.axhline(0.0, color="black", linewidth=1.0)
    axis.plot(
        aligned["time_years"], aligned["temperature_error_degC"], linewidth=1.8, color="#9467bd"
    )
    axis.set_xlabel("Time (year)")
    axis.set_ylabel("Temperature error (°C)")
    axis.grid(True, alpha=0.30)
    _save_figure(figure, "CaseA_error_curve")

    _write_metrics(metrics, len(aligned))
    _write_data_description(ogs, boundary)
    _write_report(aligned, metrics, config, result)
    return {"metrics": metrics, "samples": len(aligned), "output_dir": OUTPUT_DIR}


def main() -> None:
    """命令行入口：执行 Case A 单工况独立验证。"""

    validation = run_validation()
    print(f"Validation outputs saved to: {validation['output_dir']}")
    print(f"Aligned samples: {validation['samples']}")
    for metric_name, metric_value in validation["metrics"].items():
        print(f"{metric_name}: {metric_value:.6f}")


if __name__ == "__main__":
    main()
