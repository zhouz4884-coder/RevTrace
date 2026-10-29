# 三臂真实服务 pilot 的独立决策：优先确认 full-call retention

2026-10-29。本地只读复核已取回的 `SERVICE_PILOT_RESULTS_v1`，实际 source `bdfa3b1307d267a5a4caf6484e1ad465c39a592e`；未修改 runtime，未远端读取/运行，未启动 GPU。86 个 bounded 文件、6,548,217 B 在本机重新核对后全部符合 collection receipt 的字节 SHA。独立重跑本地完整 CPU suite：118 controls PASS，1 个 Windows 完整 native 包 import 明确 skip；实际 Linux frozen CPU gate 为 118/118、0 skip。

## 1. 结论

**GO 预先冻结四个旧来源 × 两次 fresh process × {保守 two-full、full-spec two-full} 的 16 格确认；采用完整调用保留作为当前 RevTrace 原生应用的优选实现。现在不实现 stage join。**

理由是已经获得一条完整的实际链：旧出生的真实在途计算在实际父状态确认后继续服务；不匹配的完整起点被及时隔离；原 C/IDs/全部反馈状态和质量没有改变；同一实际 Consumer 获得更多满足原期限的进展。它优于保守执行的幅度足以值得确认，而当前 ready-only stage 不是最好的实现。该选择符合“找到最有效的组合做论文”，不要求某个预先偏好的代码分支必须胜出。

本点是开发 pilot、每臂一次。来源为原 source0、共 8.068 s offered 音频，不能写成统计确认或独立 holdout。

| 执行组合 | 原 D2/C8 信用 | 全 offered D99 | 全 offered C99 | C50 | 两卡 service energy |
|---|---:|---:|---:|---:|---:|
| 保守 two-full + 相同早显 | 3.000 s | 5.145 s | 5.399 s | 3.192 s | 4802.8 J |
| protected A ready-handoff | 6.500 s | 3.468 s | 3.731 s | 1.857 s | 5111.5 J |
| full-spec two-full | **8.000 s** | **2.552 s** | **2.836 s** | **1.466 s** | **4420.8 J** |

三个臂均无 missing D/C，17 个完整 Canon 状态、selected C 和 returned IDs 全部通过原任务保真；最终均 2/23 character edits。所有 C8 都命中。full-spec 相对保守执行为 10 个 offered frontier miss→hit、6 个同 hit、1 个同 miss，新增 5.0 s 信用；能耗约低 8.0%。**全 D99 仍未达到 2 s**：最后 EOS 间隔 0.068 s 失败，不能删除它或把 8/8.068 写成全 SLO 成功。

## 2. 实际 C1 路径，不只是调度器计数

独立把 `FULLSPEC_LEDGER.json` 的 promotion、`DISPATCHES.json`、`native_jobs.jsonl`、实际 `canonical_install` 事件及完整 history 连接：

- 10/10 promotion 的完整 start cut 等于后来确认的实际父 cut，原 birth Canon/job 保持。
- 10/10 都满足 `worker_job_begin < parent Canon install < worker_job_end`，所以确实保留了正在执行的工作，不是结果已经完成但 controller 尚未读队列的伪 in-flight。确认时残余实际 worker 时间为 0.235–1.076 s。
- 其中 **3 个被保留 job 自己的 identity 预测 end 与真实原 C/U end 不同**：`j000010` 72000→80000、`j000014` 96000→104000、`j000017` 112000→120000。它们仍合法完成并进入精确原 Canon 历史。这是在实际服务中将“当前完整输入合法”与“预测未来 end 正确”分开的正例，不能被只看预测版本或预测 end 的逻辑替代。
- 4 个 C-entry skip 均有实际完整 start 的同-F Canon 否定/所属任务许可，记录 `learned_C_executed=False`、`C_U_completed=False`、`feedback_cut_emitted=False`，没有 `end` cut。它们不能获得 certified 权限。
- 本次实际 completed-full buffer reuse 为 **0**；其支持来自 CPU 控制，不要写成 pilot 已观察到的 completed-result 服务收益。future-input 收敛控件同样是 CPU evidence，不混成这条来源的自然发生率。

