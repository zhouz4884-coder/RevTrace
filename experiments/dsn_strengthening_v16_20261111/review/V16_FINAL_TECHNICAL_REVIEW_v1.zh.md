# v16首次全稿：独立技术一致性核对

范围：当前writing worktree的02/03/04、05原生比较段、N8表/macros、Fig.2，以及已封存aa9db5模型/控件与SUMMARY。只读当前PDF文字和Root已渲染page-04/05；没有重编译、测试、推理、raw重扫或修改论文。首次审阅PDF SHA256为`f87a5e96ccbd34b68b6278fd6d064a5f8420dbb5a2558f597ecee3aa84ef55cf`；Root后续修改/重编译不沿用该快照身份。

结论：没有发现需要重新实验才能解决的致命证明或任务一致性问题。以下两个文字点应在最终编译前关闭；M1已看到Root修复。

## 必改（2项）

1. **M1，pilot零ready命中不可写成N8结果（已修复）。** 首次05主比较段的“zero realized hits”会覆盖后续N8范围。当前tex已改为八源有3个admitted complete-result reuse，正确；后面明确限定两源六策略pilot的0 hit/56 reissue可保留。最终PDF应由Root新编译吸收这项修复，不能仍交付首次旧文字。
2. **M2，明确归纳是单会话事实投影。** `03_design_v16.tex` invariant段目前从“Let D=(d1,...,dn) be the verified recoverable fact prefix”直接推出相邻记录形成一条x链；真实FactStore共享日志按source_id维护多个roots。建议首句改为“For one session, let D be its ordered facts in the verified recoverable journal prefix ...”，证明中的“writer’s verified tail”相应写“that session’s verified tail”。这样允许全局日志交错，同时保持每条原反馈链的归纳；不是增加guard或改变实现。

## 已核对可接受的核心点

* **证明不循环。** 合法新边来自可信原完整执行`s =>_(A,X) t`，再由原始job/result绑定、Owner installed-parent检查与FactStore该source根检查证明`s=x_n`；不是先假定newfact合法。实际`resilience_policy._commit`及`resilience_storage._validate_transition/commit`对应这些守卫。sync后install前允许installed滞后一条；旧installed不能越过writer-root再次append。callback不确定冻结新写；replay不引入新神经边。上述论证是声明前提下的动作归纳，不冒充机械抽取证明。
* **信任/故障边界一致。** Section2声明原worker/host/input忠实、状态充分、同步可信；不称GPU算术证明/Byzantine容错。Section4的Owner-group冷重建、worker-only已收完整结果存活、旧channel无新权限、terminal/drain/exit才释放物理占用，与当前source边界相符。幸存Consumer与model清provisional的对应缺口被单独保留。
* **C1示例真实属于既有规格。** aa9db5未改原`test_model.py:58–70`的三frontier/四call单独控制：A0、B1先full并释放worker、C2出生仍为x0；A否定B输入后C仍UNKNOWN；D3原计算收敛到x2，C才CONFIRMED。selected链A–D–C连续，未跳frontier/回滚/复用错误B；该例未声称自然NN3发生率。它是命名控制，不属于两frontier/至多3issued的BFS profile。
* **Fig.2语义一致。** 已运行j3冻结输入hat(P2)，原parent选P2可确认输入，但不确认其自身hat(P3)；完整C/U返回P3+ID，再AU/sync/install。SUP判断的是实际whole h在应用P2时的支持。图中j3/parent/child、forecast与fullresult没有互换；caption明确是因果示意而非时序测量。
* **最终N8口径一致。** 32 Full/Ready cells，8既有voices×2timing repeats×2policies；首2pilot、后6confirmation。表中credit129.460/58.500audio-s、93.90/42.43%、worker223.215/322.991s、91.880/117.823kJ、pass10/16 vs0/16，与宏93.9/42.4、差51.47pp一致；figure_data_v16逐源/逐重复方向全部Full>Ready。没有把16 repeats当16独立声音，能耗是双板至模型物理drain而非纯GPU-active或取消独占收益。

## 可选精化（1项）

**Q7已有证据可更紧凑地展示，不需新检查。** 当前“hand-written Python state machine + BFS + depth12 + cutoff +35=27+8”已经正确。可加一句明确immutable Python dataclass状态/自写deque BFS，以及正常`2frontier/≤3issued/0fault:6231states,11142edges`、故障`1frontier/≤2issued/≤1fault:14074states,25799edges`；两者depth12、cutoff2144/2828。依据为`formal_source_dev/model.py`、`invariants.py:71–105`及`FORMAL_ACTION_RESULTS_v1/results/SUMMARY.json`。这比仅补工具名更能回答有限覆盖边界；不增加35之外的“27个新检查”，也不称全Python/CUDA证明或全局最小条件。

交接：Root独占最终论文编辑/编译；本审阅只写此说明文件。无需新增实验。
