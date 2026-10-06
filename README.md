# RacingLine

卡丁车赛车线与圈速优化网页：基于 Fastest-lap 的 kart-6dof 模型，提供南京引力聚宝山与官方 Vendrell 赛道、200cc / 270cc 车辆参数、实验对比和累计时间 delta。

本文依次介绍安装、使用、模型与数据来源。车辆建模详解见 [卡丁车动力学与圈速优化模型](docs/kart-model.md)，实现细节见 [实现说明](docs/implementation.md)，历史设计记录见 [设计笔记](docs/design-notes.md)。

## 安装与启动

已在 macOS Apple Silicon 上验证，需要 Python 3.11 以上、Git、C/C++ 编译器和 gfortran。首次构建会下载并编译原生依赖，可能需要数分钟。

```sh
brew install gcc
./tools/setup.sh
./tools/start.sh
```

打开 http://127.0.0.1:8765 。更换端口可运行 `./tools/start.sh 8766`。运行数据保存到 `runs/`，不进入 Git。原生依赖按 [固定提交](docs/upstream-versions.json) 下载到 `upstream/`；构建脚本应用发动机和迭代导出补丁。Linux 构建尚未验证。

## 使用

选择赛道和车辆，调整功率、车重、驾驶员体重、车宽、传动比、效率、限转与离合器参数，再启动求解。南京赛道默认 500 点。完成后可选择相同几何的实验作为基准，查看赛车线、速度、转速、功率、加速度以及累计时间 delta；负 delta 表示当前实验更快。

求解中可点击“暂停求解”，继续时保留原生优化器状态。启用“记录逐轮赛车线”后，主赛道图可切换到逐轮静态轨迹，用滑块查看任意已记录迭代；该模式没有车辆标记与运动动画。中间迭代尚未满足约束，不能当作可执行赛车线。记录关闭时只保存日志与最终解，减少写盘开销。

预设 200cc 为 4.8 kW，270cc 为 6.3 kW，车重 100 kg、驾驶员 70 kg。两套预设共用一条基础扭矩曲线，传动比分别按实车约 60 / 66 km/h 观察校准，完整核对结果见 [速度校准](docs/speed-calibration.md)。

## 模型与赛道

车辆使用六自由度车身、前轴转向与自由滚动、无差速器刚性后轴和四轮 Pacejka 非线性轮胎模型；根据滑移与轮胎载荷计算驱动、制动和转弯力。驾驶员与车辆以合并质量表示，重心、惯量、车架刚度和轮胎参数仍主要沿用上游 Lot 2016 基线。

赛车线通过空间坐标下的最短圈速最优控制求解：同时优化全圈位置、速度、姿态、后轴转速和控制，CppAD 提供自动微分，Ipopt 求解非线性规划。默认 500 点网格，控制导数转录每点 16 个变量。车宽通过道路内缩约束车辆中心，不是完整旋转车身碰撞模型。详细公式、参数来源及当前近似见 [建模说明](docs/kart-model.md)。

动力模型采用统一基础扭矩曲线（Honda GX200 官方图表的近似读数），随转速计算扭矩，叠加固定齿比、传动效率、平滑限转和离合器滑移近似；不是恒功率模型，也尚未描述发动机转动惯量。200cc / 270cc 只提供 4.8 / 6.3 kW 等参考参数；输入其他功率后整条基础曲线等比例缩放，不受 Honda 原厂额定功率限制。调参时建议先确认实车齿数、后轮滚动半径和限转，再校准效率及离合器。

南京赛道由用户提供图片描绘并标定，参考长度约 618.55 m。道路边界包含识别出的路肩，排除轮胎墙与维修区；车宽的一半和安全余量从道路两侧收缩，约束整车空间。弯道速度同时受几何、轮胎与动力模型影响。图像比例和边界为估计值，尚待现场尺寸与速度数据复核。

第三方原始地图图片、卫星截图和 Honda PDF 不随仓库分发；仓库包含求解所需的数值几何及近似扭矩读数。没有原图也能运行预置赛道与结果展示。可将自有或已获授权的图片放入 `赛道图片和卫星图对照/赛道图.jpg` 和 `卫星图对照.png`，启用原图叠加与标定工具。

## 开发与引用

```sh
.venv/bin/python -m unittest discover -s tests -v
node --check web/app.js
```

`web/` 是无框架前端，`tools/server.py` 提供本地 HTTP API，`src/solve.py` 调用原生求解器，`vehicles/` 和 `tracks/` 保存配置，`patches/` 保存发动机补丁。贡献方式见 [CONTRIBUTING](CONTRIBUTING.md)，许可证与第三方来源见 [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md)。引用项目可使用 [CITATION.cff](CITATION.cff)。

主要参考：

- [Fastest-lap](https://github.com/juanmanzanero/fastest-lap)，Juan Manzanero，MIT。
- Lot, R. & Dal Bianco, N. (2016). *Lap time optimisation of a racing go-kart*. Vehicle System Dynamics, 54(2), 210–230. [DOI](https://doi.org/10.1080/00423114.2015.1125514)。
- Honda [GX200 技术参数与曲线](https://www.honda-engines-eu.com/files/files/technical-sheet-gx200-v23.pdf)、[GX270 技术参数与曲线](https://www.honda-engines-eu.com/files/files/technical-sheet-gx270-v23.pdf)。
- [Ipopt TNLP 回调接口](https://coin-or.github.io/Ipopt/classIpopt_1_1TNLP.html)，用于读取实际中间迭代。

项目代码采用 MIT License。来源图片及上游依赖分别遵循各自授权，详见来源说明。
