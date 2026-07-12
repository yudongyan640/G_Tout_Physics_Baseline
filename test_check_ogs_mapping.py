"""OGS 映射检查规则的回归测试。"""

from __future__ import annotations

import unittest

from check_ogs_mapping import validate_mapping
from ogs_parameter_extractor import extract_ogs_parameters
from parameter_mapping import build_baseline_parameters


class OgsMappingCheckTests(unittest.TestCase):
    """验证正常 DBHE 映射能通过 SI、缺失和数值检查。"""

    def test_dbhe_mapping_has_no_required_missing_or_anomalies(self) -> None:
        """真实 DBHE 定义应具备所有 baseline 必填物理输入。"""

        raw = extract_ogs_parameters(
            r"E:\newdesktop\PINN\OGS_data\baseline\DBHE.prj",
            r"E:\newdesktop\PINN\OGS_data\baseline\DBHE.gml",
        )
        report = validate_mapping(raw, build_baseline_parameters(raw))

        self.assertEqual(report["missing_required"], [])
        self.assertEqual(report["anomalies"], [])
        self.assertTrue(report["si_units_consistent"])


if __name__ == "__main__":
    unittest.main()
