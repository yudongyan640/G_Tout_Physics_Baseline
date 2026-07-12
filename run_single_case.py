"""单工况运行入口。

默认工况为 H=2500 m、Q=30 m3/h、Tin=10 degC、t_end=20 years、dt=30 days。
本脚本只在用户手动运行时执行，不应在项目创建或修改阶段自动启动长时间模拟。
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
