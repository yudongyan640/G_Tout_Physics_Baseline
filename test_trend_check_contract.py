"""trend_check_H_Q.py 的轻量契约检查。"""

from pathlib import Path

import trend_check_H_Q


def main() -> None:
    """检查 3x3 趋势验证脚本的固定参数和输出文件清单。"""

    assert trend_check_H_Q.H_LIST == [2000.0, 2500.0, 3000.0]
    assert trend_check_H_Q.Q_LIST == [15.0, 30.0, 40.0]
    assert trend_check_H_Q.TIN == 10.0
    assert trend_check_H_Q.R_BOREHOLE == 0.10
    assert trend_check_H_Q.OUTPUT_DIR == Path("outputs") / "trend_check_H_Q"

    expected_files = {
        trend_check_H_Q.OUTPUT_DIR / "trend_summary.csv",
        trend_check_H_Q.OUTPUT_DIR / "fig_Tout_vs_time_H_Q.png",
        trend_check_H_Q.OUTPUT_DIR / "fig_Tout_vs_time_H_Q.svg",
        trend_check_H_Q.OUTPUT_DIR / "fig_final_Tout_heatmap.png",
        trend_check_H_Q.OUTPUT_DIR / "fig_final_Tout_heatmap.svg",
        trend_check_H_Q.OUTPUT_DIR / "fig_mean_power_heatmap.png",
        trend_check_H_Q.OUTPUT_DIR / "fig_mean_power_heatmap.svg",
    }
    assert set(trend_check_H_Q.expected_output_files()) == expected_files


if __name__ == "__main__":
    main()
