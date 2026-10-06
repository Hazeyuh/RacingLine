# 第三方来源与授权

RacingLine 自有代码采用 MIT。Fastest-lap 与 lion 为 Juan Manzanero 的 MIT 项目，版权 Copyright (c) 2021 Juan Manzanero；完整上游许可证下载到 `upstream/fastest-lap/LICENSE` 及依赖目录。原生库依赖 Ipopt、CppAD、MUMPS、LAPACK、TinyXML、loggercpp 等，版本记录在 `docs/upstream-versions.json`，各自许可证以下载源码内的 LICENSE/COPYING 为准。本仓库不分发编译后的依赖或上游源码。

Honda GX200/GX270 扭矩数据是官方技术图的人工近似读数，来源 URL 记录在 `vehicles/engine-curves.json`，拟合与缩放均为本项目处理。Honda 原始 PDF、商标和图片不属于本项目 MIT 授权范围，也不随仓库分发。

南京引力赛道的数值几何由用户提供的图像标定、人工描绘和平滑生成，来源与处理记录见 `tracks/nanjing/source.json`、`boundary-trace.json` 和 `docs/nanjing.md`。它是未经场地方确认的估计，并不表示场地方参与或认可项目。原始赛道图和卫星截图不随仓库分发，也不属于本项目 MIT 授权范围。新增赛道数据需说明出处和可分发授权。

论文引用见 README 和 CITATION.cff。历史设计记录中提到的其他开源项目属于方法参考；如后续引入代码，应保留其具体许可证与版权信息。
