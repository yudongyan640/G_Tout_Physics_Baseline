"""OGS 映射参数加载到 ModelConfig 的回归测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from config import ModelConfig
from ogs_parameter_extractor import extract_ogs_parameters
from parameter_mapping import build_baseline_parameters, write_baseline_parameters


OGS_CASE_DIRECTORY = Path(r"E:\newdesktop\PINN\OGS_data\baseline")


class OgsConfigLoadingTests(unittest.TestCase):
    """验证启用开关时只覆盖映射的物理参数。"""

    def test_uses_mapped_geometry_and_two_transfer_coefficients(self) -> None:
        """ModelConfig 应加载映射的几何、岩土、流体和 U 值。"""

        raw = extract_ogs_parameters(OGS_CASE_DIRECTORY / "DBHE.prj", OGS_CASE_DIRECTORY / "DBHE.gml")
        mapped = build_baseline_parameters(raw)
        with tempfile.TemporaryDirectory() as temporary_directory:
            mapping_path = write_baseline_parameters(mapped, Path(temporary_directory) / "mapped.json")
            config = ModelConfig(use_ogs_parameters=True, ogs_parameters_path=mapping_path)

        self.assertAlmostEqual(config.H, 2500.0)
        self.assertAlmostEqual(config.Rb, 0.1208)
        self.assertAlmostEqual(config.r_inner, 0.045)
        self.assertAlmostEqual(config.annulus_outer_radius, 0.0797)
        self.assertAlmostEqual(config.borehole_resistance, mapped["R_borehole"])
        self.assertAlmostEqual(config.short_circuit_resistance, mapped["R_short_circuit"])
        self.assertAlmostEqual(config.rho_r, 2400.0)
        self.assertAlmostEqual(config.cr, 1780.0)
        self.assertAlmostEqual(config.Q, 20.016)
        self.assertAlmostEqual(config.Tin, 4.0)

    def test_preserves_default_configuration_when_ogs_loading_disabled(self) -> None:
        """关闭开关时必须保留现有默认值，确保历史工作流兼容。"""

        config = ModelConfig(use_ogs_parameters=False)
        self.assertAlmostEqual(config.H, 2500.0)
        self.assertAlmostEqual(config.Rb, 0.1)
        self.assertAlmostEqual(config.r_inner, 0.04)


if __name__ == "__main__":
    unittest.main()
