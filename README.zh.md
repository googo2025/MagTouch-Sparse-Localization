# 三点磁触觉定位论文伴随资料

[中文 PDF](paper/Sparse_Magnetic_Sensors_ZH.pdf) · [中文 Word](paper/Sparse_Magnetic_Sensors_ZH.docx) · [英文 PDF](paper/Sparse_Magnetic_Sensors_EN.pdf) · [英文 Word](paper/Sparse_Magnetic_Sensors_EN.docx)

固定 1500 轮、同一冻结五点 CSML 定位器。A 为五点输入与五点监督，B 为三点输入与五点监督，C 为三点输入与三点监督。A 与 B 量化减少输入的代价，B 与 C 检验遗漏点监督的影响。历史布局筛选用三点实测加两点重建。受控主对照的 A/B/C 均用五点全重建。

原五点资料：[CSML 定位器与冻结权重](https://github.com/googo2025/MagTouch-CSML/tree/02cd40217672b43e0860c9a902ea8b4f77f922ca)、[共享场磁重建](https://github.com/googo2025/magtouch-temporal-state-reconstruction/tree/ca291d4d5324ca4b0fd42658022761cd6cfb9602/methods/shared_field)、[装置与采集平台](https://github.com/googo2025/MagTouch-RA-3d-trajectory-recon/tree/acb12b054abb75be53636fc5f2b4496c61de149c)。

仓库包含两版论文与图、去标识的逐序列评分、布局指标、训练与开发抽样点、统计和重绘代码。运行方法见[仓库首页](README.md)，指标定义见[数据字典](docs/protocol.md)。资料包从保存评分复现论文结果。原始帧和九组训练权重仍在项目归档。

新增两组同序列轨迹图，比较五点实测与种子 101 的 A/B/C。图使用已保存的原始定位输出，选例规则、哈希和逐序列指标见[轨迹回执](data/trajectory_examples_receipt.json)。本次修正“接受且误差 ≤0.5 mm”的统计口径，B 为 85.26%。原始定位均误、P95、覆盖率和接触计数不受影响。

新版正文图 5–8 覆盖点阵触压、多向直线、圆形扫描、XYZ 联合运动。补充图给出同一 XYZ 序列的三维对照。全部沿用原定位资格掩码和冻结输出规则。选例、拒绝计数和原始输出校验见[动作与掩码回执](data/dynamic_trajectory_receipt.json)。
