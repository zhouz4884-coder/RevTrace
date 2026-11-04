# v14 论证增量与证据绑定

实验主张继续使用v13的完整[主张—证据表](../dsn_editorial_v13_20261103/CLAIM_EVIDENCE.md)及[31项引文映射](../dsn_editorial_v13_20261103/review/CITATION_MAPPING.json)。本轮没有新增科学测量或引用。

| 增量 | 实际证据 | 能支持的表述 |
|---|---|---|
| 首达与当前可用性区别 | 原`ACTUAL_INTERVAL_COMPARISON.json`与原四图；原Consumer应用事件 | (a)区间首达满足D2/C8，仍缺失2.176s；(b)D2晚27.4ms但保留所示覆盖。 |
| 输入资格、原选择、视图支持的对象表 | 冻结NN4f完整输入、原调用/事实与实际Consumer记录；原命题与原core对照 | 各种用途有不同证据；不能将EL/SUP与R/S动作开关等同。 |
| 早完成缓冲与合法append顺序 | `review/EXECUTION_PROOF_AUDIT.*`逐行绑定fullspec_policy、resilience_policy、FactStore及Owner串行事件循环 | 未知父输入结果先缓冲，实际父状态确认后才append；不引入无父投影边。 |
| R/S设置语义 | 同一审计中的core live_qwen、certified_display、kernel_runtime、composed_kernel路径 | 共同安全门保留；动作关闭时保留专用函数可能短路，不能称完全相同路径。 |
| 三项适配义务 | 原§II完整状态定义、§III原选择绑定、§IV通道/持久性与Consumer执行 | 是已有合同的检查面，不是仅靠哈希即可自动迁移到任意Agent。 |
| 可读性和排版 | 最终PDF实际12页、独立冷读、顶端对齐表格、最终尺寸灰度渲染 | 表格和段落可独立理解；不以源SVG字号替代实际版面检查。 |
| 新源码包复现范围 | `paper_qa/FINAL_v2/SUMMARY.json`；v14源码ZIP；原身份v13证据ZIP | 33文件源码包冷编译12页像素一致；既有证据包字节未变，不新增原始GPU验证身份。 |

固定科学结果：新8来源/32运行/564选定转移；覆盖40.6%→93.9%；53.3pp、说话人配对95%CI[44.8,59.6]；0/16→10/16。旧native主结果段逐字节未修改，能耗、质量与offered/EOS口径保持冻结。
