# 共享守卫与C1/C2贡献：强版本依赖臂同效时如何解释

2026-11-11。只读实际运行源`baseline_source_v3`，commit **de0936b2e30179d63aeef6e235cd1af685578c58**（下称N）。没有读取pilot输出、运行分析/测试或改变source/CURRENT。本文是最终结果完成后可用的条件性解释，沿用已冻结v5的机会与决策门，不将当前部分运行写成结论。

**核心判断：即使最终Fullcall与强Dependency-versioned同效，也不能推出“只有提前派发起作用”。** 两臂同时共享合法在飞保留、完整输入见证、原C/U选择、durability与整view支持；该对比没有移除这些共同条件。同效可以削弱某个额外retention规则的必要性或性能增量，不能凭此拆掉整个组合贡献，也不能制造RevTrace独占算法增益。

## 1. 实际代码中共同的是什么

`DependencyVersionedCoordinator`直接继承`ResilientFullSpecCoordinator`（`N/versioned_policy.py:152–169`），先调用原`_reason`，再加ancestor fence。原classifier位于`N/fullspec_policy.py:35–52`：当前完整start相等可保留；同frontier完整cut不等才refute；未来未知start不因没有witness就判错。`FeedbackCut.same`比较完整规范字节，字段包括token/context/cursor/audio/contract等（`N/feedback_contract.py:16–35`）；这不是只按birth version、parent文字或一个松散版本号匹配。

因此该强control的“expected parent version”实际绑定完整`FeedbackCut`。一个版本ID若唯一代表这个完整输入，可以承载input witness；C1不要求再建一套重复的数据结构。该control的直接兼容handover保留与Fullcall一致，不能把旧92次晋升解释为92次两策略分歧。

所有合法臂还共享：

* `N/fullspec_policy.py:111–124,163–181`的原job/完整输入与原完整结果绑定；`N/resilience_policy.py:150–185`的append前实际parent/session检查、hook后再检与不确定写冻结；原selected结果不是ASR预测投影。
* `N/resilience_storage.py:71–99`的原record/真实WAL parent校验与同步先于安装；`N/resilience_consumer.py:26–42,48–76`独立校验durable fact和整view路径；`FeedbackCut/Reconciler`支持关系不因策略名称改变。
* 相同两份FP32完整原ASR/C/U、warmup、原500ms输入与EOS、实际Consumer、物理lease/通道、全服务两板计费。

共同`CanonicalFirstRoundRobin`（`N/round_robin_dispatch.py:27–57`）仅决定候选分配，Owner仍register后才send（`N/resilience_owner.py:170–179`）。Conservative禁conditional proposal，其余臂允许；但policy的`_has_work/_reason`和取消会改变后续实际可派任务，**共同allocator代码不等于相同实际schedule**。

## 2. 对比真正改变的对象

| 对比 | 在共同合法协议上实际改变什么 | 能识别什么；不能识别什么 |
|---|---|---|
| Fullcall vs Dependency-versioned | 后者在较早冻结祖先被实际否证时永久撤销descendant版本；Fullcall仍保留尚未被其同frontier完整输入反证的job，等待可能收敛。见`versioned_policy.py:167–220` | 祖先撤销与完整输入保留规则的条件性增量；不是“有/无完整输入验证” |
| Fullcall vs Ready-only | 后者在每次实际install时fence尚无Owner已验证完整receipt的call，保留已有ready原结果；见`:90–145` | 合法在飞结果保留相对只复用已完成结果的增量；零ready命中不能事先证明它等于Conservative |
| Fullcall vs safe UIR | UIR仅不转发cooperative before-C hint；仍分类、AU、SUP。见`retention_policy.py:11–44` | 现有合法早停的资源/服务增量；既不是删除classifier开销，也不是移除end-use资格 |
| Fullcall vs Conservative | 后者不派conditional tail，仍保留共享合法使用与SUP | 在此共同服务合同下，提前原完整调用及其保留带来的联合效果；不能单独分离派发、保留和所有守卫的可加秒数 |
| 既有R×S | 曾独立开关compute/view retention，在其冻结任务与source范围内比较 | 联合连续性/及时性与trade-off；该独立证据不能冒称此次五臂又识别了SUP独立增量 |

