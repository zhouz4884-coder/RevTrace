# A — Realization-equivalent Recovery：NO-GO（当前资产）

## 必须区分的三种关系

| 关系 | 足够证明什么 | 不足以证明什么 |
|---|---|---|
| Root Input Equivalence | 在同前沿/χ、原固定batch条件下，两个逻辑状态得到相同实际模型相关输入 | 不自动给任何生成结果Authority权限，也不保证换batch重跑相同 |
| 确定性Adapter重解释 | 在已知相同输入/选择来源下，旧Z经相同Render得到何种P/text | 不能把CPU重解释旧Z称为新parent下重新生成 |
| One-step Convergence | 两个**实际分别执行**的不同条件调用事后得到相同输出/状态 | 未执行第二个调用前不能凭猜测复用；观察到一次不构成提前可判定规则 |

## 冻结真实机会数量

对Phase D最终90个真实GPU serving单元做CPU只读审计，核验180个原events/worker-record哈希与上轮原始索引一致。3,993次连续性检查中，原Exact-P机制已允许3,715次；130次缺少相同认证边界的private节点；148次P不匹配。

148次是重复运行/策略下的观测，只有**12个唯一(source, frontier, Pold, Pnew)组合**，不是148个独立声学故障。对148次P不匹配：

- rollback5（含Unicode回退）后条件前缀相同：**0/148**；
- 前缀重新tokenize后相同：**0/148**；旧/新P经decode→encode发生规范化变化：均0；
- 新增可证明合法根、可挽救整条后代链：均0；
- 已存在的完成后代最大深度仅1；去重后21个后代GPU batch区间共17.164秒；
- 现机制后来对这些后代同音频区间再次执行：**0次**。这17.164秒是已经付出的工作，不是可直接从关键路径扣除的“节省”。

原始例子保存在A_WORK_BUDGET的负对中，所有计数和逐caseCSV保留。源、repeat和slot分层；没有用复制流放大样本。

## Whisper截断并不是这批资产的机会

安装版HF长音频previous-segment分支存在`max_target_positions//2-1`的截断，但Phase D F2使用显式`prompt_ids=processor.get_prompt_ids(text)`；实际调用不走该previous-segment截断分支，不能把两条路径混为一谈。

32对target/future历史中30对文本不同，**0对**出现“逻辑历史不同、实际首decoder输入相同”；实际历史prompt最长60tokens。CPU超长字符串控制也确认本安装版本get_prompt_ids本身不替调用者截断（各1001tokens），这不是合法长prompt GPU运行或真实分支机会。

不同实际输入得到相同Z的现象有：target2例、future5例。这些是已有真实GPU双调用的事后收敛观察，不是输入等价，也没有可提前判断的合法复用条件。Whisper尚无对应的Property D private DAG及已测关键路径重算成本，不能借另一模型的接口名启动Grafting。

## 裁定

**当前路线NO-GO，不实现DAG Grafting，不追加该方向GPU。** 数据支持的新增合法复用和可扣减关键路径为0；这不证明任何未来workload/adapter都不可能。若将来有真实长历史落在截断区且仍有可省的完成后代，才值得以新协议重开。不能通过CPU重解释、单步事后巧合或把已执行工作当重复工作来制造正收益。
