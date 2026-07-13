"""
Module name:
    geometry.py

Purpose:
    Compute fundamental geometric and flow quantities for the coaxial borehole
    heat exchanger: cross-sectional areas, hydraulic diameters, mass flow rate,
    and flow velocities.

    Heat-transfer correlations are kept in heat_transfer.py so that each module
    can be replaced independently.

Dependencies:
    - config.ModelConfig

Outputs:
    - GeometryResult dataclass containing all geometric values.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi

from config import ModelConfig


@dataclass
class GeometryResult:
    """Results of geometry and flow calculations.

    Attributes
    ----------
    center_area : float
        Inner pipe cross-sectional area (m2).
    annulus_area : float
        Annulus cross-sectional area (m2).
    center_dh : float
        Inner pipe hydraulic diameter (m).
    annulus_dh : float
        Annulus hydraulic diameter (m).
    Q_m3s : float
        Volumetric flow rate (m3/s).
    m_dot : float
        Mass flow rate (kg/s).
    center_velocity : float
        Flow velocity in the inner pipe (m/s).
    annulus_velocity : float
        Flow velocity in the annulus (m/s).
    """

    center_area: float
    annulus_area: float
    center_dh: float
    annulus_dh: float
    Q_m3s: float
    m_dot: float
    center_velocity: float
    annulus_velocity: float


def validate_geometry(config: ModelConfig) -> None:
    """Check that borehole geometry parameters are physically consistent.

    Raises ValueError if any parameter is out of range, preventing
    meaningless solutions downstream.
    """

    if config.H <= 0.0:
        raise ValueError("井深 H 必须大于 0。")
    if config.Rb <= 0.0 or config.Rout <= config.Rb:
        raise ValueError("必须满足 Rout > Rb > 0。")
    if config.r_inner <= 0.0:
        raise ValueError("中心管内半径 r_inner 必须大于 0。")
    if config.r_outer <= config.r_inner:
        raise ValueError("必须满足 r_outer > r_inner。")
    if config.r_outer >= config.annulus_outer_radius:
        raise ValueError("必须满足 r_outer < Rb，环空才有流通面积。")
    if config.annulus_outer_radius > config.Rb:
        raise ValueError("必须满足环空外半径不大于井壁半径。")
    if config.Q <= 0.0:
        raise ValueError("体积流量 Q 必须大于 0。")


def compute_geometry(config: ModelConfig) -> GeometryResult:
    """Compute cross-sectional areas, hydraulic diameters, mass flow rate, and velocities.

    Parameters
    ----------
    config : ModelConfig
        Model configuration containing geometry and flow parameters.

    Returns
    -------
    GeometryResult
        All computed geometric quantities (areas, diameters, flow rates).

    Notes
    -----
    Centre pipe hydraulic diameter = 2 * r_inner.
    Annulus hydraulic diameter = 2 * (outer_radius - inner_radius).
    Flow rate is converted from m3/h to m3/s before computing mass flow rate.
    """

    validate_geometry(config)

    # 中心管流通面积：圆管截面积。
    center_area = pi * config.r_inner**2

    # 环空流通面积：外圆面积减去内圆面积。
    annulus_area = pi * (config.annulus_outer_radius**2 - config.annulus_inner_radius**2)

    # 圆管水力直径等于直径；同心环空水力直径等于 2*(外半径-内半径)。
    center_dh = 2.0 * config.r_inner
    annulus_dh = 2.0 * (config.annulus_outer_radius - config.annulus_inner_radius)

    # m3/h 转换为 m3/s，再乘密度得到质量流量。
    Q_m3s = config.Q / 3600.0
    m_dot = config.rho_w * Q_m3s

    center_velocity = Q_m3s / center_area
    annulus_velocity = Q_m3s / annulus_area

    return GeometryResult(
        center_area=center_area,
        annulus_area=annulus_area,
        center_dh=center_dh,
        annulus_dh=annulus_dh,
        Q_m3s=Q_m3s,
        m_dot=m_dot,
        center_velocity=center_velocity,
        annulus_velocity=annulus_velocity,
    )
