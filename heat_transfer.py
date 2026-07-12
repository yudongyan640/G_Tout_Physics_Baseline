"""换热系数计算模块。

本文件计算 Re、Pr、Dittus-Boelter 对流换热系数，以及单位长度换热系数 U_wall 和 U_pa。
第一版假设湍流换热；如果 Re 偏低，只给出 warning，不额外切换层流模型。
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log, pi
import warnings

from config import ModelConfig
from geometry import GeometryResult, compute_geometry


@dataclass
class HeatTransferResult:
    """换热计算结果。"""

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
    """计算雷诺数 Re = rho*u*dh/mu。"""

    return rho * velocity * hydraulic_diameter / mu


def compute_prandtl(mu: float, cp: float, conductivity: float) -> float:
    """计算普朗特数 Pr = mu*cp/k。"""

    return mu * cp / conductivity


def dittus_boelter_h(conductivity: float, hydraulic_diameter: float, Re: float, Pr: float) -> float:
    """用 Dittus-Boelter 公式计算管内/环空等效对流换热系数。

    h = 0.023 * k / dh * Re**0.8 * Pr**0.4
    这里第一版统一使用加热流体常用指数 0.4。
    """

    return 0.023 * conductivity / hydraulic_diameter * Re**0.8 * Pr**0.4


def compute_heat_transfer(config: ModelConfig) -> HeatTransferResult:
    """计算全部换热参数。

    U_wall 表示井壁到环空流体的单位长度换热系数。
    当 use_effective_borehole_resistance=True 时，U_wall=1/R_borehole；
    否则回到旧写法 U_wall=2*pi*Rb*h_wall。
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
