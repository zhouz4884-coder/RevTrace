# Claim–Evidence Matrix：允许、讨论与禁止主张

所有“支持”均为本协议、实现及声明前提内。源码Git身份、公开归档commit和实验ID不同；见EVIDENCE_INDEX。原始大日志留8TB，公开包不是匿名提交材料。

| ID / 主张 | 方法、证据、反例 | 竞争方法与替代解释 | 裁定 / 论文位置 |
|---|---|---|---|
| C1 安全State Admission不单独保证当前可见进展连续 | R0旧18cells/3393转移；Fine77/61/77与Coarse2/2/15，各自发布分母279/98；事件文本/前沿/时钟 | rho改变分段与内容，不是延迟单因果；Barrier也有必要文字修订 | GO，问题定义；不叫所有生成服务必有回撤风暴 |
| C2 固定选择历史下交付变晚可增加快照覆盖回撤 | R1真实GPU18；0/.75/1.5s计算后hold；12/12配对canonical历史相同且回撤率增加；r1_v1及R1_audit | 人工干预总效应，包括后续队列/批机会；不能独立识别各中介份额 | 有条件GO，主实证洞察；不是自然发生率或细粒度必然更差 |
| C3 旧WAL本身不认证worker.text出处 | CPU text-only篡改4/4进入旧路径，Z/P不变；D1单元负控与全部新WAL/Render独立重算 | 可信Authority/Caller/依赖仍为前提，checksum不能证明上游字节来源 | GO，工程缺口及可信绑定义务；不声称新密码学/硬件attestation |
| C4 Property D将安装事实与消费字节、顺序、恢复关联 | runtime live_qwen/text_binding/certified_display及测试；本地FIFO真实线程、身份收据、重启3次 | 可靠FIFO/单owner/同χ/存储同步；非网络Exactly-once、浏览器绘制、ASR完整性 | GO，可执行契约/证明，必须伴随假设 |
| C5 同F同P + 完整因果链/冻结输入可保留whole provisional | continuity_proof及独立GPU记录BFS；24因子全部positive见证重算；CPU错根/断链/在途负控 | 不是FP16=FP32选择证明，不是新batch重跑数值等价；P不含数值KV等隐藏状态 | 有条件GO，机制保证；仍未认证、不可写canonical |
| C6 分支与view联合提供收益，单杠杆不等价 | R2 24真实cells，每rho12完整canonical histories相同；Fine67/61/77→0/0/0，配对P99−43.94%，xRT比.9952；单view15.687s、单chain回撤93/77/77 | 单view隐藏/等待、单chain仍全量覆盖；c16未过SLO；文字修订非零 | GO，主机制交互；不是普遍零回撤/新吞吐headline |
| C7 RevTrace排他优于最强常规异步 | R2_strong_async6 + R4_strict54，Safe Async获同样规则、历史相同，连续性/性能相近，部分点更快 | 常规组件能实现规则；独立策略仍共享executor/WAL/Renderer，非完全独立系统复现 | **NO-GO该主张**；正文正面报告等价、重新界定贡献 |
| C8 比正确LA更适合有认证祖先的连续view | 修复全词LocalAgreement2/3、保持确认prefix，不空白；同protected engine；离线selected-text可见性 | 无词音对齐的frontier是保守下界，不能借此宣称原生LA未达SLO；非native系统复现 | 仅受控适配比较，讨论互补性；不主张发明显式稳定化 |
| C9 真实有限负载下有可行双SLO点 | scout10，冻结选点；strict54+transfer6，独立语音c8sync/c4stagger，3repeat；联合两点均3/3过2s/8s | 每点8/4新源，非全部16；均匀错峰非Poisson；Fine-B c8仅2/3；含未完成的共同frontier指标 | GO，所测工作点；不声称最大稳态容量或全部配置通过 |
| C10 真实消费历史可传播上下文故障 | Whisper16新说话人，192GPUcalls，实际decoder首前缀hook；16/16有效，14/16目标改变，其中9/14未来改变；same-input repeats全同 | 人工跨speaker替换、三段固定态操作器；共享音频池非额外独立数据集；R2未跨家族部署 | GO作为受控跨家族失效证据，不作自然发生率/服务性能 |
| C11 intended raw input相同不保证processed input相同 | R6 4context×3layouts×2，chinese05 523/524，CPU实际processor重放一致，生成Z/P跨layout全同 | 小样本输出未受损，padding/effective input/浮点/GPU SDC须区分 | GO边界，禁止宣称已发现自然GPU错误或普遍质量损害 |
| C12 持久安装事实可恢复到真正认证消费 | 真实SIGKILL3次，均2恢复快照被新consumer观察，0重复准入，ledger与31s可见RTO分列 | 非断电、磁盘损坏、网络ACK持久化、无界流量；重放剩余输入从F开始 | GO依赖假设的恢复证据；不把23–64ms账本写成服务RTO |
| C13 可安全拼接认证字符串后缀 | 无可靠token–audio边界；LCP/latest-frontier/blind-append CPU冲突负控；未改Z/P | 即使文字相似也可能不同ancestor，或重写认证prefix | **NO-GO**，只保留two-lane整体未认证view |
| C14 V2可凭本轮启动或旧V0/V1已翻盘 | 旧C2 0/98、C3 0–1/98及时且一致；全成本验证NO-GO原样保留 | 本轮连续性不是廉价严格选择认证，不改变selector门槛 | **NO-GO**；没有V2/新KV fallback |

## 证据导航

- R0：`R0_MECHANISM_AUDIT.md`、`TEXT_BINDING_GAP.md`，有界证据 `R0/`；真实旧文件逐hash复核另见 `PRIOR_FREEZE_RECHECK.json`。
- R1：`R1_CAUSAL_FINDING.md`，有界证据 `R1_audit/`；`source_r1.tar.gz`。
- R2：`PROPERTY_D_PROOF_AND_ASSUMPTIONS.md`、`R2_MATCHED_FINDING.md`，`independent/SERVICE_CELLS.csv`、`independent/DUAL_DEADLINE_GRID.csv`及recovery。
- R3/R4：`tables/CAPACITY_AND_STRONG_CONTROLS.csv` 与全部逐run、逐source、共同frontier/selected-text表；R3/R4共享实际run不重复计数。
- R5/R6：`FINAL_STUDIES_INDEPENDENT_AUDIT.json`、`R5_whisper/`、`R6_realization/`；实际tools_v5源码，不把UNRUN旧bundle当执行身份。

完整数据路径以原始索引为准；表名/文件存在与hash通过不是机制有效性的证明。各阶段独立复算不调用生产scheduler，部分certificate/WAL parser共享实现这一层复用也明确保留。
