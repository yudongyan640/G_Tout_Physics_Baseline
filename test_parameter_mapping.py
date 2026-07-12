"""井壁/短路热阻与 OGS 参数映射的回归测试。"""

from __future__ import annotations

import math
import unittest
from pathlib import Path

from borehole_resistance_calculator import calculate_borehole_wall_path
from ogs_parameter_extractor import extract_ogs_parameters
from parameter_mapping import build_baseline_parameters
from short_circuit_resistance_calculator import calculate_short_circuit_path


OGS_CASE_DIRECTORY = Path(r"E:\newdesktop\PINN\OGS_data\baseline")


class ParameterMappingTests(unittest.TestCase):
    """验证两条物理热阻路径独立且可映射为 baseline 参数。"""

    def test_wall_path_excludes_center_pipe_insulation(self) -> None:
        """井壁路径应只含环空对流、外管和回填材料。"""

        result = calculate_borehole_wall_path(
            annulus_radius=0.0797,
            annulus_h=500.0,
            outer_pipe_inner_radius=0.0797,
            outer_pipe_outer_radius=0.0889,
            outer_pipe_k=45.0,
            borehole_radius=0.1208,
            grout_k=1.5,
        )

        self.assertGreater(result["R_borehole"], 0.0)
        self.assertTrue(math.isfinite(result["U_wall"]))
        self.assertNotIn("insulation", result["components"])

    def test_short_circuit_path_contains_insulation(self) -> None:
        """中心管短路路径应包含保温层而不含回填材料。"""

        result = calculate_short_circuit_path(
            center_inner_radius=0.045,
            center_outer_radius=0.055,
            center_h=500.0,
            annulus_h=500.0,
            insulation_k=0.2,
        )

        self.assertGreater(result["R_short_circuit"], 0.0)
        self.assertTrue(math.isfinite(result["U_pa"]))
        self.assertIn("insulation", result["components"])
        self.assertNotIn("grout", result["components"])

    def test_mapping_contains_required_physical_keys(self) -> None:
        """映射结果必须含用户指定的岩土、流体和两类换热参数。"""

        raw = extract_ogs_parameters(
            OGS_CASE_DIRECTORY / "DBHE.prj",
            OGS_CASE_DIRECTORY / "DBHE.gml",
        )
        mapped = build_baseline_parameters(raw)

        for key in ("H", "rock_properties", "fluid_properties", "R_borehole", "U_wall", "R_short_circuit", "U_pa"):
            self.assertIn(key, mapped)
        self.assertAlmostEqual(mapped["H"], 2500.0)
        self.assertGreater(mapped["R_borehole"], 0.0)
        self.assertGreater(mapped["R_short_circuit"], 0.0)


if __name__ == "__main__":
    unittest.main()
