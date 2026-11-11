# Pilot/reference执行前独立因果与来源审阅

2026-11-11，只读静态审阅；没有新CPU/GPU实验、模型调用、源码修改或CURRENT操作。本文不代替正式CPU控制、真实reference或GPU启动门。

## 最终审阅范围与结论

最终对象为实际runtime `de0936b2e30179d63aeef6e235cd1af685578c58` 的66文件、driver `f367c4e1068a9391a0e99d8537c94995a3388e13` 的20文件及已生成的metadata-only first4/first2/24格handoff。两份本地完整manifest逐大小/SHA核对、Git HEAD/clean检查均通过；已有正式CPU门分别225/56项、零fail/error/skip。本审阅只读取这些结果，没有重新执行它们。

**未发现当前代码中必须在GPU前修改的因果或来源缺陷。** 五主臂与出生版本辅助臂的干预边界、全局canonical-first RR、实际Owner ready定义、两次repeat反序/GPU交换、全offered和原EOS、新reference严格绑定、事前full4→first2派生与非筛选哨兵均一致。Root可继续真实新source reference的常规启动门；这不是宣称reference或24格服务已经运行/PASS。

审阅还覆盖GPU_PLAN_v2、GPU_EXPERIMENT_CONTRACT_v2、EXECUTION_ADDENDUM_v3、RESOURCE_LEDGER_AND_SENTINELS_v1、RESOURCE_COMPARISON_ADDENDUM_v4。过程先审过历史14ae/2fac候选，后追加实际v3/f367，旧候选没有改标签。合同v2 SHA `93c7e2c96b54bbac0bf5998e12f3bb7b4a22d41ea8a397bcddd86103ea99ae98`；addendum_v3 SHA `2fd0a319d3bcc5970b321efc391de5172c60b444aa48917b1c14fb640605cb32`。下文保留因果解释与实际新版核验细节。

## 因果对照的对象明确，未让AU/SUP随策略漂移

| 比较 | 实际改变 | 保持不变 | 能回答的问题 |
|---|---|---|---|
| Conservative vs Fullcall | 当前真实父输入派发 vs 条件完整输入提前派发与合法保留 | 两完整FP32 worker、原ASR/C/U、AU/SUP、同步durable-before-install、全部输入与EOS | 该负载下提前执行整体的服务/资源效果 |
| Ready-only vs Fullcall | 每次实际install时，尚无Owner验证完整receipt的调用被policy fence | 已完成且Owner-admitted原结果、真实父状态选择、SUP与物理lease | 已完成memoization是否足够，以及在飞合法工作保留的增量 |
| Dependency-versioned vs Fullcall | 已冻结祖先版本失配永久撤销后继；不因未来完整输入收敛恢复 | 直接兼容handover允许保留、原完整输入/AU/SUP守卫 | 更强version-DAG策略与完整输入资格的条件差异 |
| UIR vs Fullcall | 只禁止Owner下发合作式C入口skip hint | input/coverage分类仍运行；returned结果仍经原AU、SUP、durability和身份校验 | 已知无效/已覆盖计算提前停止的增量；不能据tie说输入验证冗余 |
| Safe-versioned auxiliary | 每次真实root install递增policy generation，严格出生版本fence | 不伪造session epoch/incarnation；SUP独立 | 简单出生版本失效控制；不冒充强dependency策略或外部Retire |

依据：runtime `retention_policy.process_c_entry_hints` 保留分类，只改变发送；`versioned_policy` 的policy-only fence与完整输入反证分开；所有提交继承 `ResilientFullSpecCoordinator._commit` 的实际父状态+同步durable hook，实际Consumer保持同一SUP路径。unsafe UseAll不出现在live exact arms中。

## Ready边界与时钟不能偷换

Ready-only保存的是**实际Reconciler.install之前，Owner已校验并接纳的完整原结果**。worker model_end或physical frame已到但Owner尚未处理，并不满足该定义。`complete_receipt_order` 与 `canonical_install_order` 使用同一串行policy执行序号；Owner出队另有序号，FramedReader收到时钟保留为channel_received_perf。其他ready bank快照和当前selected job自己的receipt分别记录，避免因当前job已从bank弹出而误报它没ready。