因此，这次正面贡献不是“多装一份模型就快”：保守臂也有两份同样的完整模型、相同原 ASR/C/U、相同精度与真实 neural-ready。差别在于允许在合法临时反馈输入上提前执行，并在根推进后按完整输入继续使用原在途计算；同时禁止错误完整起点的状态提交。两份 full 当然带来流水并行，正是合法性/消费合同让这种并行能被有用且正确地兑现。

## 3. same S 的作用和实际边界

三个臂都调用同一实际 `StageConsumer`、同一完整 branch/cut 检查、同一 typed identity projection 与相同 Canon/Provisional 权限区分；不是 full-spec 多获一种显示或认证能力。Consumer 会检查当前 Canon hash 和逐步完整依赖链；canonical 发布前经过 fsync WAL，不能把早期 projection 或条件 full-C 完成冒充 certified 进展。

不过，独立逐行检查本点 50 条 full-spec Consumer 记录：34 条 Canon 视图、16 条 typed ASR projection；17 次 Canon 安装中，实际保留 ahead private view 的次数为 **0**。所以本点直接支持的是 **C1 在途计算保留，在相同 S 消费合同下带来服务收益**。它没有单独证明跨 Canon 的 S 留存发生，更没有重新证明 R×S 必要性。C2 的交互与单边保留可能恶化显示的证据仍来自主核心实验。这种分工比把每项 native 加速都叫“R×S 协同”更有说服力。

本地内容侧复核也保留了区别：full-spec 8 s 原信用中 6.5 s 首见事件是 strict append，1.5 s 是 unchanged；三臂均 17 次文字变化、4 个 LCP erased code-point occurrences。不能把所有音频 frontier 信用称作新增文本。

额外只读检查将每个及时首见 Consumer **完整文本**，与该行实际 `visible_frontier` 的完整 Canon 文本比较，不截更长文本来伪装同 F：保守为 3.0 s agree/0 different，stage 为 5.5/1.0，full-spec 为 6.0/2.0，unknown 均 0。这是后验实际同视图-F 文本支持，不是在线认证或 ground truth，也没有替换原 D2/C8。它说明可支持文本的增量仍为 +3.0 s，但不能说新增的所有 5.0 s 首见文本都已等于未来 Canon。确认轮宜冻结同样的独立内容检查，主指标保持原样。

## 4. 强控制与公平性判断

此次 `two_full_spec_early` 本身是本工作新组装的实现/控制，不是外部已有作者系统。它已包含合法临时输入、真实 full 推理、实际 start/epoch 后验确认、in-flight promotion、可完成结果缓冲、同 whole-state Consumer 和明确无用 C 的退出。**若它胜出，应作为 RevTrace 的实现选择报告，不能一边把它叫我们自己的组合，一边又把它当外部先例来否定本工作的创新。**

同时，保守 two-full 是本工作对原作者推理程序的保守执行控制；原 ASR/C/U 源码/模型保真不等于原作者已部署的完整实时框架。正文应称“controlled native adaptation using the original recognizer/corrector/update”，避免把本结果写成未经复现的完整 published-system 端到端比较。

现有 controller 对三臂使用相同 offered cadence、all-offered 含 EOS、同两卡资源与早显端点。full-spec 的已知无用 C-entry 退出只由实际同-F **完整 job start**、覆盖或 epoch 见证触发。更早祖先失配不会被当成 future complete input 永不可能收敛，未知父输入继续；这避免了人为削弱强控制。按实际 start 相等后直接 promote/commit、不重复 full fallback，也避免了人为浪费第二卡。

