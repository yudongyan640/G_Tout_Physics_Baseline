"""井筒热阻计算工具的公式测试。"""

import math

from borehole_resistance_calculator import (
    compute_convective_resistance,
    compute_cylindrical_layer_resistance,
    compute_total_borehole_resistance,
)


def main() -> None:
    """检查圆筒导热热阻、对流热阻和总热阻求和。"""

    layer_r = compute_cylindrical_layer_resistance(r_inner=0.05, r_outer=0.10, k=2.0)
    expected_layer_r = math.log(0.10 / 0.05) / (2.0 * math.pi * 2.0)
    assert abs(layer_r - expected_layer_r) < 1.0e-12

    conv_r = compute_convective_resistance(radius=0.05, h=100.0)
    expected_conv_r = 1.0 / (2.0 * math.pi * 0.05 * 100.0)
    assert abs(conv_r - expected_conv_r) < 1.0e-12

    total_r = compute_total_borehole_resistance(
        layers=[{"r_inner": 0.05, "r_outer": 0.10, "k": 2.0}],
        convective_terms=[{"radius": 0.05, "h": 100.0}],
    )
    assert abs(total_r - (expected_layer_r + expected_conv_r)) < 1.0e-12


if __name__ == "__main__":
    main()
