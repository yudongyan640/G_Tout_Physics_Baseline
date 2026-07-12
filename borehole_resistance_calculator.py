"""井筒等效热阻计算框架。

R_borehole 不是训练参数，而是由井筒几何、材料导热系数和对流换热系数
估算得到的单位长度等效热阻，单位为 m*K/W。

第一版只提供多层圆筒导热热阻和圆柱面对流热阻的组合计算，不自动替换
config.py 中的默认 borehole_resistance。
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping


def compute_cylindrical_layer_resistance(r_inner: float, r_outer: float, k: float) -> float:
    """计算单位长度圆筒层导热热阻。

    公式：
        R = ln(r_outer / r_inner) / (2*pi*k)

    参数：
    - r_inner：内半径，单位 m；
    - r_outer：外半径，单位 m；
    - k：材料导热系数，单位 W/(m*K)。

    返回：
    - 单位长度热阻，单位 m*K/W。
    """

    if r_inner <= 0.0:
        raise ValueError("r_inner 必须大于 0。")
    if r_outer <= r_inner:
        raise ValueError("r_outer 必须大于 r_inner。")
    if k <= 0.0:
        raise ValueError("k 必须大于 0。")
    return math.log(r_outer / r_inner) / (2.0 * math.pi * k)


def compute_convective_resistance(radius: float, h: float) -> float:
    """计算单位长度圆柱面对流换热热阻。

    公式：
        R = 1 / (2*pi*r*h)

    参数：
    - radius：发生对流换热的半径，单位 m；
    - h：对流换热系数，单位 W/(m2*K)。

    返回：
    - 单位长度热阻，单位 m*K/W。
    """

    if radius <= 0.0:
        raise ValueError("radius 必须大于 0。")
    if h <= 0.0:
        raise ValueError("h 必须大于 0。")
    return 1.0 / (2.0 * math.pi * radius * h)


def compute_total_borehole_resistance(
    layers: Iterable[Mapping[str, float]],
    convective_terms: Iterable[Mapping[str, float]],
) -> float:
    """累加多层圆筒导热热阻和多个对流热阻。

    layers 中每一项需要包含：
    - r_inner
    - r_outer
    - k

    convective_terms 中每一项需要包含：
    - radius
    - h

    返回的总热阻仍为单位长度等效热阻 m*K/W。
    """

    total = 0.0
    for layer in layers:
        total += compute_cylindrical_layer_resistance(
            r_inner=float(layer["r_inner"]),
            r_outer=float(layer["r_outer"]),
            k=float(layer["k"]),
        )
    for term in convective_terms:
        total += compute_convective_resistance(
            radius=float(term["radius"]),
            h=float(term["h"]),
        )
    return total


def calculate_borehole_wall_path(
    *,
    annulus_radius: float,
    annulus_h: float,
    outer_pipe_inner_radius: float,
    outer_pipe_outer_radius: float,
    outer_pipe_k: float,
    borehole_radius: float,
    grout_k: float,
) -> dict[str, object]:
    """计算岩土井壁到环空流体的单位长度等效热阻。

    路径严格为：环空侧对流 -> 外管/套管导热 -> 回填（水泥环）导热。
    近井岩土的瞬态导热已由 ``rock_solver_1d.py`` 显式计算，不能重复加入
    常数热阻；中心管保温层属于流体短路路径，也不能加入本函数。
    """

    components = {
        "annulus_convection": compute_convective_resistance(annulus_radius, annulus_h),
        "outer_pipe": compute_cylindrical_layer_resistance(
            outer_pipe_inner_radius, outer_pipe_outer_radius, outer_pipe_k
        ),
        "grout": compute_cylindrical_layer_resistance(outer_pipe_outer_radius, borehole_radius, grout_k),
    }
    resistance = sum(components.values())
    return {
        "R_borehole": resistance,
        "U_wall": 1.0 / resistance,
        "components": components,
    }


def example_borehole_resistance() -> float:
    """给出一个示例计算，便于替换成真实工程尺寸后复用。

    这里的数值只是演示格式，不代表当前工程真实井筒结构。
    """

    example_layers = [
        # 示例：套管或水泥环等圆筒层。
        {"r_inner": 0.060, "r_outer": 0.080, "k": 1.50},
        {"r_inner": 0.080, "r_outer": 0.100, "k": 2.00},
    ]
    example_convective_terms = [
        # 示例：环空流体到井壁等效对流项。
        {"radius": 0.060, "h": 800.0},
    ]
    return compute_total_borehole_resistance(example_layers, example_convective_terms)


def main() -> None:
    """打印示例 R_borehole，提醒用户替换为真实井筒参数。"""

    resistance = example_borehole_resistance()
    print("Example borehole resistance")
    print("---------------------------")
    print(f"R_borehole = {resistance:.6f} m*K/W")
    print(f"Equivalent U_wall = {1.0 / resistance:.6f} W/(m*K)")
    print("Note: replace the example geometry and material values with real borehole data before use.")


if __name__ == "__main__":
    main()
