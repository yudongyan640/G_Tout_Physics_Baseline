"""
Module name:
    fluid_bvp_solver.py

Purpose:
    Solve the coupled quasi-steady fluid energy equations as a boundary-value
    problem (BVP).

    Given the borehole wall temperature profile Twall(z) at the current time
    step, compute:
        - Annulus downward-flowing fluid temperature Ta(z)
        - Inner-pipe upward-flowing fluid temperature Tp(z)
        - Outlet temperature Tout = Tp(0)

    The outlet temperature is not a boundary condition but a solution result.

Physical model:
    - Annulus:  m_dot * cw * dTa/dz = U_wall * (Twall - Ta) + U_pa * (Tp - Ta)
    - Inner pipe: m_dot * cw * dTp/dz = U_pa * (Tp - Ta)
    - Boundaries: Ta(0) = Tin, Tp(H) = Ta(H)

Dependencies:
    - numpy
    - scipy.integrate.solve_bvp
    - config.ModelConfig
    - heat_transfer.HeatTransferResult

Outputs:
    - FluidSolution dataclass containing temperature profiles and diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.integrate import solve_bvp

from config import ModelConfig
from heat_transfer import HeatTransferResult


@dataclass
class FluidSolution:
    """Solution of the fluid BVP at one time step.

    Attributes
    ----------
    z : np.ndarray
        Depth coordinates (m).
    Ta : np.ndarray
        Annulus fluid temperature profile (degC).
    Tp : np.ndarray
        Inner pipe fluid temperature profile (degC).
    Tout : float
        Outlet temperature at z = 0 (degC).
    q_wall : np.ndarray
        Borehole wall heat flux per unit length (W/m).
    success : bool
        Whether solve_bvp converged.
    message : str
        Solver status message.
    """

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
    """Construct the initial guess for solve_bvp.

    If a previous solution exists (previous time step), it is reused directly
    as the initial guess, which improves convergence stability.
    Otherwise, a linear profile from Tin to Twall(H) is used for Ta, with Tp
    slightly above Ta.

    Parameters
    ----------
    z : np.ndarray
        Depth grid (m).
    Twall : np.ndarray
        Borehole wall temperature profile at the current time (degC).
    config : ModelConfig
        Model configuration containing the inlet temperature.
    previous_solution : FluidSolution or None
        Solution from the previous time step, if available.

    Returns
    -------
    np.ndarray
        Initial guess array of shape (2, z.size) for [Ta; Tp].
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
    """Solve the quasi-steady fluid BVP for the current time step.

    Governing equations:
        m_dot * cw * dTa/dz = U_wall * (Twall - Ta) + U_pa * (Tp - Ta)
        m_dot * cw * dTp/dz = U_pa * (Tp - Ta)

    Boundary conditions:
        Ta(0) = Tin
        Tp(H) = Ta(H)

    Parameters
    ----------
    z : np.ndarray
        Depth grid (m).
    Twall : np.ndarray
        Borehole wall temperature profile (degC).
    config : ModelConfig
        Model configuration.
    heat_transfer : HeatTransferResult
        Heat transfer coefficients (U_wall, U_pa, mass flow rate, etc.).
    previous_solution : FluidSolution or None
        Previous time-step solution for initial guess.

    Returns
    -------
    FluidSolution
        Temperature profiles, outlet temperature, and solver diagnostics.
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

