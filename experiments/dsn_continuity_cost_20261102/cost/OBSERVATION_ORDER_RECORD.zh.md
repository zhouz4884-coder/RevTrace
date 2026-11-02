# COST_NN_V1：已冻结观测开关次序的准确记录

日期2026-11-02。源外解释记录；不修改已冻结observer3cf、driverb164、计划、NN16原数据或分析d727。

## 已执行的次序

正式主聚合 `../history/RESULTS_C_COST_AGGREGATE_V1/SUMMARY.json` 的 `NN_cells` 保留实际计划/执行列表：

| source / policy | repeat0次序 | repeat1次序 | primary GPU |
|---|---|---|---|
| S0908 / Conservative | off→on | off→on | 0→1 |
| S0908 / Full-call | on→off | on→off | 0→1 |
| S0916 / Conservative | off→on | off→on | 0→1 |
| S0916 / Full-call | on→off | on→off | 0→1 |

repeat0的blocks为S0908/Conservative、S0908/Full-call、S0916/Conservative、S0916/Full-call；repeat1完全反转这四个blocks。八对全保留。

## 为什么没有实现policy内AB/BA

原已冻结 `source_dev/build_plan.py` 同时使用 `blocks.reverse()` 和 `(block+repeat)%2` 选择mode顺序。原block索引b在repeat1变为3−b，再加repeat1得到4−b，与b的奇偶性相同，因此每个policy/source的mode顺序与repeat0一致。

原方案叙述中“repeat交换GPU并反转off/on顺序”不能作为已完成的counterbalance陈述。实际完成了GPU交换与block反转；没有完成同policy/source的mode反转。这个事实是设计混杂，不是原任务、协议安全性或计时导出失败。原代码、计划、执行GATE和全部数据仍原样保留，不重新归属执行commit。

## 对结果的影响与处理

- 不能将on−off方向解读为一个已隔离period/order的因果开销估计；尤其Full-call四对都on先。
- 不把“7/8 C99下降”称为观测器带来的系统优化，也不把缺少下降称为“零开销”。
- 独立审计仍验证原选定任务、质量、Consumer、实际物理能耗及嵌套计时；八个计时开启运行的实际coarse函数足迹仍可按其原scope使用。
- 正文仅采用实测coarse footprint，不主张因果observer tax，因此本轮不为这个缺口追加16格NN。若将来需要估计观测的因果影响，须新ID、新冻结计划，按每个policy/source明确AB/BA并保留所有结果；不能事后调整本轮次序。

本记录由已取回本地摘要与冻结计划逻辑解释产生，无新模型、远端读取或raw重算。
