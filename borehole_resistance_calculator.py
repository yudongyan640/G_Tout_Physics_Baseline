"""
Module name:
    borehole_resistance_calculator.py

Purpose:
    Compute the equivalent borehole thermal resistance R_borehole based on
    borehole geometry, material thermal conductivities, and convective heat
    transfer coefficients.

    R_borehole is not a training parameter; it is a physical quantity computed
    from measurable layer properties and geometry. The module provides a
    layer-by-layer framework and does NOT automatically modify config.py.

Physical model:
    R_borehole = sum(R_cylindrical_layer) + sum(R_convective)
    where:
        R_layer = ln(r_outer / r_inner) / (2 * pi * k)
        R_conv = 1 / (2 * pi * r * h)

Dependencies:
    - math (standard library only)

Outputs:
    - R_borehole (m*K/W)
    - Equivalent U_wall (W/(m*K))
    - Component breakdown for diagnostics
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping


def compute_cylindrical_layer_resistance(r_inner: float, r_outer: float, k: float) -> float:
    """Compute the unit-length thermal resistance of a cylindrical layer.

    Formula: R = ln(r_outer / r_inner) / (2 * pi * k)

    Parameters
    ----------
    r_inner : float
        Inner radius (m).
    r_outer : float
        Outer radius (m).
    k : float
        Material thermal conductivity (W/(m·K)).

    Returns
    -------
    float
        Unit-length thermal resistance (m·K/W).

    Raises
    ------
    ValueError
        If r_inner <= 0, r_outer <= r_inner, or k <= 0.
    """

    if r_inner <= 0.0:
        raise ValueError("r_inner must be > 0.")
    if r_outer <= r_inner:
        raise ValueError("r_outer must be > r_inner.")
    if k <= 0.0:
        raise ValueError("k must be > 0.")
    return math.log(r_outer / r_inner) / (2.0 * math.pi * k)


def compute_convective_resistance(radius: float, h: float) -> float:
    """Compute the unit-length convective thermal resistance at a cylindrical surface.

    Formula: R = 1 / (2 * pi * r * h)

    Parameters
    ----------
    radius : float
        Radius of the convective surface (m).
    h : float
        Convective heat transfer coefficient (W/(m2·K)).

    Returns
    -------
    float
        Unit-length thermal resistance (m·K/W).

    Raises
    ------
    ValueError
        If radius <= 0 or h <= 0.
    """

    if radius <= 0.0:
        raise ValueError("radius must be > 0.")
    if h <= 0.0:
        raise ValueError("h must be > 0.")
    return 1.0 / (2.0 * math.pi * radius * h)


def compute_total_borehole_resistance(
    layers: Iterable[Mapping[str, float]],
    convective_terms: Iterable[Mapping[str, float]],
) -> float:
    """Sum multiple cylindrical layer resistances and convective resistances.

    Each item in ``layers`` must contain keys ``r_inner``, ``r_outer``, and ``k``.
    Each item in ``convective_terms`` must contain keys ``radius`` and ``h``.

    Parameters
    ----------
    layers : iterable of dict
        Cylindrical conduction layers.
    convective_terms : iterable of dict
        Convective resistance terms.

    Returns
    -------
    float
        Total unit-length borehole thermal resistance (m·K/W).
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
    """Compute the unit-length equivalent thermal resistance from the rock wall to the annulus fluid.

    The heat flow path is: annulus convection → outer pipe/steel casing
    conduction → grout/cement ring conduction.

    Note: the transient conduction in the near-well rock is already handled
    explicitly by ``rock_solver_1d.py`` and must NOT be included here.
    The insulation layer belongs to the short-circuit path (Tp → Ta) and is
    also excluded from this function.

    Parameters
    ----------
    annulus_radius : float
        Annulus outer radius (m).
    annulus_h : float
        Annulus-side convective coefficient (W/(m2·K)).
    outer_pipe_inner_radius : float
        Inner radius of the outer steel pipe (m).
    outer_pipe_outer_radius : float
        Outer radius of the outer steel pipe (m).
    outer_pipe_k : float
        Thermal conductivity of the outer pipe (W/(m·K)).
    borehole_radius : float
        Borehole radius (m).
    grout_k : float
        Thermal conductivity of the grout (W/(m·K)).

    Returns
    -------
    dict
        With keys:
        - "R_borehole": total unit-length resistance (m·K/W)
        - "U_wall": equivalent unit-length heat transfer coefficient (W/(m·K))
        - "components": breakdown of each resistance term for diagnostics.
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
