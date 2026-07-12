"""检查 OGS XML 参数到 pure physics baseline 的映射结果。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ogs_parameter_extractor import extract_ogs_parameters, write_raw_parameters
from parameter_mapping import build_baseline_parameters, write_baseline_parameters


def validate_mapping(raw: dict[str, Any], mapped: dict[str, Any]) -> dict[str, Any]:
    """检查映射所需字段、SI 单位和基本数值范围。"""

    required_mapped = (
        "H", "Rb", "r_inner", "r_outer", "annulus_outer_radius", "R_borehole", "U_wall", "R_short_circuit", "U_pa"
    )
    missing = [name for name in required_mapped if name not in mapped or mapped[name] is None]
    for group, keys in (("rock_properties", ("thermal_conductivity", "density", "heat_capacity")), ("fluid_properties", ("density", "heat_capacity", "thermal_conductivity", "viscosity"))):
        missing.extend(f"{group}.{key}" for key in keys if key not in mapped.get(group, {}))

    positive_values = [
        mapped.get("H"), mapped.get("Rb"), mapped.get("r_inner"), mapped.get("r_outer"),
        mapped.get("annulus_outer_radius"), mapped.get("R_borehole"), mapped.get("U_wall"),
        mapped.get("R_short_circuit"), mapped.get("U_pa"),
        *mapped.get("rock_properties", {}).values(), *mapped.get("fluid_properties", {}).values(),
    ]
    anomalies = [f"发现非正或非数值参数：{value!r}" for value in positive_values if not isinstance(value, (int, float)) or value <= 0.0]
    if mapped.get("r_inner", 0.0) >= mapped.get("r_outer", 0.0):
        anomalies.append("中心管内半径必须小于中心管外半径。")
    if mapped.get("r_outer", 0.0) >= mapped.get("annulus_outer_radius", 0.0):
        anomalies.append("中心管外半径必须小于环空外半径。")
    if mapped.get("annulus_outer_radius", 0.0) > mapped.get("Rb", 0.0):
        anomalies.append("环空外半径不得大于井壁半径。")

    expected_units = {"length": "m", "temperature": "degC", "gradient": "K/m"}
    return {
        "missing_required": missing,
        "anomalies": anomalies,
        "si_units_consistent": raw.get("units") == expected_units,
        "unmapped_boundary_conditions": {
            key: value for key, value in raw.get("boundary_conditions", {}).items() if value is None
        },
    }


def _print_report(raw: dict[str, Any], mapped: dict[str, Any], validation: dict[str, Any]) -> None:
    """按用户要求打印原始参数、映射参数和检查结果。"""

    print("OGS raw parameters")
    print(f"H = {raw['geometry']['H']:.6g} m")
    print(f"Rb = {raw['geometry']['Rb']:.6g} m")
    print(f"kr = {raw['rock']['thermal_conductivity']:.6g} W/(m*K)")
    print(f"rho = {raw['rock']['density']:.6g} kg/m3")
    print(f"cp = {raw['rock']['heat_capacity']:.6g} J/(kg*K)")
    print("\nMapped baseline parameters")
    print(f"H = {mapped['H']:.6g} m")
    print(f"Rb = {mapped['Rb']:.6g} m")
    print(f"R_borehole = {mapped['R_borehole']:.9g} m*K/W")
    print(f"U_wall = {mapped['U_wall']:.9g} W/(m*K)")
    print(f"R_short_circuit = {mapped['R_short_circuit']:.9g} m*K/W")
    print(f"U_pa = {mapped['U_pa']:.9g} W/(m*K)")
    print(f"rho_r = {mapped['rock_properties']['density']:.6g} kg/m3")
    print(f"cp_r = {mapped['rock_properties']['heat_capacity']:.6g} J/(kg*K)")
    print("\nChecks")
    print(f"SI units consistent: {validation['si_units_consistent']}")
    print(f"Missing required parameters: {validation['missing_required']}")
    print(f"Anomalies: {validation['anomalies']}")
    print(f"Unmapped OGS boundaries: {validation['unmapped_boundary_conditions']}")


def main() -> None:
    """解析、写出 JSON 并报告检查结果；不读取任何 OGS 输出文件。"""

    project_root = Path(__file__).resolve().parent
    ogs_directory = Path(r"E:\newdesktop\PINN\OGS_data\baseline")
    raw = extract_ogs_parameters(ogs_directory / "DBHE.prj", ogs_directory / "DBHE.gml")
    mapped = build_baseline_parameters(raw)
    validation = validate_mapping(raw, mapped)
    write_raw_parameters(raw, project_root / "outputs" / "ogs_raw_parameters.json")
    write_baseline_parameters(mapped, project_root / "outputs" / "baseline_physical_parameters.json")
    _print_report(raw, mapped, validation)
    if validation["missing_required"] or validation["anomalies"] or not validation["si_units_consistent"]:
        raise SystemExit("OGS 参数映射检查未通过。")


if __name__ == "__main__":
    main()
