# v18原位小修与版本清理

本轮直接修改v18，不新增v19。修订前v18的逐文件身份保存在BASE_V18_MANIFEST；修订前PDF/源包还可从私有仓库既有提交`bd3d1593ebf3cca95d843759faae728174317e61`追溯。V15/V16/V17内容保持不变。

## 正文改动与依据

1. 将四臂信用、总撤回和可避免撤回并为Table III。相对Snapshot的coverage差为Compute-only +1.41pp、View-only −3.60pp、Joint +3.73pp；“唯一同时改善”限定在这四个因子臂，而不是整个实现空间。
2. 摘要、引言和评估统一报告total12→17，其中avoidable6→17，避免总数与子集计数并置造成误读。
3. 明确B为三个initial primary staggered cohort运行；同时报告四臂I与直接Joint−Compute：I18.530/6.205/17.555s，直接差2.790/10.180/3.640s。后续fresh时序重复的反向结果保留，负jitter仍有5次兼容ahead机会，不归因为零机会。
4. 区分两个语义不同的开关：core两个Consumer都允许检查后的Private首显，S控制canonical应用时保留已显示view；native canonical-only在固定日程上禁止Private首次发布。未把core的25.680s下降归因于未经隔离的锁、ACK或协议净开销。
5. 201.960与194.735s的信用账闭合为共同167.035s、各自额外34.925/27.700s。两个2s区间在首次及时后被撤回，仍保留一次first-credit；恢复没有再次计分。“Joint为0”限定为未撤掉其已经及时且仍兼容的进展，不表示全部原始区间在D2都已显示。
6. 290/278/12先标为shadow谓词比较，再与各保留策略56次真实model-active交接分开。保持“采样剖面上一致”的范围。
7. 恢复旧/新两runtime的聚合复现：相同八speaker、137.864125s、129.460s信用、10/16通过、20个D2miss含6个EOS。四个0.5-audio-s分类反向变化抵消，未宣称事件身份相同；0.5是音频权重，不是延迟或半个deadline。
8. 摘要与贡献2直接陈述selected-transition保证：每个所选转移为原程序允许，replay不新增原转移。不将它扩为每个可见预测都属于原程序转移，也不声称改变调度后必然得到唯一相同序列。
9. 保留正向Operating scope解释，区分实测机会/服务结果、合同下允许转移及受控故障注入。没有新增“密度足以预测收益”的主张。
10. 分开称225 protocol unit tests、35 named model checks和28 observer unit tests；96 trial–rule rows明确为24条实际trial日程×4种发布规则。

## 版面与源包

- 仍为v18；11页技术内容＋1页参考文献，147词摘要、34条已引用文献、4张原矢量图。新增四臂表，末页技术内容分栏排布。
- 修订保证、证据和参考引用没有新增来源；4张图及其测量输入字节不变。所有可达源与manifest/ZIP重新生成。
- 源包独立解压重编译，12页文字和72dpi raster均逐页一致。无新模型或科学实验。

## 清理范围

用户要求只保留v15–v18。主目录`Paper_DSN/revisions`及三个受管理工作副本均先解析绝对目标、验证直接子目录和无reparse point，再用PowerShell LiteralPath删除更早论文目录；共移除64个工作副本目录。主目录最终恰好保留四个指定版本。

实验目录、数据、模型、原始日志和科学证据包未删除；Git历史没有改写。公共仓库的旧论文目录在本次提交中删除。私有审稿仓库保留v15–v18论文及源包；v13 scientific companion是证据包，继续保留。

复核入口：`review/A_CREDIT_READPOINT_AND_REPLICATION_RECONCILIATION.zh.md`、`CLEANUP_PLAN.json`、`CLEANUP_RECEIPT.json`、`PROTECTED_V15_V17.json`、`FINAL_RELEASE_CHECK.json`、`COLD_BUILD_CHECK.json`及GitHub同步回执。