这些是政策定义不同导致的真实边界，不能在分析中悄悄改为“物理模型已结束”。同时必须保留发送、channel收到、Owner出队、验证和真正install各时钟；输出相同timestamp时仍按序号判定。新CPU合成Owner路径测试覆盖queued child在parent之前/之后处理两种情形，是有针对性的控制，尚不等于真实神经负载已出现复用机会。

## 新reference绑定具有两层严格守卫

driver `reference_binding` 检查actual runtime、generator实际commit、完整选样对象、每source全部500ms/EOS边界、start→end整状态链，以及所有原reference state内部source marker；只改外层标签不能通过。generator实际执行一次无步间restore的原连续引擎，再对每个冻结完整输入做两次原full-step，失败时追加same-input与original-prefix控制并保留，不能挑诊断输出替换原reference。

service配置固定 `require_reference=True`、`reference_kind='strict'`。runtime `resilience_trial` 只有在其 `resilience_metrics.reference_audit` 对完整start/end/C/IDs**无投影**通过后才出原task PASS，driver先要求此PASS，随后才调用a13支持层的外部审计。

a13 `audit_results.selected_trace` 仍有旧BDFA/current source-marker投影，它是额外交叉检查，不是新reference获权的唯一门；上述严格层在它之前。因此没有发现其允许旧4f/BDFA reference冒充新actual source的旁路。不能在最终报告中仅引用a13的投影PASS而省掉严格runtime结果。

旧warmup状态作为一次新模型实际执行的固定warmup输入、随后reset-to-genesis，与复用旧reference结果不同；准备器已把旧parameter layout标为inherited expected，仅新READY才是新实际观测。该区别应保留。

## 队列与统计的解释

24个pilot＝2个已用speaker×6臂×2 fresh；五主臂20格、辅助4格分开。r0种子只依赖冻结metadata，r1逐speaker精确反序并交换主GPU，整个r1 source顺序也反转。它平衡基本顺序/卡角色，不构成所有非线性漂移都被消除的保证，也不提供新的speaker外部效度。

每臂所有原offered、500ms/8000sample推进与最后真实partial EOS保留；reference开销单独付费，不计服务成功。SLO miss、tie、Ready复用0、资源差>2%继续完整队列。身份、完整选定任务、账本不闭合或物理释放失败可以技术停止，但必须保持partial和planned/completed分母，不得把剩余格说成已完成。Ready0与2%没有参与删除/重试门。

## 额外2/4链共享资源机会对照

同两张GPU、两完整FP32 worker、Conservative与Fullcall各两个fresh、两个固定嵌套source组共8格，是有价值的资源机会成本控制。2-source组包含在4-source组内，新增独立speaker数为0；最多4个旧speaker，24个source/run观察不能变成24独立声学样本。两个固定混合负载也不是最大容量或稳态扩展性测量。

现有14ae Owner会给Conservative的full0/full1分配两个独立current-parent chain，因同sid的active_authority阻止重复，故不是“保守臂只用一张卡”。但其旧循环每次从sidlist[0]扫描，4链可能优先前两条，Fullcall还可能给第一条链两槽；这一缺陷足以使“per-sid公平共享”的解释不成立。Root已事前选择所有六臂共用的**全局canonical-first RR**作为修正，未把它包装成新算法贡献。

v3补验要点：先遍历所有可派发canonical工作，再允许任何conditional tail；cursor只在实际成功dispatch后前进；所有六臂同一路径；最大ahead、原frozen input/receipt guard、AU/SUP和原EOS不变；至少两个独立canonical链ready时Conservative实际两卡均可派发。原始输入时钟必须包含等待source，不能在获得worker时重置clock。

在canonical需求持续占满两worker时，Fullcall可能自然没有conditional dispatch并与Conservative趋同。这是该负载的机制边界，不是无效run、Ready0故障或重跑直到出现优势的理由。应并列记录canonical demand、free slots、conditional-only派发机会和实际两卡工作。

4-source组还需要其全部source在**同一新runtime**下的完整reference；pilot两source reference不能覆盖另两条，更不能用旧4f填充。新driver若增加multi-source入口，应在GPU前独立冻结，不把现有single-source代码尚无入口称为bug。