单会话的保守臂只能在已确认反馈上执行，所以第二卡不提供预测并行，这个差异是其明示策略，不应包装成系统硬件上限。full-spec 比较解释的是作者组合将两卡资源变成合法反馈流水的机会。后续容量边界仍须报告；原双会话下 full-spec/两 full 总资源和调度机会也可能不同，不能外推本点到所有并发负载。

## 5. 为什么现在不加 stage join

预 pilot 假设实际被触发：4 次完整 key/epoch 匹配的 producer A 尚未 ready 时，Authority 又 full fallback；producer packet 比重复 Authority A 分别早 0.278、0.360、0.309、0.122 s。**这是真实 stage 内部修复机会**，不能说 ready-only 已穷尽一切合法 in-flight retention。

但研究目标不是让 stage 追平已经更好的我们自己 full-call 实现。当前 stage 对 full-spec 信用少 1.5 s、C50 慢 0.391 s、service energy 高约 15.6%。actual 原 ASR 执行量为：stage 30 次完整 ASR（consume 不重复计包内 A）；full-spec 16 次完成 ASR加4次被正确退出的 ASR prefix；保守 16 次。join 即使消掉这 4 次重复 A，也尚未展示相对 full-spec 的额外端到端价值，完整时序变化又不能用静态相加推成收益。

因此保留预结果 join 合同与这 4 个实证触发点，不实现新分支。只有正式确认反而揭示 full-call 因资源/容量/内存而无法兑现目标、stage 少一份 C 的结构优势有具体部署价值时，才重新评估。没有这样的新证据，就把时间放在确认当前最佳完整组合和论文主线。

## 6. 下一轮 16 格与停止条件

支持 root 的有限方案：四个旧来源全部纳入，两个 fresh process repeats，每个配对均为 full-spec 与保守 two-full；两重复交换 primary GPU 角色，配对内顺序随机且预先冻结。保持 source `bdfa` 和完整共同消费语义；如果不改 runtime，就不因增加配置重跑原 69 神经等价。对每格完整配置/source/env/run/raw/summary/gate、全部实际 Canon/C/IDs/fidelity、能耗和 offered Consumer 记录照常保留。

重点输出不只是均值：每来源配对信用/可信 C 延迟方向、每个原期限 miss→hit/反向、原 all-offered D99/C99（包括 EOS）、内容支持与 churn、真实 in-flight/取消 witness、两卡能耗及进程时序重复。四个旧来源不是独立 holdout，不把约 8 s 的来源当独立的 17 次统计样本；不把 8 组成对进程重跑当 8 个新来源。

若多数来源没有收益、收益仅来自一个 warm/role/排队偶然点或有质量/反馈不等，就冻结边界或 NO-GO，不通过新来源/新 deadline/新 phase 调参续命。若来源方向和 fresh-process 稳定性支持当前效应，再按最终冻结实现以 metadata/固定 seed/speaker-disjoint 选少量新来源作独立确认；不得先看模型响应或兼容率。双会话容量只做有解释价值的固定边界，避免横向扩网格。

## 7. 对 DSN 论证的取舍

建议将原生应用的主叙事调整为：**反馈会改变临时计算的授权根；完整输入支持的仍合法进展可跨根继续，未支持的后继被隔离；同一 trusted update 与消费合同兑现为更多及时合法服务。** 输入合法性的条件/必要交互由 C1/C2 主实验支撑，native 的 10 个实际在途保留、3 个 end-prediction 不同仍合法完成和4个错 start 退出给出外部真实反馈应用的具体实现证据。

stage packet、原 C/U AST suffix、65 组神经等价与 13 个 end-different 点支持另一种更细粒度实现及边界；不必硬塞成额外主贡献，更不应因它未胜 full-spec 而宣布机制结束。等 16 格确认后再选择最少充分图表：核心 R×S 交互 + native 配对服务进展/可信延迟 + 一个实际授权时序见证即可；保留 stage 的负相对结果作为执行粒度选择依据，避免把所有实验摞进主文。
