"""
Module name:
    run_single_case.py

Purpose:
    Entry point for a single-case simulation with default parameters:
        H = 2500 m,  Q = 30 m3/h,  Tin = 10 degC,
        t_end = 20 years,  dt = 30 days.

    This script must only be executed manually by the user. It should never
    be triggered automatically during project setup or modification.

Dependencies:
    - config.ModelConfig
    - simulation.run_simulation
    - postprocess

Outputs:
    - CSV time series, JSON diagnostics and summary, PNG/SVG figures.
"""

from __future__ import annotations

from config import ModelConfig
from postprocess import build_diagnostics, format_diagnostics_text, save_outputs
from simulation import run_simulation


def main() -> None:
    """运行默认单工况、打印诊断参数并保存输出。"""

    config = ModelConfig()
    result = run_simulation(config)

    diagnostics = build_diagnostics(result)
    print(format_diagnostics_text(diagnostics))

    output_dir = save_outputs(result, config)
    print(f"Simulation finished. Outputs saved to: {output_dir}")


if __name__ == "__main__":
    main()
