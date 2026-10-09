# S00.1 元数据与来源核查

框架依据：§2.2（时间元数据不足）、§8.1（必须级增补项）。

## 结论摘要

| 核查项 | 结果 |
|---|---|
| 栅格文件数 | 11 |
| 含 TIFF 采集时间标签(306) | 0 |
| **能否恢复观测时间** | **否** |
| **能否恢复传感器** | **否** |
| **能否恢复反演流程** | **否** |

## 栅格：找回的元数据

| 文件 | EPSG | 尺寸 | 像元 | nodata | 描述标签(270) | 时间标签(306) | aux 统计 |
|---|---|---|---|---|---|---|---|
| DEM_30m_Final.tif | 32650 | 2966x1723 | 30.0000 | -9999.0 | — | — | 无 |
| LST_30m_Final new.tif | 32650 | 2874x1658 | 30.0000 | -9999.0 | — | — | 无 |
| NDVI_30m_Final.tif | 32650 | 3011x1784 | 30.0000 | -9999.0 | — | — | 有 |
| archi_30m_Final.tif | 32650 | 2874x1658 | 30.0000 | 0.0 | — | — | 无 |
| road_30m_Final.tif | 32650 | 2966x1723 | 30.0000 | -9999.0 | — | — | 无 |
| 0_论文data/DEM_shenzhen.tif | 32649 | 1205x776 | 30.0004 | -9999.0 | — | — | 无 |
| 0_论文data/LST_shenzhen.tif | 32649 | 1205x776 | 30.0004 | -9999.0 | — | — | 无 |
| 0_论文data/NVDI_shenzhen.tif | 32649 | 1205x776 | 30.0004 | -9999.0 | — | — | 有 |
| 0_论文data/Road_shenzhen.tif | 32649 | 1205x776 | 30.0004 | -9999.0 | — | — | 无 |
| 0_论文data/SVF_Shenzhen.tif | 32649 | 7230x4658 | 5.0000 | -9999.0 | — | — | 无 |
| 0_论文data/arch_shenzhen.tif | 32649 | 1205x776 | 30.0004 | 0.0 | — | — | 无 |

## 矢量：坐标系与要素数

| 文件 | 类型 | 要素数 | .prj | 字段数 |
|---|---|---|---|---|
| 2023年县级/2023年初县矢量.shp | Polygon | 2852 | ['GCS_WGS_1984'] | 29 |
| arch shp/深圳建筑.shp | Polygon | 745213 | ['WGS_1984_UTM_Zone_50N', 'GCS_WGS_1984'] | 2 |
| road/road 3d/road.shp | Polyline | 4223 | ['WGS_1984_UTM_Zone_49N', 'GCS_WGS_1984'] | 10 |
| road/road.shp | Polyline | 197834 | ['GCS_WGS_1984'] | 10 |
| road/road_new.shp | Polyline | 140029 | ['GCS_WGS_1984'] | 10 |
| szbuildings.shp | Polygon | 119808 | ['WGS_1984_UTM_Zone_49N', 'GCS_WGS_1984'] | 5 |
| 研究边界/Buildings_Fixed.shp | Polygon | 745213 | ['WGS_1984_UTM_Zone_49N', 'GCS_WGS_1984'] | 2 |
| 研究边界/buildings_utm.shp | Polygon | 0 | None | 2 |
| 研究边界/grid_utm.shp | Polygon | 32748 | ['WGS_1984_UTM_Zone_49N', 'GCS_WGS_1984'] | 12 |
| 研究边界/studyarea.shp | Polygon | 299 | ['GCS_WGS_1984'] | 9 |
| 研究边界/szbuildings_utm.shp | Polygon | 119808 | ['WGS_1984_UTM_Zone_49N', 'GCS_WGS_1984'] | 2 |
| 边界/广东省深圳市各社区.shp | Polygon | 668 | ['GCS_WGS_1984'] | 9 |
| 边界/粤港澳大湾区2023/yuegangao2023.shp | Polygon | 23 | ['GCS_WGS_1984'] | 20 |

## 文本类文件中的来源线索

- **arch shp/深圳建筑.qmd**（679 字符）命中关键词：['date']
- **road/road 3d/road.qmd**（681 字符）命中关键词：['date']
- **szbuildings.qmd**（2339 字符）命中关键词：['date', 'unit', 'units']
- **~$过程.docx**（36 字符）命中关键词：无
- **过程.docx**（48057 字符）命中关键词：['date', 'lst', 'time']
- **2023年县级/2023年初县矢量.shp.xml**（22382 字符）命中关键词：['date', 'time']
- **边界/粤港澳大湾区2023/yuegangao2023.shp.xml**（1290 字符）命中关键词：['date', 'time']

## 内嵌图片证据

- `过程.docx` → `stage00_data_audit/reports/evidence/过程__image1.png`（116783 字节，SHA256 ef7ccd98658889a2…）

人工复核：`过程.docx` 内嵌图为 QGIS 3.x「Vector creation — Create grid」对话框截图，
界面参数可直接读取，是网格生成流程的**一等证据**：

| 参数 | 界面取值 |
|---|---|
| Grid type | Rectangle (Polygon) |
| Grid extent | 794467.4184, 2485099.3175, 830617.9329, 2508389.4085 [EPSG:32649] |
| Horizontal spacing | 100.000000 meters |
| Vertical spacing | 100.000000 meters |
| Grid CRS | EPSG:32649 — WGS 84 / UTM zone 49N |

该 extent 与 `0_论文data/*_shenzhen.tif` 的栅格范围**完全一致**，说明网格并非由社区多边形生成，
而是先取研究区栅格外包框生成 100 m 全覆盖网格，再与社区边界相交得到 `grid_utm.shp` 的 32748 格。

## ArcGIS 处理谱系（.shp.xml）

- **2023年县级/2023年初县矢量.shp.xml**：创建于 20230102 19065500，共 106 条处理记录
    - 20221230 162751 — `CalculateField 2022年\2022县矢量 曾用名 "东宁县" VB #`
    - 20221230 164622 — `CalculateField 2022年\2022县矢量 曾用名 "吐鲁番市" VB #`
    - 20230102 184037 — `CalculateField 2023年\2023年初县矢量 year 2023 VB #`
- **边界/粤港澳大湾区2023/yuegangao2023.shp.xml**：创建于 20260102 21354400，共 5 条处理记录
    - 20221220 233027 — `CalculateField 2022年\2022市矢量 ENG_NAME [NAME_2] VB #`
    - 20221220 233035 — `CalculateField 2022年\2022市矢量 VAR_NAME [VAR_NAME2] VB #`
    - 20230102 184023 — `CalculateField 2023年\2023年初市矢量 year 2023 VB #`

注：谱系仅覆盖行政区划矢量（2023 年县级、粤港澳大湾区 2023），
**研究区自身数据（LST/NDVI/DEM/SVF/建筑/道路）无任何处理谱系**。

## 判定

档案中**不存在** LST 观测日期、传感器、过境时刻、反演算法与 QA 波段说明。
所有 GeoTIFF 只带投影与统计信息；`过程.docx` 仅记录选址与网格生成步骤。
据此，框架 §2.2「时间元数据不足」与 §8.1 的必须级增补项 **全部成立**：
在补入原始影像元数据之前，任何日间/夜间、季节、热恢复动态类分析都不得开展。
现有数据只能支撑**单一时相的空间分异**研究。