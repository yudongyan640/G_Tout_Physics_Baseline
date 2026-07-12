"""准稳态流体一维边值问题求解器。

给定当前时刻井壁温度 Twall(z)，求解环空下降流体 Ta(z) 与中心管上升流体 Tp(z)。
出口水温不是输入边界条件，而是求解结果 Tout = Tp(0)。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_bvp

from config import ModelConfig
from heat_transfer import HeatTransferResult


@dataclass
class FluidSolution:
    """流体 BVP 的求解结果。"""

    z: np.ndarray
    Ta: np.ndarray
    Tp: np.ndarray
    Tout: float
    q_wall: np.ndarray
    success: bool
    message: str


def build_initial_guess(
    z: np.ndarray,
    Twall: np.ndarray,
    config: ModelConfig,
    previous_solution: FluidSolution | None = None,
) -> np.ndarray:
    """构造 solve_bvp 初始猜测。

    如果上一时间步已经有解，则直接用上一时间步结果作为初值，通常能提高收敛稳定性。
    否则用入口水温到地层温度的线性升高作为 Ta 猜测，Tp 略高于 Ta。
    """

    if previous_solution is not None:
        return np.vstack([previous_solution.Ta, previous_solution.Tp])

    Ta_guess = np.linspace(config.Tin, float(Twall[-1]), z.size)
    Tp_guess = Ta_guess + 2.0
    Tp_guess[-1] = Ta_guess[-1]  # 井底连通条件 Tp(H)=Ta(H) 的初始近似
    return np.vstack([Ta_guess, Tp_guess])


def solve_fluid_bvp(
    z: np.ndarray,
    Twall: np.ndarray,
    config: ModelConfig,
    heat_transfer: HeatTransferResult,
    previous_solution: FluidSolution | None = None,
) -> FluidSolution:
    """求解当前时刻的流体准稳态 BVP。

    控制方程：
    m_dot*cw*dTa/dz = U_wall*(Twall-Ta) + U_pa*(Tp-Ta)
    m_dot*cw*dTp/dz = U_pa*(Tp-Ta)

    边界条件：
    Ta(0)=Tin
    Tp(H)=Ta(H)
    """

    z = np.asarray(z, dtype=float)
    Twall = np.asarray(Twall, dtype=float)
    m_dot_cw = heat_transfer.geometry.m_dot * config.cw

    def ode(z_eval: np.ndarray, y: np.ndarray) -> np.ndarray:
        """solve_bvp 调用的 ODE 右端项。"""

        Twall_eval = np.interp(z_eval, z, Twall)
        Ta = y[0]
        Tp = y[1]

        # 井壁给环空的热量和中心管热短路共同改变环空温度。
        dTa_dz = (
            heat_transfer.U_wall * (Twall_eval - Ta)
            + heat_transfer.U_pa * (Tp - Ta)
        ) / m_dot_cw

        # 由于 z 向下为正，而中心管实际向上流动，采用题目给出的符号形式。
        dTp_dz = heat_transfer.U_pa * (Tp - Ta) / m_dot_cw
        return np.vstack([dTa_dz, dTp_dz])

    def boundary_conditions(ya: np.ndarray, yb: np.ndarray) -> np.ndarray:
        """边界残差：ya 为 z=0，yb 为 z=H。"""

        return np.array(
            [
                ya[0] - config.Tin,  # Ta(0)=Tin
                yb[1] - yb[0],  # Tp(H)=Ta(H)
            ]
        )

    initial_guess = build_initial_guess(z, Twall, config, previous_solution)
    solution = solve_bvp(
        ode,
        boundary_conditions,
        z,
        initial_guess,
        tol=config.bvp_tol,
        max_nodes=config.bvp_max_nodes,
    )

    Ta = solution.sol(z)[0]
    Tp = solution.sol(z)[1]
    q_wall = heat_transfer.U_wall * (Twall - Ta)

    return FluidSolution(
        z=z,
        Ta=Ta,
        Tp=Tp,
        Tout=float(Tp[0]),
        q_wall=q_wall,
        success=bool(solution.success),
        message=str(solution.message),
    )

