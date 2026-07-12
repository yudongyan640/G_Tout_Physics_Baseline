"""summary.json 新增时间点和去启动期指标的轻量测试。"""

from types import SimpleNamespace

import numpy as np

from postprocess import build_time_based_metrics


def main() -> None:
    """用人工数组检查最近时间点取值和去启动期统计。"""

    result = SimpleNamespace(
        time_days=np.array([0.0, 1.0, 7.0, 30.0, 90.0, 365.0]),
        time_years=np.array([0.0, 1.0 / 365.0, 7.0 / 365.0, 30.0 / 365.0, 90.0 / 365.0, 1.0]),
        Tout=np.array([40.0, 30.0, 25.0, 20.0, 18.0, 16.0]),
        power_W=np.array([900.0, 700.0, 600.0, 500.0, 400.0, 300.0]),
    )

    metrics = build_time_based_metrics(result)

    assert metrics["Tout_day_1"] == 30.0
    assert metrics["Tout_day_1_actual_time_days"] == 1.0
    assert metrics["Tout_year_1"] == 16.0
    assert metrics["Tout_year_1_actual_time_years"] == 1.0
    assert metrics["power_day_30"] == 500.0
    assert metrics["power_day_30_actual_time_days"] == 30.0
    assert metrics["mean_Tout_after_30_days"] == float(np.mean([20.0, 18.0, 16.0]))
    assert metrics["mean_power_after_1_year"] == 300.0
    assert metrics["max_Tout_after_30_days"] == 20.0
    assert metrics["max_power_after_30_days"] == 500.0


if __name__ == "__main__":
    main()
