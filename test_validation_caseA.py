"""Case A 连续运行验证脚本的回归测试。"""

from __future__ import annotations

import csv
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from validation_caseA import (
    OUTLET_COLUMN,
    build_caseA_config,
    calculate_metrics,
    load_ogs_outlet_data,
)


class ValidationCaseATests(unittest.TestCase):
    """验证 OGS 出口数据读取、20 年配置和误差指标公式。"""

    def test_loads_only_confirmed_outlet_column_and_converts_to_years(self) -> None:
        """只读取允许的时间和出口温度列，并按 365 天换算为 year。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "caseA_outlet.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=["Time", OUTLET_COLUMN, "unused_field"])
                writer.writeheader()
                writer.writerow({"Time": "0", OUTLET_COLUMN: "30.0", "unused_field": "x"})
                writer.writerow({"Time": "31536000", OUTLET_COLUMN: "21.5", "unused_field": "x"})
            data = load_ogs_outlet_data(csv_path)

        self.assertEqual(list(data.columns), ["time_s", "time_years", "ogs_Tout_degC"])
        self.assertEqual(len(data), 2)
        self.assertAlmostEqual(float(data["time_years"].iloc[-1]), 1.0)
        self.assertAlmostEqual(float(data["ogs_Tout_degC"].iloc[-1]), 21.5)

    def test_builds_20_year_case_without_changing_resistances(self) -> None:
        """Case A 只覆盖 H/Q/Tin/时长，既有热阻映射值必须原样保留。"""

        config = build_caseA_config()

        self.assertAlmostEqual(config.H, 2501.0)
        self.assertAlmostEqual(config.Q, 26.0)
        self.assertAlmostEqual(config.Tin, 11.0)
        self.assertAlmostEqual(config.t_end_years, 20.0)
        self.assertAlmostEqual(config.borehole_resistance, 0.03385171416024736)
        self.assertAlmostEqual(config.short_circuit_resistance, 0.16228885447704483)

    def test_calculates_requested_metrics(self) -> None:
        """MAE、RMSE、R2 和 Bias 必须遵循任务指定公式。"""

        metrics = calculate_metrics(np.array([1.0, 2.0]), np.array([2.0, 4.0]))

        self.assertAlmostEqual(metrics["MAE_degC"], 1.5)
        self.assertAlmostEqual(metrics["RMSE_degC"], math.sqrt(2.5))
        self.assertAlmostEqual(metrics["Bias_degC"], -1.5)
        self.assertAlmostEqual(metrics["R2"], -1.5)


if __name__ == "__main__":
    unittest.main()
