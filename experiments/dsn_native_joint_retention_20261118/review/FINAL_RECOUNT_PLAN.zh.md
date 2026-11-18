# 完整80格独立重算计划

脚本：`review/final_recount.py`。它只使用Python标准库，位于冻结运行时、driver和audit源之外，不修改那些源、论文或原结果。当前仅进行了AST语法读取，尚未执行重算。

## 执行条件与命令

只有PILOT20_V1和CONFIRM60_V1的SUMMARY均为完整完成、分别20/60格且无技术失败时，才读取逐格结果。否则返回`NOT_READY_NO_FINAL_POINT_ESTIMATE`，不产生最终点估计文件。

完整镜像就绪后：

```text
python review/final_recount.py --out review/FINAL_RECOUNT_V1
```

默认镜像目录为`gpu_results/PILOT20_V1`、`gpu_results/CONFIRM60_V1`和`gpu_results/REFERENCE8_V3`。可用两次`--campaign`和一次`--reference`覆盖路径。输出目录必须事先不存在。

## 必需镜像

每个campaign：CONFIG、SUMMARY、GATE、RUN_RECORD；本地plans目录中的相应冻结PLAN与configs/<campaign>/<cell_id>.json。

每个cells/<cell_id>：CONFIG、SUMMARY、GATE、ORIGIN、SERVICE_END、EXTERNAL_FACTORIAL_AUDIT、JOB_ACCOUNTING、WORKER_TIMER_LEDGER、INDEPENDENT_VIEW_AUDIT、SAMPLED_ENERGY_OWNERSHIP；以及view_audit下SUMMARY、GATE、CANONICAL_SUPPORT_EVENTS、OBSERVED_LOSS_WINDOWS。

参照目录：REFERENCE_RECEIPT、GATE、SUMMARY、REFERENCE_DETAILS、GENESIS。

## 校验与输出

- 全部80个source×repeat×condition键唯一；8个speaker，5条件，各2次fresh重复；所有来源恰好等于NN11453433的已测参照银行。
- 每条件137.864125audio-s、282个offered frontier；逐前沿500ms/partial EOS权重、D2/C8判据、原线性P99和credit独立算术重算，所有失败/缺测留在分母。
- 所有原任务、原selected-trace、独立Consumer实际策略审计、worker终态守恒、完整worker计时、两板物理drain窗口和采样归属门通过；strict完整state/C/IDs参照相同，不合并旧NN4f/de0936数据。
- 四臂交互及R/S简单效应分别计算credit、各撤回类别、累计移除音频、全高水位面积、同根可避免面积及资源。Conservative作为同runtime第五锚点，分开报告Full和Ready相对它的实际差。
- 直接从逐格continuity恢复`gap_right_censored_windows`等字段，不依赖driver聚合中未纳入的别名。全高水位面积与同根分类面积对象和终止边界完整保留，不把后者冒充跨root完整G。
- 所有预定义credit对照做8来源固定配对的描述性符号枚举：两重复随来源一起翻转，零效应来源不丢弃，无非零/正向结果筛选，不解释为部署总体显著性。
- 输出SUMMARY、CONDITION_TOTALS、SOURCE_CONDITION_TOTALS、ALL80_CELLS、SOURCE_FACTORIAL_EFFECTS及中文报告。每个输入文件的SHA与重算脚本SHA写入结果。

该脚本是独立汇总与报告字段守恒检查。原始部署源/完整路径合法性由已经冻结并执行的独立audit门承担；没有重新运行模型或将不在镜像中的raw日志伪装为已重新验证。
