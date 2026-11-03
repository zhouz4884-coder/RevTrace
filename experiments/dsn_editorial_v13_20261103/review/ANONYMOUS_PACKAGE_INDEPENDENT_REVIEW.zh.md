# v13 匿名材料独立复核

原独立冷读保留的复现材料条件现已解除。最终两个匿名 ZIP 的实际成员、清单、原始来源绑定及本地已有冷构建/复现输出支持第 11 页复现段的现在时声明；没有发现未满足的稿件声明，也无需修改稿件或档案。

审阅 PDF 保持 SHA256 `1413182663224acb507c2c68080f4dc8d340b2d7dab47a678e2aea39aa941928`。对应声明位于 `sections/07_progress_discussion.tex:17–22`。

| 最终档案 | 实际大小 | 实际文件数 | SHA256 |
|---|---:|---:|---|
| `RevTrace_DSN2027_anonymous_source_v13.zip` | 150,895 B | 33 | `92bcb91fe7bea9af353c76b1afea7b50ad8afde8026dbce7d74e568802207cd0` |
| `RevTrace_DSN2027_anonymous_evidence_v13.zip` | 778,902 B | 173 | `09e3ae7be37b56fdc8ce4993f0a13fd767a7d62ec3f8d4adbb66afad610f7d5f` |

## 按稿件原句逐项核对

| 第 11 页声明 | 档案内实际内容与独立验证 |
|---|---|
| Source snapshots | Evidence 的 `source_snapshots/` 实际包含 6 个完整源码快照，共 103 个源码文件；其中 NN4f 为 59 个。逐一核对其 `SOURCE_IDENTITY.json` 中的文件集合、长度、SHA256 与完整 commit，全部匹配。还对照清单指向的本地原始冻结源文件重新计算哈希并比较内容；不是仅接受 `all_source_bytes_exact` 状态。 |
| Fixed model/data configurations | `configurations/cells/` 有完整 32 个配置；其 ID 集合与 `data/new8/ALL32_CELLS.csv` 完全相等。逐例核对策略、repeat、说话人、音频 ID/时长/哈希、NN4f 完整 commit 及原始 StreamCorrect commit。`SERVICE_PLAN_v1.json`、`STATISTICAL_PLAN_v1.json` 与模型资产字节门均实际存在。所有包装 JSON 与其原文件的差异经递归比较仅为声明过的位置前缀映射，数值和非路径身份未改变。 |
| Per-run identities | 32 行实际 run 摘要和 32 个固定 cell 配置共同保留 run/source/speaker/policy/repeat 身份、原始结果位置与源绑定。两策略各 16 次的 137.864125 audio-s、56.000/129.460 s credit、0/16 与 10/16 pass 均从打包的逐行记录重新求和验证；564 个原始 selected steps 也是逐行求和，未当作独立样本。 |
| Endpoint-checking scripts | `source_snapshots/original_endpoint_checker/` 含原始完整实际轨迹 checker，另有 `recorded_event_accounting/`、NN4f 的 `content_endpoints.py`、`resilience_metrics.py` 等。源清单与原文件逐字节匹配。README 正确说明完整 checker 需要未分发的原始输入及依赖；本次未把代码存在误报成原始端点已重新测量。 |
| Hash-bound figure inputs / figure programs | Evidence 内含可编辑 `figure_source/render.py`、5 个冻结输入、`reproduce_figures.py` 与清单绑定。全部 173 个 fresh-extraction 文件重新与最终 ZIP 对比相同；对既有 fresh-extract 复现产生的 5 个实际 PDF 逐页作 144-dpi 像素比较，均与冻结图完全相同。四幅正文图还与 source ZIP 内的 PDF 字节相等；第五幅 `source8_paired_effects` 被明确标为 artifact-only。 |
| Bounded summaries and raw-log hash indices | `data/new8/`、`data/ENDPOINTS.csv`、事件/成本摘要与两个原始输入索引均实际存在。完整哈希索引含 420 项，raw-cell 输入索引含 419 项；对每项长度与 SHA256 格式作检查，并逐项确认 419 个 raw-cell 输入的路径、长度和哈希与完整索引相同。这里交付的是有界记录与索引，不是完整原始日志。 |
| Weights and full journals are separate | Evidence README 的 “Materials not included” 明确排除模型权重、录音、原始 StreamCorrect 依赖 checkout、环境缓存及完整原始 journals；MANIFEST 同样将 weights/full journals 标为 false。实际 173 个成员不含权重、录音、WAL 或 JSONL 原始日志文件。README 明确列出完整服务/checker 重跑的外部输入条件，并明确不声称完整一键服务复现。与稿件的有限范围一致。 |

## 未仅依赖状态字段的核查

两个 ZIP 均做了完整 CRC 读取、成员唯一性/安全路径检查及清单文件集合比较。Source 清单的 32 个输入、Evidence 清单的 172 个输入逐个重算长度与 SHA256；清单自身由各 ZIP 的外层 SHA256 固定。Source provenance 还正确绑定当前 PDF 和 companion ZIP。Evidence 的 171 个有原始来源的条目中，109 项逐字节相同，58 项仅 JSON 位置映射，4 项仅文本位置映射；另 1 项是新的包装 README。

Source ZIP 的全部 TeX/BibTeX/图引用均可在包内解析。将已有 `paper_qa/cold_manuscript/` 的全部 32 个编译输入与 ZIP 字节重新比较后，再直接渲染其实际冷构建 PDF 与交付 PDF 的全部 12 页，144 dpi 下逐像素一致。PDF 文件本身的 SHA 因构建元数据不同而不同，没有把它误称为二进制相同。

统计也用独立计算再次核对：按说话人配对且保留其两次 timing repeat，固定 `random.Random(20261102)`、20,000 次重采样，得到 53.2843479041 pp，95% CI [44.7693151645, 59.6175816565]；与冻结报告及正文四舍五入值一致。能量归一化与逐策略 pass 总数同时匹配。

本次没有重新运行模型、原始端点、测试、TeX 或绘图程序；核查的是最终包字节、原始冻结来源、有界统计，以及已完成冷构建/绘图产生的真实输出。未修改稿件、图、两个档案或旧实验。原 `INDEPENDENT_COLD_READ.zh.md/.json` 保持原字节不变；本报告仅解除其中的最终材料交付条件。

结论：`PASS_ANONYMOUS_PACKAGE_PRESENT_TENSE_REPRODUCIBILITY_CONDITION_RESOLVED`。未满足声明：无。最小修复项：无。
