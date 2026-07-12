"""OGS XML 参数解析模块的回归测试。"""

from __future__ import annotations

import unittest
from pathlib import Path

from ogs_parameter_extractor import extract_ogs_parameters


OGS_CASE_DIRECTORY = Path(r"E:\newdesktop\PINN\OGS_data\baseline")


class OgsParameterExtractorTests(unittest.TestCase):
    """验证只从 OGS 项目 XML 与几何 XML 提取定义参数。"""

    def test_extracts_dbhe_physical_parameters_without_result_files(self) -> None:
        """应正确读取 DBHE 的几何、物性与地温表达式参数。"""

        parameters = extract_ogs_parameters(
            OGS_CASE_DIRECTORY / "DBHE.prj",
            OGS_CASE_DIRECTORY / "DBHE.gml",
        )

        self.assertAlmostEqual(parameters["geometry"]["H"], 2500.0)
        self.assertAlmostEqual(parameters["geometry"]["Rb"], 0.1208)
        self.assertAlmostEqual(parameters["geometry"]["annulus_outer_radius"], 0.0797)
        self.assertAlmostEqual(parameters["rock"]["thermal_conductivity"], 1.54)
        self.assertAlmostEqual(parameters["rock"]["density"], 2400.0)
        self.assertAlmostEqual(parameters["fluid"]["density"], 998.0)
        self.assertAlmostEqual(parameters["geothermal"]["Tamb"], 14.8)
        self.assertAlmostEqual(parameters["geothermal"]["gradient"], 0.033)
        self.assertAlmostEqual(parameters["operation"]["flow_rate_m3s"][0], 0.00556)
        self.assertAlmostEqual(parameters["operation"]["inlet_temperature_degC"][0], 4.0)
        self.assertEqual(parameters["source_files"], ["DBHE.prj", "DBHE.gml"])


if __name__ == "__main__":
    unittest.main()
