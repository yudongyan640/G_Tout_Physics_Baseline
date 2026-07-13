"""
Module name:
    heat_transfer.py

Purpose:
    Compute Reynolds number, Prandtl number, Dittus-Boelter convective heat
    transfer coefficients, and the overall unit-length heat transfer parameters
    U_wall (borehole wall-to-annulus) and U_pa (inner pipe-to-annulus).

    The first version assumes turbulent flow; a warning is issued for low Re
    but no laminar correlation is implemented.

Dependencies:
    - config.ModelConfig
    - geometry.GeometryResult

Outputs:
    - HeatTransferResult dataclass with all heat-transfer quantities.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log, pi
import warnings

from config import ModelConfig
from geometry import GeometryResult, compute_geometry


@dataclass
class HeatTransferResult:
    """Computed heat transfer coefficients and diagnostics.

    Attributes
    ----------
    geometry : GeometryResult
        The underlying geometry and flow data.
    Re_center : float
        Inner-pipe Reynolds number (-).
    Re_annulus : float
        Annulus Reynolds number (-).
    Pr : float
        Prandtl number (-).
    h_inner : float
        Inner-pipe convective coefficient (W/(m2·K)).
    h_outer : float
        Annulus-side convective coefficient (W/(m2·K)).
    h_wall : float
        Annulus-side coefficient stored for legacy diagnostics (W/(m2·K)).
    U_wall : float
        Borehole wall-to-annulus unit-length heat transfer coefficient (W/(m·K)).
    U_pa : float
        Inner pipe-to-annulus unit-length heat transfer coefficient (W/(m·K)).
    """

    geometry: GeometryResult
    Re_center: float
    Re_annulus: float
    Pr: float
    h_inner: float
    h_outer: float
    h_wall: float
    U_wall: float
    U_pa: float


def compute_reynolds(rho: float, velocity: float, hydraulic_diameter: float, mu: float) -> float:
    """Compute Reynolds number Re = rho * u * dh / mu.

    Parameters
    ----------
    rho : float
        Fluid density (kg/m3).
    velocity : float
        Flow velocity (m/s).
    hydraulic_diameter : float
        Hydraulic diameter (m).
    mu : float
        Dynamic viscosity (Pa·s).

    Returns
    -------
    float
        Reynolds number (dimensionless).
    """

    return rho * velocity * hydraulic_diameter / mu


def compute_prandtl(mu: float, cp: float, conductivity: float) -> float:
    """Compute Prandtl number Pr = mu * cp / k.

    Parameters
    ----------
    mu : float
        Dynamic viscosity (Pa·s).
    cp : float
        Specific heat capacity (J/(kg·K)).
    conductivity : float
        Thermal conductivity (W/(m·K)).

    Returns
    -------
    float
        Prandtl number (dimensionless).
    """

    return mu * cp / conductivity


def dittus_boelter_h(conductivity: float, hydraulic_diameter: float, Re: float, Pr: float) -> float:
    """Compute convective heat transfer coefficient using the Dittus-Boelter correlation.

    h = 0.023 * k / dh * Re^0.8 * Pr^0.4

    The exponent 0.4 (heating) is used uniformly throughout this baseline.

    Parameters
    ----------
    conductivity : float
        Fluid thermal conductivity (W/(m·K)).
    hydraulic_diameter : float
        Hydraulic diameter (m).
    Re : float
        Reynolds number (dimensionless).
    Pr : float
        Prandtl number (dimensionless).

    Returns
    -------
    float
        Convective heat transfer coefficient (W/(m2·K)).
    """

    return 0.023 * conductivity / hydraulic_diameter * Re**0.8 * Pr**0.4


def compute_heat_transfer(config: ModelConfig) -> HeatTransferResult:
    """Compute all heat transfer parameters for the current configuration.

    U_wall (wall-to-annulus) is the unit-length heat transfer coefficient:
    - If use_effective_borehole_resistance is True: U_wall = 1 / R_borehole.
    - Otherwise: U_wall = 2 * pi * Rb * h_wall (legacy formulation).

    U_pa (pipe-to-annulus) accounts for the thermal short-circuit path:
    inner-pipe convection + insulation conduction + annulus convection.

    Parameters
    ----------
    config : ModelConfig
        Model configuration with borehole geometry, material properties, and
        resistance settings.

    Returns
    -------
    HeatTransferResult
        All computed heat transfer coefficients and diagnostic quantities.
    """

    geometry = compute_geometry(config)
    Pr = compute_prandtl(config.mu_w, config.cw, config.kw)

    Re_center = compute_reynolds(
        config.rho_w,
        geometry.center_velocity,
        geometry.center_dh,
        config.mu_w,
    )
    Re_annulus = compute_reynolds(
        config.rho_w,
        geometry.annulus_velocity,
        geometry.annulus_dh,
        config.mu_w,
    )

    if Re_center < config.turbulent_re_warning:
        warnings.warn(
            f"中心管 Re={Re_center:.1f} 偏低，Dittus-Boelter 湍流公式可能不适用。",
            RuntimeWarning,
            stacklevel=2,
        )
    if Re_annulus < config.turbulent_re_warning:
        warnings.warn(
            f"环空 Re={Re_annulus:.1f} 偏低，Dittus-Boelter 湍流公式可能不适用。",
            RuntimeWarning,
            stacklevel=2,
        )

    h_inner = dittus_boelter_h(config.kw, geometry.center_dh, Re_center, Pr)
    h_outer = dittus_boelter_h(config.kw, geometry.annulus_dh, Re_annulus, Pr)

    # h_wall 仍保存为环空侧对流换热系数，便于诊断旧模型为什么 U_wall 可能很大。
    h_wall = h_outer
    if config.use_effective_borehole_resistance:
        if config.borehole_resistance <= 0.0:
            raise ValueError("borehole_resistance 必须大于 0。")
        U_wall = 1.0 / config.borehole_resistance
    else:
        U_wall = 2.0 * pi * config.Rb * h_wall

    # 中心管与环空间热短路热阻：内侧对流 + 保温层导热 + 外侧对流。
    # 使用 OGS 映射参数时，该热阻已由独立模块算出；历史配置仍保留原公式。
    thermal_resistance = (
        1.0 / (2.0 * pi * config.r_inner * h_inner)
        + log(config.r_outer / config.r_inner) / (2.0 * pi * config.lambda_ins)
        + 1.0 / (2.0 * pi * config.r_outer * h_outer)
    )
    if config.use_effective_short_circuit_resistance:
        if config.short_circuit_resistance <= 0.0:
            raise ValueError("short_circuit_resistance 必须大于 0。")
        U_pa = 1.0 / config.short_circuit_resistance
    else:
        U_pa = 1.0 / thermal_resistance

    return HeatTransferResult(
        geometry=geometry,
        Re_center=Re_center,
        Re_annulus=Re_annulus,
        Pr=Pr,
        h_inner=h_inner,
        h_outer=h_outer,
        h_wall=h_wall,
        U_wall=U_wall,
        U_pa=U_pa,
    )
