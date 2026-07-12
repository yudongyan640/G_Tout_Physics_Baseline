# OGS 参数映射设计

## 目标

只读取 `E:\newdesktop\PINN\OGS_data\baseline\DBHE.prj` 和其关联的
`DBHE.gml`，将 OGS 中定义的几何、材料和地温参数转换为纯物理 baseline
配置。禁止读取 `.vtu`、`.pvd` 及任何 OGS 温度场结果。

## 模块边界

- `ogs_parameter_extractor.py`：只负责 XML 解析和 SI 单位原始参数归档，写入
  `outputs/ogs_raw_parameters.json`。
- `borehole_resistance_calculator.py`：计算岩土到环空流体路径的
  `R_borehole`、`U_wall`，只包含环空侧对流、外管壁导热和回填材料导热。
- `short_circuit_resistance_calculator.py`：计算中心管流体到环空流体路径的
  `R_short_circuit`、`U_pa`，只包含中心管保温层导热和中心管内外对流项。
- `parameter_mapping.py`：把原始参数及两类热阻映射为 baseline 字段，写入
  `outputs/baseline_physical_parameters.json`。
- `config.py`：当 `use_ogs_parameters=True` 时，从映射 JSON 覆盖默认物理参数；
  PDE/ODE 求解器接口和离散方法保持不变。
- `check_ogs_mapping.py`：报告原始/映射参数、SI 单位、缺失项和合理性检查。

## 几何与物理映射

OGS `DBHE.prj` 的 borehole 直径给出 `Rb`；外管内径和壁厚给出环空外半径、
外管外半径；中心管内径和壁厚给出中心管内/外半径。baseline 新增可选
`annulus_outer_radius`，使环空外边界使用外管内半径，而非误用 `Rb`。

`R_borehole` 的径向串联路径为：

`R_conv(annulus -> outer-pipe-inner-wall) + R_outer_pipe + R_grout`。

岩土近井导热不再额外串入常数热阻，因为现有 `rock_solver_1d.py` 已显式求解
从井壁向外的瞬态岩土导热；重复加入会双重计算岩土热阻。

`R_short_circuit` 的路径为：

`R_conv(center fluid -> inner-pipe-inner-wall) + R_insulation + R_conv(inner-pipe-outer-wall -> annulus)`。

对流项使用既有 `heat_transfer.py` 的流动与 Dittus--Boelter 关联式计算，保持
baseline 的传热关联式一致。

## 不可自动获得的信息

DBHE 文件没有为岩土外侧或底部定义独立温度边界；映射文件将它们标记为
`null` 并在检查报告中明确说明。baseline 的 `Rout`、数值网格和运行时长仍沿用
现有默认值，除非 OGS 文件显式给出对应参数。

## 验证

单元测试覆盖 XML 解析、热阻划分、映射文件和配置加载。随后运行
`check_ogs_mapping.py`，最后按用户授权运行一次 `run_single_case.py`；不运行批量工况。
