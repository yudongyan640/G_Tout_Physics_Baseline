"""主仿真流程。

本模块把几何、换热、流体 BVP 和岩土径向导热连接起来，形成一个可运行的纯物理 baseline。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import ModelConfig
from fluid_bvp_solver import FluidSolution, solve_fluid_bvp
from heat_transfer import HeatTransferResult, compute_heat_transfer
from rock_solver_1d import (
    RockGrid,
    create_grids,
    initial_rock_temperature,
    update_rock_temperature_implicit_wall,
)


@dataclass
class SimulationResult:
    """保存主模拟结果，便于后处理和测试。"""

    config: ModelConfig
    grid: RockGrid
    heat_transfer: HeatTransferResult
    time_s: np.ndarray
    time_days: np.ndarray
    time_years: np.ndarray
    Tout: np.ndarray
    power_W: np.ndarray
    cumulative_energy_J: np.ndarray
    final_Ta: np.ndarray
    final_Tp: np.ndarray
    final_q_wall: np.ndarray
    initial_Twall: np.ndarray
    final_Twall: np.ndarray
    final_Ts: np.ndarray
    rock_temperature_snapshots: dict[float, np.ndarray]
    rock_snapshot_actual_years: dict[float, float]
    bvp_messages: list[str]


def _build_time_array(config: ModelConfig) -> np.ndarray:
    """构造保存结果用的时间数组，包含 t=0 和最后时刻。"""

    if config.dt_seconds <= 0.0:
        raise ValueError("dt_seconds 必须大于 0。")
    if config.t_end_seconds <= 0.0:
        raise ValueError("t_end_seconds 必须大于 0。")

    n_steps = int(np.ceil(config.t_end_seconds / config.dt_seconds))
    return np.linspace(0.0, n_steps * config.dt_seconds, n_steps + 1)


def _build_snapshot_index_map(config: ModelConfig, time_years: np.ndarray) -> dict[int, float]:
    """确定哪些时间步需要保存岩土温度快照。

    由于默认时间步是 30 天，时间点通常不会精确落在 1、5、10、20 年。
    这里为每个目标年份选择最近的模拟时间步，并用目标年份作为字典 key。
    """

    index_to_target_year: dict[int, float] = {}
    for target_year in config.rock_profile_years:
        if target_year < 0.0 or target_year > float(time_years[-1]):
            continue
        nearest_index = int(np.argmin(np.abs(time_years - target_year)))
        index_to_target_year[nearest_index] = float(target_year)
    return index_to_target_year


def run_simulation(config: ModelConfig) -> SimulationResult:
    """运行单工况纯物理模拟。

    流程：
    1. 初始化 r-z 网格和岩土温度；
    2. 每个时间步读取当前井壁温度 Twall(z)；
    3. 求解准稳态流体 BVP，得到 Ta、Tp、Tout、q_wall；
    4. 用隐式井壁边界更新岩土径向温度；
    5. 保存出口水温、取热功率、累计取热量和指定年份岩土快照。
    """

    grid = create_grids(config)
    heat_transfer = compute_heat_transfer(config)
    Ts = initial_rock_temperature(grid, config)
    initial_Twall = Ts[0, :].copy()

    time_s = _build_time_array(config)
    time_years = time_s / (365.0 * 24.0 * 3600.0)
    snapshot_index_map = _build_snapshot_index_map(config, time_years)

    Tout = np.empty(time_s.size)
    power_W = np.empty(time_s.size)
    cumulative_energy_J = np.zeros(time_s.size)
    bvp_messages: list[str] = []
    rock_temperature_snapshots: dict[float, np.ndarray] = {}
    rock_snapshot_actual_years: dict[float, float] = {}

    previous_fluid_solution: FluidSolution | None = None
    final_fluid_solution: FluidSolution | None = None

    for step_index, current_time in enumerate(time_s):
        # 如果当前时间步是目标诊断年份附近的最近点，就保存完整 Ts(r,z) 快照。
        if step_index in snapshot_index_map:
            target_year = snapshot_index_map[step_index]
            rock_temperature_snapshots[target_year] = Ts.copy()
            rock_snapshot_actual_years[target_year] = float(time_years[step_index])

        Twall = Ts[0, :].copy()

        fluid_solution = solve_fluid_bvp(
            grid.z,
            Twall,
            config,
            heat_transfer,
            previous_solution=previous_fluid_solution,
        )
        bvp_messages.append(fluid_solution.message)
        if not fluid_solution.success:
            raise RuntimeError(f"第 {step_index} 个时间点流体 BVP 未收敛：{fluid_solution.message}")

        Tout[step_index] = fluid_solution.Tout
        power_W[step_index] = heat_transfer.geometry.m_dot * config.cw * (fluid_solution.Tout - config.Tin)

        if step_index > 0:
            dt = time_s[step_index] - time_s[step_index - 1]
            # 梯形积分累计取热量，单位 J。
            cumulative_energy_J[step_index] = cumulative_energy_J[step_index - 1] + 0.5 * (
                power_W[step_index - 1] + power_W[step_index]
            ) * dt

        final_fluid_solution = fluid_solution
        previous_fluid_solution = fluid_solution

        # 最后一个保存时刻不需要再向后推进岩土温度。
        if step_index < time_s.size - 1:
            next_dt = time_s[step_index + 1] - current_time
            Ts = update_rock_temperature_implicit_wall(
                Ts,
                fluid_solution.Ta,
                heat_transfer.U_wall,
                grid,
                config,
                next_dt,
            )

    if final_fluid_solution is None:
        raise RuntimeError("模拟没有产生任何流体解。")

    return SimulationResult(
        config=config,
        grid=grid,
        heat_transfer=heat_transfer,
        time_s=time_s,
        time_days=time_s / (24.0 * 3600.0),
        time_years=time_years,
        Tout=Tout,
        power_W=power_W,
        cumulative_energy_J=cumulative_energy_J,
        final_Ta=final_fluid_solution.Ta,
        final_Tp=final_fluid_solution.Tp,
        final_q_wall=final_fluid_solution.q_wall,
        initial_Twall=initial_Twall,
        final_Twall=Ts[0, :].copy(),
        final_Ts=Ts,
        rock_temperature_snapshots=rock_temperature_snapshots,
        rock_snapshot_actual_years=rock_snapshot_actual_years,
        bvp_messages=bvp_messages,
    )
