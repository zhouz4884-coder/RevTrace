# 真实完整2s非EOS病例：已经及时显示的内容在D2读点消失

[论文PDF](RESULTS_v2/timely_full_interval_case.pdf) · [可编辑SVG](RESULTS_v2/timely_full_interval_case.svg) · [完整PDF页预览](RESULTS_v2/timely_full_interval_case_PDF_PAGE.png) · [实际快照](RESULTS_v2/ACTUAL_SNAPSHOTS.json) · [完整证明与数值](RESULTS_v2/SUMMARY.json)

这是附件启发的**post-hoc单臂机制说明**，复用原c16-staggered r0、R1S0、sid7/source3570-5694-0003已经取回的全部Consumer/events/worker记录。没有新remote读取、GPU或模型调用；原36/48分母、新c12强gate阴性和旧19.025s paired/EOS图均不改变。

所选offered interval是12–14s完整2s段，14s严格早于19.025s的EOS。图以其原始ready时刻为t0：

| 实际事件 | 相对原ready时间 | visible F | certified F | 文字LCP变化 |
|---|---:|---:|---:|---|
| 首次cover | 1.443905769s | 14s | 10s | 新增37 raw codepoints（31非空白），擦除1旧末尾标点 |
| 兼容Canonical应用 | 1.543663285s | 12s | 12s | 撤去37字符，恢复1标点 |
| 原D2读点 | 2.000000000s | 12s | 12s | 已经见过的整段进展缺失 |
| 恢复 | 3.719605122s | 14s | 14s | 完整visible_text与首次cover逐字节相同 |

新suffix是“ a taboo or a larger conventionality.”。这是实际内容变化，不是只有F推进；但没有将字符分配给音频或推断token/audio对齐。首次D2/C8信用仍然成立，随后缺口持续2.175941837s；D2读点缺口是另外的连续性观察，不能拿它改写原first-credit指标。

独立C1重算使用实际complete结果和实际执行prompt：Private proposal-7-201的输入P逐token等于F12时Authority authority-7-182选中的P，得到exact_selected_root。没有依赖retention flag或仅靠文字一致。后来F14的文字相同只是一项后验支持，不给首次provisional view提前认证。

Joint在同F12没有ahead view，所以图中不画Joint反事实或把两条不同交错对齐。这里解释一个具体事件，不估计发生率，也不替换12点未找到强见证的事实。

冻结配置CONFIG_v1.json，SHA4208999074d5f9196a0359e814e74dc2a86421a38abca4243afc9edbb4969ffb。首次源ac0083a2c99f1c178b0480756f1a67ea9a9f98ca保留；最终源8970f923c2ef8ca066eb963e7a1ba8664829159e只移动说明文字以避开certified线，完整manifest及bundle均已保存并导入root。六个既有输入逐一核SHA，包含原timely窗口，实际代码、环境、config、run record、gate、plotmanifest均在RESULTS_v2与source_v2中。

图为7.15×2.65in，字号≥8pt，嵌入字体，Type3=0，完整PDF页和所有标签已目视检查通过。