## GPU前仅保留真正需要补验的门

1. 新共享RR runtime及driver实际source冻结、完整manifest与新CPU控制通过；2fac中的14ae常量、64-file guard、reference marker与actual_NN绑定须按新完整source一并更新，保持严格检查，不放宽为任意source。
2. 针对新runtime实际执行并通过完整continuous/restored reference，随后才冻结24格service config；multi-source额外source同样必须完整覆盖。
3. Root重新激活CURRENT、默认和显式预检、环境/模型/WAV字节与fresh GPU owners/PID-generation登记。已有CPU/只读审阅不是GPU预约或神经task PASS。

除上述已经宣布的v3替换与常规真实启动门外，本轮不增加与因果问题无关的审批、风格重构或新实验前置。下面补充实际v3审阅，尚不将未生成的新reference说成已通过。

## 实际runtime v3冻结后的补验

实际commit为 `de0936b2e30179d63aeef6e235cd1af685578c58`，manifest `packages/BASELINE_SOURCE_v3.json` 的SHA256为 `ce99ca421f5f8b416a1545c57a600ee6a28f43e7d2c10294caa00f0d6636a7c9`。本审阅独立核对本地全部66个manifest文件的大小/SHA、Git HEAD与干净状态，零不匹配。相对实际14ae64文件，只有 `RUNTIME_POLICY_CONTRACT.json` 和 `resilience_owner.py` 改动，新增 `round_robin_dispatch.py` 与其测试；原神经程序、AU、SUP、durability和取消守卫文件逐字节未改。

`CanonicalFirstRoundRobin.peek` 先构造全source的canonical与conditional候选集合，再按层和RR顺序选择。它只读canonical/tail/accepted与_has_work/_reason，不调用会refresh/promote的next_full_start；查询没有注册、接纳receipt、发proof或cursor前移。Owner对每个空闲物理slot分别抓取一份accepted vector，保存canonical/accepted frontier和候选集合，保留decision_begin/end。后来的输入更新不能重写该tuple。第一次register和真实command.send成功后才confirm前移cursor，第二个slot重新查询，所以不能复用旧proposal重复派发。

一source时canonical/tail优先、完整8000sample/EOS步长和max-ahead保持原选择规则，差异只剩同等策略共有的查询/记录开销，不能把它称为零开销或逐时钟完全相同。多source时所有六臂共用同一Owner入口，Conservative仅禁止conditional候选；没有借RR为它限制单GPU。完整receipt/target/physical ownership仍由原register守卫最终决定。

我只读了已有正式CPU结果 `baseline_ops/CPU_BASELINE_V3/{GATE,SUMMARY}.json`：实际source同de0936，225测试、0fail/error/skip、无神经包导入、0model/GPU；summary SHA `18a5b96147aa35c4c1ce672563fbfb563a0d40a0dfa40ec3b0b1302886783f81`。其中11项新RR控制覆盖全局canonical优先、纯query、第二slot重查、并发后续release不改快照、原guard、单source与实际Owner的双卡/四source顺序、全部六臂共享。这个CPU结果不是我重新运行，也不是新神经等价/性能证据。

**v3共享dispatcher静态因果/来源审阅：PASS，未发现GPU前必须修改的缺陷。** v4资源对照合同SHA `3f2186b04c5ad2df95c59f1566ac54daa0a4af12b71971d61e1d5193083816da` 保留了合法零投机结果与固定两组解释边界。

## 实际driver v2与full4→prespecified2补验

driver已冻结为 `f367c4e1068a9391a0e99d8537c94995a3388e13`、20文件，manifest SHA `c9c0fa0c14424fae51d3e822f35286ba69c28b11233fa6c2aef848a231ec724b`，bundle SHA `bd1f9e278ae066bd63a9e8ce908ab6aae5f8d72c1c07f35add3ea020ba0b7f6e`。我独立核对本地全部20文件大小/SHA、HEAD和干净状态，零差异；未运行其测试或模型。

所有实际runtime常量已指向de0936，包括reference state内部marker、base source与66-file完整性守卫、Root noarg/explicit driver身份、service setting与严格原task对照。旧14ae和4f不能只换外层标签通过；2fac仍保留为历史前身。新CPU实验使用V2 ID，未覆盖V1。