strict birth-root辅助臂比强Dependency-versioned更粗，不能代替后者，更不能代表全部versioning系统。

## 3. 如果最终24格仍同效，应削弱哪一项

首先分清“相同dual-credit端点”与“完整行为等价”。信用按offered前沿计，端点相同仍可能有延迟、paid work、能耗或Consumer轨迹差异；没有预先等效检验也不能把24格写成总体统计等效。该pilot是两位speaker、两次fresh重复、六个臂；不是24个独立声学来源。

* **应削弱/撤回：** 相对这个强expected-parent版本control，Fullcall有独特的自然性能优势、其更宽松的祖先失配后保留/后续完整输入收敛规则在当前workload必不可少，或每个晋升都只能由Fullcall实现。若真实分歧充分但结果仍近，应接受该增量null/简单策略足够，不能换workload直到赢。
* **若真实分歧很少/没有：** 本pilot主要检验了两者共同的直接兼容handover，缺少的是**特定祖先规则增量**的自然实证机会。仍完整报告同效；按已冻结v5决定是否还有至多两个独立声明的开发点，不因null自动扩bank。shadow predicate只说明实际状态上的潜在分歧，不是另一schedule已经运行过。
* **不能推出：** 提前派发是唯一原因、所有input/AU检查冗余、三种逻辑判断不成立、先前联合R×S结果消失，或完整系统已经在某个未复现外部作品中被证明同样实现。

## 4. C1与C2仍可怎样成立

**C1：可复用的服务条件与对象分解。** 把“call输入是否得到真实支持”“原完整结果是否有selected使用权”“Consumer整view是否仍受支持”分开，给出共用witness可如何建立这些用途的条件与guard映射。AU/原任务和SUP不能由提前派发替代；安全UIR本身也保留它们。它是有实现、反例和有界检查支持的充分条件/使用纪律，不是三套物理证书必须独立，更不是全局最小协议。强control也采用这些条件，说明抽象可由另一保留规则实例化，不能倒过来称额外算法增益已经得到证明。

**C2：新应用中的联合机制与系统证据。** 原ASR→Correct→Update是反馈递归，提前调用的完整start可能后来被确认/否证；可显示预测、原selected结果与完整反馈状态不是一个对象。协调实际在飞工作、durable selected prefix、Consumer整view与故障边界，并在同任务同资源下揭示“compute保留可改善及时性却恶化撤回、view单独保留存在代价、joint达到更好的组合”，仍是一项可检验的新应用/组合贡献。称它只是prefetch会遗漏使用授权与持续可用性质；称这些所有原语均为新发明也不成立。

自然trace中与Ready-only的合法model-active差异、原完整任务不变、实际SUP连续性检查以及既有严格R×S证据各有独立作用。它们不能因Vdag tie被抹掉，但也不能被打包成“每一内部检查都贡献若干独立秒数”。若Ready-only或UIR也在有真实机会时同效，相应在飞/早停增量也须据实收缩；保留合同与组合贡献，不用概念正确替代性能验证。

## 5. R1外部基线的诚实定位

这次Dependency-versioned/Ready-only/UIR是**作者构建的强控制**，用于检验比粗birth-version更实质的替代规则。若它们足以达到相同端点，这应正面展示，而不弱化或换名。它们不是SSBD、Retire或PredGen的完整已发表系统复现，也不能将作者在同一substrate中为强control实现的AU/SUP视为外部系统已经原样具备这些语义的证据。

因此本轮能够加强机制归因与同资源对照，不能宣称已经赢过外部SOTA。R1的实际外部系统/更多资源对照缺口仍须按已有范围明确：若原任务、输出、选择或可观察量不兼容，应逐项说明并保留其真实原能力，不伪造同任务head-to-head，也不以“不直接可比”推导优越性。新应用/组合可以是贡献，但须依靠服务问题、合同、可靠实现与完整实测来成立，而非仅靠新命名。

建议最终结果句式（条件模板，非已完成结果）：**“在该冻结原任务与资源条件下，基于完整输入绑定的expected-parent版本策略与Fullcall达到相同的[已核实端点]；本研究未建立祖先失配后继续保留这一额外规则的性能增益。两者均保留合法提前执行与原结果/整view守卫；其相对Ready-only、Conservative和独立R×S的发现分别报告。”**
