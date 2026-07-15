"""单工况独立验证脚本的回归测试。"""

from __future__ import annotations

import csv
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

from validation_single_case import (
    OUTLET_COLUMN,
    build_validation_config,
    calculate_metrics,
    load_ogs_outlet_data,
)


class ValidationSingleCaseTests(unittest.TestCase):
    """验证 OGS Tout 读取、指标公式和指定工况配置。"""

    def test_loads_confirmed_outlet_column_and_converts_seconds_to_years(self) -> None:
        """应只读取确认的出口列，并按 365 天换算年。"""

        with tempfile.TemporaryDirectory() as temporary_directory:
            csv_path = Path(temporary_directory) / "outlet.csv"
            with csv_path.open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=["Time", OUTLET_COLUMN])
                writer.writeheader()
                writer.writerow({"Time": "0", OUTLET_COLUMN: "11.0"})
                writer.writerow({"Time": "31536000", OUTLET_COLUMN: "12.5"})
            data = load_ogs_outlet_data(csv_path)

        self.assertEqual(data.shape[0], 2)
        self.assertAlmostEqual(float(data["time_years"].iloc[-1]), 1.0)
        self.assertAlmostEqual(float(data["ogs_Tout_degC"].iloc[-1]), 12.5)

    def test_calculates_requested_metrics(self) -> None:
        """MAE、RMSE、R2 与 Bias 必须遵循任务给定公式。"""

        metrics = calculate_metrics(np.array([1.0, 2.0]), np.array([2.0, 4.0]))

        self.assertAlmostEqual(metrics["MAE_degC"], 1.5)
        self.assertAlmostEqual(metrics["RMSE_degC"], math.sqrt(2.5))
        self.assertAlmostEqual(metrics["Bias_degC"], -1.5)
        self.assertAlmostEqual(metrics["R2"], -1.5)

    def test_builds_requested_case_without_changing_mapped_resistances(self) -> None:
        """验证工况只能覆盖 H/Q/Tin 和运行时长，热阻保持当前映射值。"""

        config = build_validation_config(622080000.0)

        self.assertAlmostEqual(config.H, 2501.0)
        self.assertAlmostEqual(config.Q, 26.0)
        self.assertAlmostEqual(config.Tin, 11.0)
        self.assertAlmostEqual(config.t_end_years, 622080000.0 / 31536000.0)
        self.assertAlmostEqual(config.borehole_resistance, 0.03385171416024736)
        self.assertAlmostEqual(config.short_circuit_resistance, 0.16228885447704483)


if __name__ == "__main__":
    unittest.main()
