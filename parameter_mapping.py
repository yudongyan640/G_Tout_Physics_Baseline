"""将 OGS XML 原始物理参数映射为 pure physics baseline 配置。"""

from __future__ import annotations

import json
from math import pi
from pathlib import Path
from typing import Any

from borehole_resistance_calculator import calculate_borehole_wall_path
from heat_transfer import compute_prandtl, compute_reynolds, dittus_boelter_h
from short_circuit_resistance_calculator import calculate_short_circuit_path


def _active_curve_value(raw: dict[str, Any], curve_name: str, fallback: float) -> float:
    """读取 OGS 控制曲线的首个正值；当前 baseline 不支持启停时序。"""

    values = raw.get("operation", {}).get(curve_name, [])
    return next((float(value) for value in values if float(value) > 0.0), fallback)


def _calculate_convection(raw: dict[str, Any], q_m3h: float) -> dict[str, float]:
    """用现有 Dittus--Boelter 关联式计算两侧对流系数，保证定义一致。"""

    geometry = raw["geometry"]
    fluid = raw["fluid"]
    q_m3s = q_m3h / 3600.0
    center_radius = float(geometry["center_pipe_inner_radius"])
    annulus_inner = float(geometry["annulus_inner_radius"])
    annulus_outer = float(geometry["annulus_outer_radius"])
    center_velocity = q_m3s / (pi * center_radius**2)
    annulus_velocity = q_m3s / (pi * (annulus_outer**2 - annulus_inner**2))
    prandtl = compute_prandtl(fluid["viscosity"], fluid["heat_capacity"], fluid["thermal_conductivity"])
    center_re = compute_reynolds(fluid["density"], center_velocity, 2.0 * center_radius, fluid["viscosity"])
    annulus_re = compute_reynolds(fluid["density"], annulus_velocity, 2.0 * (annulus_outer - annulus_inner), fluid["viscosity"])
    return {
        "center_h": dittus_boelter_h(fluid["thermal_conductivity"], 2.0 * center_radius, center_re, prandtl),
        "annulus_h": dittus_boelter_h(fluid["thermal_conductivity"], 2.0 * (annulus_outer - annulus_inner), annulus_re, prandtl),
        "center_Re": center_re,
        "annulus_Re": annulus_re,
        "Pr": prandtl,
    }


def build_baseline_parameters(raw: dict[str, Any]) -> dict[str, Any]:
    """生成可由 ``ModelConfig`` 直接加载的 baseline 物理参数字典。"""

    geometry = raw["geometry"]
    materials = raw["materials"]
    # DBHE 曲线的非零流量为运行阶段值；零流量停机段仍只作为元数据保留。
    q_m3h = _active_curve_value(raw, "flow_rate_m3s", 30.0 / 3600.0) * 3600.0
    inlet_temperature = _active_curve_value(raw, "inlet_temperature_degC", 10.0)
    convection = _calculate_convection(raw, q_m3h)
    wall_path = calculate_borehole_wall_path(
        annulus_radius=geometry["annulus_outer_radius"],
        annulus_h=convection["annulus_h"],
        outer_pipe_inner_radius=geometry["outer_pipe_inner_radius"],
        outer_pipe_outer_radius=geometry["outer_pipe_outer_radius"],
        outer_pipe_k=materials["outer_pipe_thermal_conductivity"],
        borehole_radius=geometry["Rb"],
        grout_k=materials["grout_thermal_conductivity"],
    )
    short_path = calculate_short_circuit_path(
        center_inner_radius=geometry["center_pipe_inner_radius"],
        center_outer_radius=geometry["center_pipe_outer_radius"],
        center_h=convection["center_h"],
        annulus_h=convection["annulus_h"],
        insulation_k=materials["insulation_thermal_conductivity"],
    )
    return {
        "H": geometry["H"],
        "Q": q_m3h,
        "Tin": inlet_temperature,
        "Rb": geometry["Rb"],
        "r_inner": geometry["center_pipe_inner_radius"],
        "r_outer": geometry["center_pipe_outer_radius"],
        "annulus_outer_radius": geometry["annulus_outer_radius"],
        "rock_properties": dict(raw["rock"]),
        "fluid_properties": dict(raw["fluid"]),
        "geothermal": dict(raw["geothermal"]),
        "insulation_thermal_conductivity": materials["insulation_thermal_conductivity"],
        "R_borehole": wall_path["R_borehole"],
        "U_wall": wall_path["U_wall"],
        "R_short_circuit": short_path["R_short_circuit"],
        "U_pa": short_path["U_pa"],
        "resistance_components": {"wall_path": wall_path["components"], "short_circuit_path": short_path["components"]},
        "convection_diagnostics": convection,
        "operation_metadata": raw.get("operation", {}),
        "mapping_notes": {
            "rock_near_well_resistance": "由 rock_solver_1d.py 显式求解，未重复串入 R_borehole。",
            "operation_schedule": "当前 baseline 为单一连续工况，未映射 OGS 的启停曲线。",
        },
    }


def write_baseline_parameters(parameters: dict[str, Any], output_path: Path) -> Path:
    """保存 UTF-8 映射 JSON，供 ``ModelConfig`` 自动读取。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(parameters, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path