`prepare_pilot` 在任何模型结果之前选择existing8 bank的metadata词典序first4，并同时冻结first2 pilot与first4 reference两份selection；4条WAV/PCM header与hash都核。它只预留24格service路径，未在真实新reference PASS前制造service config或reference PASS。

`bind_reference_subset.derive_subset` 先以严格actualv3和同一实际generator验证直接测量的full4父receipt，再保留事前词典序first2的完整原DETAILS行和genesis。`prespecified_reference_subset` 以不可变existing8 bank SHA验证first4，子集必须恰好first2，不能换另外两个speaker。子receipt使用不同状态 `PASS_PREDECLARED_SOURCE_SUBSET_OF_MEASURED_REFERENCE`，并明确new_model_calls=0、new_neural_verification=false；该0只表示派生步骤未新推理，父full4的paid ledger/energy由显式reference_cost_source链接保留。

实际读取子receipt时再次递归校验直接父receipt、父selection和bank SHA、原full4的完整新source链/C/IDs，随后要求子DETAILS与对应父行、子genesis与对应父genesis按完整canonical字节一致。改子tokens或genesis再刷新子文件hash仍过不了父等价检查。没有放宽actual-parent、AU/SUP、状态字段或500ms/EOS要求。

新 `test_reference_subset` 的6项正反控制已纳入正式CPU入口，覆盖有效full4→first2、改选其他2、子IDs/genesis篡改后重hash、失败/旧source父reference、bank/selection漂移、派生冒充新推理。我读取 `baseline_ops/CPU_PILOT_DRIVER_V2` 正式结果：56测试、零fail/error/skip、actual runtime de0936和driver f367、无神经包/模型/GPU调用，summary SHA `6caff962aa9c540df74886aee04a749c547b80eb383e8181627a21ca754f47fe`。它仍不是“模型reference已生成”。

**最终独立静态审阅结论：actual runtime de0936 / driver f367c4 的pilot因果、来源与full4→first2绑定为GO，无本轮必须修改的代码/协议问题。** Root尚须激活对应CURRENT/默认和显式预检、fresh资源/资产核验、真实新runtime reference及其退出闭合，之后才能冻结/启动24格服务。另8格multi-source driver尚须按v4合同冻结；缺少尚未编写的入口不计作现有pilot缺陷，也不能用当前single-source配置假称已支持multi-source。

## 实际metadata准备与六步CLI核对

已读取 `baseline_ops/PILOT_PREPARATION_V2` 的selection、REFERENCE_PLAN、SUMMARY和LAUNCH_HANDOFF。预登记reference源恰为S0769/S0901/S0902/S0906；pilot恰为前两个S0769/S0901。24格各source均六策略r0顺序精确反转为r1，主GPU由0换1；所有service config状态仍是PENDING_ACTUAL_NEW_REFERENCE_PASS，未把预留路径说成已冻结可运行配置。

实际六步顺序为：1) 将Root CURRENT-de0936与explicit-f367收据绑定新reference计划；2) 执行paid full4新source原连续/restore reference；3) 在父真实PASS后派生事前pilot2严格子集；4) 才生成24格实际service configs；5) 绑定新service prelaunch；6) 运行24格服务。所有命令指向同一de0936/66与f367/20，full4输出为8TB `REFERENCE_FULL4_V2`，pilot输出为 `PILOT24_V2`，没有旧4f reference冒充路径。

REFERENCE_PLAN SHA为 `4b6839bbd1b0eaadedba7e24f42fb132b8790edf7329e0c54237926c5b58daf6`；该plan内environment SHA `0804bfeff2385e31a58a17e7a1e2cf65404f5f4bec7b6c2d34931ddc1879dc1c`，reference-selection SHA `00bf513008a6d5c298822a9f386ea60713643a41998f4935e8b05c3ad0437b6a`。计划metadata PASS不是GPU预约、neural READY或reference PASS；Root仍须记录实际reference PID/start_ticks、命令SHA与物理退出，服务阶段保留每格所有失败/partial/negative结果。
