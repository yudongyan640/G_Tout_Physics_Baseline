"""early_time_check.py 的轻量契约检查。

这个测试不运行 1 年数值模拟，只检查脚本暴露的配置和输出路径是否符合任务要求。
"""

from pathlib import Path

import early_time_check


def main() -> None:
    """检查 early_time_check.py 的关键配置和输出文件清单。"""

    config = early_time_check.build_early_time_config()
    expected_output_dir = Path("outputs") / "early_time_check"

    assert config.H == 2500.0
    assert config.Q == 30.0
    assert config.Tin == 10.0
    assert config.t_end_years == 1.0
    assert config.dt_days == 1.0
    assert config.Nz == 201
    assert config.Nr == 80
    assert early_time_check.OUTPUT_DIR == expected_output_dir

    expected_files = {
        expected_output_dir / "tout_timeseries.csv",
        expected_output_dir / "fig_tout_first_year.png",
        expected_output_dir / "fig_tout_first_year.svg",
        expected_output_dir / "fig_power_first_year.png",
        expected_output_dir / "fig_power_first_year.svg",
    }
    assert set(early_time_check.expected_output_files()) == expected_files


if __name__ == "__main__":
    main()
