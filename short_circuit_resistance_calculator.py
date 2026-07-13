"""
Module name:
    short_circuit_resistance_calculator.py

Purpose:
    Compute the unit-length thermal short-circuit resistance between the inner
    pipe fluid (Tp) and the annulus fluid (Ta).

    The heat flow path is:
        inner-pipe convection → insulation conduction → annulus convection.

    This module does NOT cover the borehole wall path (pipe → grout → rock),
    which is handled by ``borehole_resistance_calculator.py``.

Dependencies:
    - borehole_resistance_calculator (reuses compute_convective_resistance
      and compute_cylindrical_layer_resistance)

Outputs:
    - R_short_circuit (m·K/W)
    - Equivalent U_pa (W/(m·K))
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
    """Compute the unit-length thermal resistance and U_pa for the Tp → Ta short-circuit path.

    The path consists of three serial components:
        1. Inner-pipe convection
        2. Insulation layer conduction
        3. Annulus-side convection

    Parameters
    ----------
    center_inner_radius : float
        Inner radius of the centre pipe (m).
    center_outer_radius : float
        Outer radius of the centre pipe / insulation (m).
    center_h : float
        Inner-pipe convective coefficient (W/(m2·K)).
    annulus_h : float
        Annulus-side convective coefficient (W/(m2·K)).
    insulation_k : float
        Insulation thermal conductivity (W/(m·K)).

    Returns
    -------
    dict
        With keys:
        - "R_short_circuit": total unit-length resistance (m·K/W)
        - "U_pa": equivalent unit-length heat transfer coefficient (W/(m·K))
        - "components": breakdown of each resistance term for diagnostics.
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
