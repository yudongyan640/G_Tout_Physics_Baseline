"""几何与流动基础量计算。

本文件只处理面积、水力直径、质量流量和流速等基础几何/流动量。
换热关联式放在 heat_transfer.py 中，便于后续单独替换。
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi

from config import ModelConfig


@dataclass
class GeometryResult:
    """几何与流动计算结果。"""

    center_area: float
    annulus_area: float
    center_dh: float
    annulus_dh: float
    Q_m3s: float
    m_dot: float
    center_velocity: float
    annulus_velocity: float


def validate_geometry(config: ModelConfig) -> None:
    """检查几何参数是否基本合理。

    如果几何参数不合理，直接抛出 ValueError，避免后续求解得到无意义结果。
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
    """根据配置计算面积、水力直径、质量流量和流速。"""

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
