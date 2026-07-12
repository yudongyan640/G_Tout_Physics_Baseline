"""从 OGS DBHE 项目文件提取纯物理 baseline 所需参数。

本模块的输入严格限定为 OGS 的 ``.prj`` 和 ``.gml`` 定义文件。它不读取网格、
VTK/PVD 或任何温度场结果，因此不能也不会使用 OGS 计算结果训练或校准模型。
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def _text_as_float(element: ET.Element, path: str) -> float:
    """读取必填 XML 文本数值，并在结构变化时给出清晰错误。"""

    text = element.findtext(path)
    if text is None:
        raise ValueError(f"OGS 项目文件缺少必填节点：{path}")
    return float(text.strip())


def _medium_properties(project_root: ET.Element, medium_id: str) -> dict[str, float]:
    """读取指定介质的固相密度、比热和介质导热系数。"""

    medium = project_root.find(f"./media/medium[@id='{medium_id}']")
    if medium is None:
        raise ValueError(f"OGS 项目文件缺少 medium id={medium_id}。")

    solid = medium.find("./phases/phase[type='Solid']")
    if solid is None:
        raise ValueError(f"medium id={medium_id} 中缺少固相物性。")

    def phase_property(name: str) -> float:
        property_node = solid.find(f"./properties/property[name='{name}']/value")
        if property_node is None or property_node.text is None:
            raise ValueError(f"medium id={medium_id} 缺少固相参数 {name}。")
        return float(property_node.text.strip())

    conductivity = medium.find("./properties/property[name='thermal_conductivity']/value")
    if conductivity is None or conductivity.text is None:
        raise ValueError(f"medium id={medium_id} 缺少 thermal_conductivity。")
    return {
        "thermal_conductivity": float(conductivity.text.strip()),
        "density": phase_property("density"),
        "heat_capacity": phase_property("specific_heat_capacity"),
    }


def _parse_linear_geothermal_expression(expression: str) -> tuple[float, float]:
    """将 OGS 的 ``Tamb - gradient*Z`` 转为向下深度坐标的 Tamb、G。

    DBHE.gml 中井深方向采用 Z 向上为正，因此 OGS 表达式中的负 Z 系数在
    baseline 的向下深度坐标中对应正地温梯度。
    """

    compact = expression.replace(" ", "")
    match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)([+-])(\d+(?:\.\d+)?)\*Z", compact)
    if match is None:
        raise ValueError(f"暂不支持的地温初始表达式：{expression}")
    surface_temperature = float(match.group(1))
    z_coefficient = float(match.group(3)) * (1.0 if match.group(2) == "+" else -1.0)
    return surface_temperature, -z_coefficient


def _read_geometry_points(gml_path: Path) -> list[dict[str, float | str]]:
    """读取 GML 点坐标，保留边界位置供人工核查。"""

    geometry_root = ET.parse(gml_path).getroot()
    points: list[dict[str, float | str]] = []
    for point in geometry_root.findall("./points/point"):
        points.append(
            {
                "id": point.attrib["id"],
                "name": point.attrib.get("name", ""),
                "x": float(point.attrib["x"]),
                "y": float(point.attrib["y"]),
                "z": float(point.attrib["z"]),
            }
        )
    return points


def _curve_values(project_root: ET.Element, curve_name: str) -> list[float]:
    """读取 OGS 曲线数值，仅作为运行控制元数据而不读取结果数据。"""

    curve = project_root.find(f"./curves/curve[name='{curve_name}']/values")
    if curve is None or curve.text is None:
        raise ValueError(f"OGS 项目文件缺少曲线 {curve_name}。")
    return [float(value) for value in curve.text.split()]


def extract_ogs_parameters(prj_path: Path | str, gml_path: Path | str) -> dict[str, Any]:
    """解析 DBHE 项目参数，并全部以 SI 单位返回。

    参数仅来自输入 XML 文件；返回字典中不会保存或扫描网格、结果或温度场路径。
    """

    prj_path = Path(prj_path)
    gml_path = Path(gml_path)
    project_root = ET.parse(prj_path).getroot()
    bhe = project_root.find("./processes/process/borehole_heat_exchangers/borehole_heat_exchanger")
    if bhe is None:
        raise ValueError("OGS 项目文件缺少 borehole_heat_exchanger 配置。")

    # 由 OGS 内径和壁厚恢复每一个物理半径；单位均为 m。
    borehole_diameter = _text_as_float(bhe, "./borehole/diameter")
    outer_inner_diameter = _text_as_float(bhe, "./pipes/outer/diameter")
    outer_wall_thickness = _text_as_float(bhe, "./pipes/outer/wall_thickness")
    center_inner_diameter = _text_as_float(bhe, "./pipes/inner/diameter")
    insulation_thickness = _text_as_float(bhe, "./pipes/inner/wall_thickness")
    outer_inner_radius = outer_inner_diameter / 2.0
    outer_outer_radius = outer_inner_radius + outer_wall_thickness
    center_inner_radius = center_inner_diameter / 2.0
    center_outer_radius = center_inner_radius + insulation_thickness
    borehole_radius = borehole_diameter / 2.0

    refrigerant = bhe.find("./refrigerant")
    grout = bhe.find("./grout")
    if refrigerant is None or grout is None:
        raise ValueError("OGS 项目文件缺少 refrigerant 或 grout 配置。")

    initial_expression = project_root.findtext("./parameters/parameter[name='T0']/expression")
    if initial_expression is None:
        raise ValueError("OGS 项目文件缺少 T0 初始温度表达式。")
    surface_temperature, geothermal_gradient = _parse_linear_geothermal_expression(initial_expression)

    top_temperature = project_root.findtext("./parameters/parameter[name='Dirichlet_top']/value")
    geometry_points = _read_geometry_points(gml_path)
    return {
        "source_files": [prj_path.name, gml_path.name],
        "units": {"length": "m", "temperature": "degC", "gradient": "K/m"},
        "geometry": {
            "H": _text_as_float(bhe, "./borehole/length"),
            "Rb": borehole_radius,
            "outer_pipe_inner_radius": outer_inner_radius,
            "outer_pipe_outer_radius": outer_outer_radius,
            "center_pipe_inner_radius": center_inner_radius,
            "center_pipe_outer_radius": center_outer_radius,
            "annulus_inner_radius": center_outer_radius,
            "annulus_outer_radius": outer_inner_radius,
            "outer_pipe_wall_thickness": outer_wall_thickness,
            "insulation_thickness": insulation_thickness,
            "grout_thickness": borehole_radius - outer_outer_radius,
        },
        "materials": {
            "outer_pipe_thermal_conductivity": _text_as_float(bhe, "./pipes/outer/wall_thermal_conductivity"),
            "insulation_thermal_conductivity": _text_as_float(bhe, "./pipes/inner/wall_thermal_conductivity"),
            "grout_thermal_conductivity": _text_as_float(grout, "./thermal_conductivity"),
            "grout_density": _text_as_float(grout, "./density"),
            "grout_heat_capacity": _text_as_float(grout, "./specific_heat_capacity"),
        },
        "rock": _medium_properties(project_root, "0"),
        "fluid": {
            "density": _text_as_float(refrigerant, "./density"),
            "heat_capacity": _text_as_float(refrigerant, "./specific_heat_capacity"),
            "thermal_conductivity": _text_as_float(refrigerant, "./thermal_conductivity"),
            "viscosity": _text_as_float(refrigerant, "./viscosity"),
        },
        "geothermal": {"Tamb": surface_temperature, "gradient": geothermal_gradient},
        "operation": {
            "flow_rate_m3s": _curve_values(project_root, "flow_rate_curve"),
            "inlet_temperature_degC": _curve_values(project_root, "temperature_curve"),
            "schedule_note": "保留 OGS 曲线供追溯；当前 baseline 仅支持单一连续工况。",
        },
        "boundary_conditions": {
            "initial_temperature": initial_expression.strip(),
            "surface_boundary": float(top_temperature.strip()) if top_temperature else None,
            "outer_boundary_temperature": None,
            "bottom_boundary": None,
        },
        "geometry_points": geometry_points,
    }


def write_raw_parameters(parameters: dict[str, Any], output_path: Path) -> Path:
    """将提取结果保存为 UTF-8 JSON，便于映射前追溯来源。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(parameters, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    """提供直接生成 ``outputs/ogs_raw_parameters.json`` 的命令行入口。"""

    project_root = Path(__file__).resolve().parent
    ogs_directory = Path(r"E:\newdesktop\PINN\OGS_data\baseline")
    parameters = extract_ogs_parameters(ogs_directory / "DBHE.prj", ogs_directory / "DBHE.gml")
    output_path = write_raw_parameters(parameters, project_root / "outputs" / "ogs_raw_parameters.json")
    print(f"OGS raw parameters saved to: {output_path}")


if __name__ == "__main__":
    main()
