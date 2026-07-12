"""一维径向岩土瞬态导热求解器。

第一版把每一个 z 位置看作互相独立的一维径向导热问题，不考虑岩土轴向导热。
径向网格使用对数网格，时间推进采用隐式有限体积近似，因此比显式格式更适合多年模拟。
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi

import numpy as np
from scipy.linalg import solve_banded

from config import ModelConfig


@dataclass
class RockGrid:
    """岩土与井深方向网格。"""

    r: np.ndarray
    z: np.ndarray


def create_grids(config: ModelConfig) -> RockGrid:
    """创建 z 方向线性网格和 r 方向对数网格。"""

    z = np.linspace(0.0, config.H, config.Nz)
    r = np.logspace(np.log10(config.Rb), np.log10(config.Rout), config.Nr)
    return RockGrid(r=r, z=z)


def initial_rock_temperature(grid: RockGrid, config: ModelConfig) -> np.ndarray:
    """初始化岩土温度场 Ts(r,z,0)=Tamb+G*z。

    返回数组形状为 (Nr, Nz)，第一维是径向 r，第二维是井深 z。
    """

    initial_z_temperature = config.Tamb + config.G * grid.z
    return np.tile(initial_z_temperature, (grid.r.size, 1))


def _control_volume_faces(r: np.ndarray) -> np.ndarray:
    """根据节点半径计算有限体积控制体边界半径。

    内边界固定为 r[0]=Rb，外边界固定为 r[-1]=Rout。
    中间面使用相邻节点半径的几何平均，更适合对数网格。
    """

    faces = np.empty(r.size + 1)
    faces[0] = r[0]
    faces[-1] = r[-1]
    faces[1:-1] = np.sqrt(r[:-1] * r[1:])
    return faces


def update_rock_temperature(
    Ts_old: np.ndarray,
    q_wall: np.ndarray,
    grid: RockGrid,
    config: ModelConfig,
    dt_seconds: float,
) -> np.ndarray:
    """用井壁热流 q_wall 更新岩土温度。

    参数
    ----
    Ts_old:
        上一时刻岩土温度，形状 (Nr, Nz)。
    q_wall:
        流体从井壁获得的单位长度热量，单位 W/m，形状 (Nz,)。
        当 q_wall > 0 时，表示岩土向流体放热，因此近井岩土应该降温。
    grid:
        r-z 网格。
    config:
        模型配置。
    dt_seconds:
        时间步长，单位 s。

    实现说明
    ----
    对每个 z 独立求解：
    rho*cr*dT/dt = kr/r * d/dr(r*dT/dr)

    内边界通过源项体现取热：
    q_wall > 0 时，在最内侧控制体的能量方程右端减去 q_wall。
    外边界采用 Dirichlet：Ts(Rout,z,t)=Tamb+G*z。
    """

    r = grid.r
    z = grid.z
    Nr = r.size
    Nz = z.size
    faces = _control_volume_faces(r)

    # 每个径向节点对应的单位长度控制体体积，单位 m2（因为按 1 m 井长计）。
    volumes = pi * (faces[1:] ** 2 - faces[:-1] ** 2)

    # 相邻节点之间的导热导纳，单位 W/(m K)。
    # 使用圆柱坐标导热的有限体积形式：G = 2*pi*k*r_face/dr。
    conductance = np.empty(Nr - 1)
    for i in range(Nr - 1):
        dr = r[i + 1] - r[i]
        conductance[i] = 2.0 * pi * config.kr * faces[i + 1] / dr

    capacity_over_dt = config.rho_r * config.cr * volumes / dt_seconds
    Ts_new = np.empty_like(Ts_old)

    for j in range(Nz):
        far_field_temperature = config.Tamb + config.G * z[j]

        # solve_banded 使用三对角带状矩阵：
        # ab[0,1:] 是上对角，ab[1,:] 是主对角，ab[2,:-1] 是下对角。
        ab = np.zeros((3, Nr))
        rhs = capacity_over_dt * Ts_old[:, j]

        for i in range(Nr):
            if i == Nr - 1:
                # 远场边界温度保持原始地温。
                ab[1, i] = 1.0
                rhs[i] = far_field_temperature
                continue

            main = capacity_over_dt[i]

            if i > 0:
                west = conductance[i - 1]
                main += west
                ab[2, i - 1] = -west

            if i < Nr - 1:
                east = conductance[i]
                main += east
                ab[0, i + 1] = -east

            ab[1, i] = main

        # 井壁取热符号：q_wall>0 表示热量离开岩土进入流体，所以岩土能量减少。
        rhs[0] -= q_wall[j]

        Ts_new[:, j] = solve_banded((1, 1), ab, rhs)

    return Ts_new


def update_rock_temperature_implicit_wall(
    Ts_old: np.ndarray,
    Ta: np.ndarray,
    U_wall: float,
    grid: RockGrid,
    config: ModelConfig,
    dt_seconds: float,
) -> np.ndarray:
    """用隐式井壁 Robin 边界更新岩土温度。

    与 update_rock_temperature 直接使用显式 q_wall 不同，本函数把
    q_wall = U_wall * (Twall_new - Ta)
    写入最内侧岩土控制体的隐式方程。这样当井壁温度在一个大时间步内下降时，
    取热热流会同步减小，可避免强换热条件下的非物理过冷和振荡。

    物理符号仍然保持一致：
    - 若 Twall_new > Ta，则 q_wall > 0，岩土向流体放热；
    - 在岩土能量方程中表现为 -U_wall*(Twall_new-Ta)，因此最内侧岩土降温。
    """

    r = grid.r
    z = grid.z
    Nr = r.size
    Nz = z.size
    faces = _control_volume_faces(r)
    volumes = pi * (faces[1:] ** 2 - faces[:-1] ** 2)

    conductance = np.empty(Nr - 1)
    for i in range(Nr - 1):
        dr = r[i + 1] - r[i]
        conductance[i] = 2.0 * pi * config.kr * faces[i + 1] / dr

    capacity_over_dt = config.rho_r * config.cr * volumes / dt_seconds
    Ts_new = np.empty_like(Ts_old)

    for j in range(Nz):
        far_field_temperature = config.Tamb + config.G * z[j]
        ab = np.zeros((3, Nr))
        rhs = capacity_over_dt * Ts_old[:, j]

        for i in range(Nr):
            if i == Nr - 1:
                ab[1, i] = 1.0
                rhs[i] = far_field_temperature
                continue

            main = capacity_over_dt[i]

            if i > 0:
                west = conductance[i - 1]
                main += west
                ab[2, i - 1] = -west

            if i < Nr - 1:
                east = conductance[i]
                main += east
                ab[0, i + 1] = -east

            if i == 0:
                # 隐式井壁换热项：
                # C/dt*Tnew = ... - U*(Twall_new-Ta)
                # 移项后主对角增加 U，右端增加 U*Ta。
                main += U_wall
                rhs[i] += U_wall * Ta[j]

            ab[1, i] = main

        Ts_new[:, j] = solve_banded((1, 1), ab, rhs)

    return Ts_new
