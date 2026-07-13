"""
Module name:
    rock_solver_1d.py

Purpose:
    Solve the transient 1D radial heat conduction equation in the rock
    surrounding the borehole.

    Each depth (z) position is treated as an independent 1D radial problem;
    axial (vertical) heat conduction in the rock is neglected in this version.
    The radial mesh uses logarithmic spacing for higher resolution near the
    borehole wall, and time integration uses an implicit finite-volume scheme.

Physical model:
    rho_r * cr * dTs/dt = kr * (1/r) * d/dr(r * dTs/dr)

    Boundary conditions:
        - Implicit Robin (borehole wall): q_wall = U_wall * (Twall_new - Ta)
        - Dirichlet (far-field): Ts(Rout, z, t) = Tamb + G * z

Dependencies:
    - numpy
    - scipy.linalg.solve_banded
    - config.ModelConfig

Outputs:
    - RockGrid dataclass (r and z arrays)
    - Initial rock temperature field (Nr × Nz array)
    - Updated rock temperature field after each time step
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi

import numpy as np
from scipy.linalg import solve_banded

from config import ModelConfig


@dataclass
class RockGrid:
    """Radial and vertical mesh for the rock domain.

    Attributes
    ----------
    r : np.ndarray
        Radial grid points (m), logarithmically spaced from Rb to Rout.
    z : np.ndarray
        Vertical grid points (m), uniformly spaced from 0 to H.
    """

    r: np.ndarray
    z: np.ndarray


def create_grids(config: ModelConfig) -> RockGrid:
    """Create the vertical (z) linear grid and radial (r) logarithmic grid.

    The radial grid uses log-spacing to concentrate nodes near the borehole
    wall where temperature gradients are largest.

    Parameters
    ----------
    config : ModelConfig
        Configuration with Nz, Nr, H, Rb, Rout.

    Returns
    -------
    RockGrid
        Radial and vertical mesh arrays.
    """

    z = np.linspace(0.0, config.H, config.Nz)
    r = np.logspace(np.log10(config.Rb), np.log10(config.Rout), config.Nr)
    return RockGrid(r=r, z=z)


def initial_rock_temperature(grid: RockGrid, config: ModelConfig) -> np.ndarray:
    """Initialise the rock temperature field: Ts(r, z, 0) = Tamb + G * z.

    Returns an array of shape (Nr, Nz) where the first dimension is radial
    and the second is vertical depth.

    Parameters
    ----------
    grid : RockGrid
        Radial and vertical mesh.
    config : ModelConfig
        Configuration with Tamb and G.

    Returns
    -------
    np.ndarray
        Initial rock temperature (degC) at each (r, z) point, shape (Nr, Nz).
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
    """Advance the rock temperature field using explicit borehole wall heat flux.

    For each depth z, the 1D radial heat conduction equation is solved
    independently using an implicit finite-volume scheme:

        rho * cr * dT/dt = kr / r * d/dr(r * dT/dr)

    The heat extraction is imposed as a source term at the innermost control
    volume: q_wall > 0 means heat leaves the rock and enters the fluid.

    Parameters
    ----------
    Ts_old : np.ndarray
        Rock temperature at the previous time step, shape (Nr, Nz) (degC).
    q_wall : np.ndarray
        Borehole wall heat flux per unit length, shape (Nz,) (W/m).
        Positive values indicate rock-to-fluid heat transfer.
    grid : RockGrid
        Radial and vertical mesh.
    config : ModelConfig
        Model configuration with rock properties.
    dt_seconds : float
        Time step size (s).

    Returns
    -------
    np.ndarray
        Updated rock temperature field, shape (Nr, Nz) (degC).
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
    """Advance the rock temperature field using an implicit Robin borehole wall condition.

    Unlike ``update_rock_temperature`` which uses an explicit q_wall, this
    function embeds the wall condition directly in the implicit system:

        q_wall = U_wall * (Twall_new - Ta)

    This couples the wall temperature and heat flux implicitly, preventing
    unphysical overcooling that can occur when a large explicit heat flux is
    applied over a coarse time step.

    Parameters
    ----------
    Ts_old : np.ndarray
        Rock temperature at the previous time step, shape (Nr, Nz) (degC).
    Ta : np.ndarray
        Annulus fluid temperature profile (degC).
    U_wall : float
        Unit-length wall-to-annulus heat transfer coefficient (W/(m·K)).
    grid : RockGrid
        Radial and vertical mesh.
    config : ModelConfig
        Model configuration with rock properties.
    dt_seconds : float
        Time step size (s).

    Returns
    -------
    np.ndarray
        Updated rock temperature field, shape (Nr, Nz) (degC).
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
