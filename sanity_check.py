"""
Module name:
    sanity_check.py

Purpose:
    Quick smoke test using a small mesh and a 10-day simulation.

    Checks:
        1. The code runs without errors.
        2. Tout > Tin (physical consistency).
        3. q_wall is positive at most depths (heat flows from rock to fluid).
        4. Near-well rock temperature decreases (consistent with heat extraction).

    This script is intended for rapid verification before running the full
    20-year simulation.

Dependencies:
    - config.ModelConfig
    - simulation.run_simulation
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from config import ModelConfig
from simulation import run_simulation


def main() -> None:
    """运行短时间 sanity check。"""

    config = replace(
        ModelConfig(),
        H=1000.0,
        t_end_years=10.0 / 365.0,
        dt_days=1.0,
        Nz=51,
        Nr=30,
    )

    result = run_simulation(config)

    tout_greater_than_tin = bool(result.Tout[-1] > config.Tin)
    positive_q_ratio = float(np.mean(result.final_q_wall > 0.0))
    wall_cooling_mean = float(np.mean(result.initial_Twall - result.final_Twall))
    wall_temperature_decreased = bool(wall_cooling_mean > 0.0)

    print("Sanity check report")
    print("-------------------")
    print(f"Final Tout: {result.Tout[-1]:.3f} degC")
    print(f"Tin: {config.Tin:.3f} degC")
    print(f"Tout > Tin: {tout_greater_than_tin}")
    print(f"Positive q_wall ratio: {positive_q_ratio:.3f}")
    print(f"Mean near-wall cooling: {wall_cooling_mean:.6f} K")
    print(f"Near-wall rock temperature decreased: {wall_temperature_decreased}")
    print("")
    print("Expected physical trends:")
    print("1. Larger H usually increases Tout.")
    print("2. Larger Q may reduce Tout, but heat extraction power may increase.")
    print("3. Larger Tin increases Tout, while Tout-Tin may decrease.")
    print("4. Larger lambda_ins strengthens thermal short-circuiting and may reduce Tout.")
    print("5. Longer operation causes thermal drawdown, so Tout usually decreases toward stable values.")
    print("6. Larger kr improves long-term heat supply and slows Tout decline.")

    if not tout_greater_than_tin:
        raise AssertionError("Sanity check failed: Tout should be greater than Tin for this default case.")
    if positive_q_ratio < 0.7:
        raise AssertionError("Sanity check failed: q_wall should be positive at most depths.")
    if not wall_temperature_decreased:
        raise AssertionError("Sanity check failed: near-wall rock should cool when q_wall is positive.")


if __name__ == "__main__":
    main()

