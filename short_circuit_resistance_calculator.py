"""中心管与环空流体热短路的等效热阻计算模块。

本模块仅描述 ``Tp -> Ta`` 路径：中心管内侧对流、保温层导热和环空侧对流。
它不包含外管、回填材料或岩土，这些内容属于井壁到环空的另一条路径。
"""

from __future__ import annotations

from borehole_resistance_calculator import (
    compute_convective_resistance,
    compute_cylindrical_layer_resistance,
)


def calculate_short_circuit_path(
    *,
    center_inner_radius: float,
    center_outer_radius: float,
    center_h: float,
    annulus_h: float,
    insulation_k: float,
) -> dict[str, object]:
    """计算中心管流体到环空流体的单位长度热阻和 ``U_pa``。

    参数中的半径为中心管内、外半径，``center_h`` 和 ``annulus_h`` 分别由
    当前工况下中心管与环空的对流关联式计算得到，单位均为 SI。
    """

    components = {
        "center_convection": compute_convective_resistance(center_inner_radius, center_h),
        "insulation": compute_cylindrical_layer_resistance(
            center_inner_radius, center_outer_radius, insulation_k
        ),
        "annulus_convection": compute_convective_resistance(center_outer_radius, annulus_h),
    }
    resistance = sum(components.values())
    return {
        "R_short_circuit": resistance,
        "U_pa": 1.0 / resistance,
        "components": components,
    }
