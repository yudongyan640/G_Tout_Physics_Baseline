"""项目集中配置文件。

本文件用 dataclass 保存单工况参数、几何参数、物性参数、数值网格和输出路径。
第一版 baseline 只依赖这些物理输入，不读取任何 OGS 计算结果。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelConfig:
    """中深层同轴套管地埋管换热器纯物理 baseline 的配置。

    说明：
    - 温度使用摄氏度 degC。由于传热方程只用温差，degC 与 K 的温差等价。
    - 时间内部统一换算为秒 s。
    - 流量输入单位为 m3/h，内部换算为 m3/s。
    - 几何参数是第一版占位默认值，后续应替换为 OGS 模型或实际工程尺寸。
    """

    # 单工况输入参数
    H: float = 2500.0  # 井深，m
    Q: float = 30.0  # 体积流量，m3/h
    Tin: float = 10.0  # 环空入口水温，degC
    Tamb: float = 15.0  # 地表温度，degC
    G: float = 0.035  # 地温梯度，K/m
    t_end_years: float = 20.0  # 默认长周期模拟时间，年
    dt_days: float = 30.0  # 默认时间步长，天

    # 数值网格
    Nz: int = 201  # z 方向网格点数
    Nr: int = 80  # r 方向网格点数
    Rb: float = 0.10  # 井壁半径，m
    Rout: float = 50.0  # 岩土远场半径，m

    # 流体物性，按水的常用常温物性给出
    rho_w: float = 1000.0  # 水密度，kg/m3
    cw: float = 4200.0  # 水比热，J/(kg K)
    kw: float = 0.598  # 水导热系数，W/(m K)
    mu_w: float = 1.0e-3  # 水动力黏度，Pa s

    # 岩土物性
    rho_r: float = 2200.0  # 岩土密度，kg/m3
    cr: float = 1100.0  # 岩土比热，J/(kg K)
    kr: float = 2.0  # 岩土导热系数，W/(m K)

    # 同轴套管几何占位值
    # 注意：这些尺寸只是第一版默认占位值，后续应替换为 OGS 模型或实际工程中的真实尺寸。
    r_inner: float = 0.04  # 中心管内半径，m
    r_outer: float = 0.06  # 中心管外/保温层外半径，m
    r_annulus_outer: float | None = None  # 环空外半径；None 时兼容旧模型并取 Rb
    lambda_ins: float = 0.005  # 保温层导热系数，W/(m K)

    # 井筒等效热阻设置。
    # True 表示用 borehole_resistance 代表水泥环、套管、接触热阻等综合井筒热阻。
    # False 表示退回到旧写法，只用环空侧对流换热估算 U_wall。
    use_effective_borehole_resistance: bool = True
    borehole_resistance: float = 0.10  # 等效井筒热阻，m*K/W；启用时 U_wall=1/R
    # 中心管与环空之间的热短路等效热阻。默认关闭以保持历史公式和结果不变。
    use_effective_short_circuit_resistance: bool = False
    short_circuit_resistance: float = 0.10  # 单位长度热阻，m*K/W；启用时 U_pa=1/R

    # OGS 参数映射开关。开启后只读取本项目 outputs 中的 JSON，不读取任何 OGS 结果文件。
    use_ogs_parameters: bool = True
    ogs_parameters_path: Path = Path("outputs/baseline_physical_parameters.json")

    # 数值求解控制
    bvp_tol: float = 1.0e-4  # solve_bvp 收敛容差
    bvp_max_nodes: int = 10000  # solve_bvp 最大节点数
    turbulent_re_warning: float = 2300.0  # 低于该 Re 时提示湍流关联式可能不适用

    # 岩土径向温度剖面诊断年份。后处理会从模拟过程中保存这些年份附近的快照。
    rock_profile_years: tuple[float, ...] = (0.0, 1.0, 5.0, 10.0, 20.0)

    # 输出目录。默认相对于项目根目录，不写死绝对路径。
    output_root: Path = Path("outputs")

    def __post_init__(self) -> None:
        """在用户启用开关时，用已映射的 OGS 物理参数覆盖默认占位参数。"""

        if not self.use_ogs_parameters:
            return
        mapping_path = Path(self.ogs_parameters_path)
        if not mapping_path.exists():
            raise FileNotFoundError(
                f"已启用 use_ogs_parameters，但未找到映射文件：{mapping_path}。"
                "请先运行 check_ogs_mapping.py 生成参数文件。"
            )
        mapped = json.loads(mapping_path.read_text(encoding="utf-8"))
        rock = mapped["rock_properties"]
        fluid = mapped["fluid_properties"]
        geothermal = mapped["geothermal"]

        # 以下赋值均为 SI 单位；不改变求解器，只替换其使用的物理输入。
        self.H = float(mapped["H"])
        self.Q = float(mapped["Q"])
        self.Tin = float(mapped["Tin"])
        self.Rb = float(mapped["Rb"])
        self.r_inner = float(mapped["r_inner"])
        self.r_outer = float(mapped["r_outer"])
        self.r_annulus_outer = float(mapped["annulus_outer_radius"])
        self.rho_r = float(rock["density"])
        self.cr = float(rock["heat_capacity"])
        self.kr = float(rock["thermal_conductivity"])
        self.rho_w = float(fluid["density"])
        self.cw = float(fluid["heat_capacity"])
        self.kw = float(fluid["thermal_conductivity"])
        self.mu_w = float(fluid["viscosity"])
        self.Tamb = float(geothermal["Tamb"])
        self.G = float(geothermal["gradient"])
        self.lambda_ins = float(mapped["insulation_thermal_conductivity"])
        self.borehole_resistance = float(mapped["R_borehole"])
        self.short_circuit_resistance = float(mapped["R_short_circuit"])
        self.use_effective_borehole_resistance = True
        self.use_effective_short_circuit_resistance = True

    @property
    def annulus_inner_radius(self) -> float:
        """环空内半径，即中心管外/保温层外半径。"""

        return self.r_outer

    @property
    def annulus_outer_radius(self) -> float:
        """环空外半径；未映射时近似等于井壁半径以兼容旧版本。"""

        return self.Rb if self.r_annulus_outer is None else self.r_annulus_outer

    @property
    def dt_seconds(self) -> float:
        """时间步长，单位 s。"""

        return self.dt_days * 24.0 * 3600.0

    @property
    def t_end_seconds(self) -> float:
        """总模拟时间，单位 s。"""

        return self.t_end_years * 365.0 * 24.0 * 3600.0

    @property
    def case_name(self) -> str:
        """根据关键工况参数生成输出文件夹名称。"""

        return f"case_H{self.H:g}_Q{self.Q:g}_Tin{self.Tin:g}"
