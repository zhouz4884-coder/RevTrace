# 正式补强表图：先验证据与绘制契约

此目录是独立的事后分析工具开发稿，不属于原生神经执行源码，不改变
`source_v2`、正式计划、CURRENT、原D2/C8/所有offered/EOS或实验队列。
正式运行前须另行冻结此工具的完整源码、配置、环境及全部输入SHA256；
开发稿存在不意味着正式分析已运行或任何结果已通过。

## 最少充分结构

一张跨栏表：S0908六条件，Conservative / FullSpec固定次序。主要字段为
独立语义检查的非法安装数、完整原任务完成fresh数、局部拒绝数及拒绝后
Canonical变更数、故障至首个故障后新模型完成且实际认证消费的时钟、
原D2/C8通过fresh数、双GPU在原service区间内的能耗。完整机器附表另存
EOS misses、逐臂逐fresh原分位数、最终CER、输入未完成债务、独立精化
结论、旧fact重放/新durable fact/新推理认证消费等全部时钟。

六主条件每臂2fresh；4回归与8长流服务格必须进入机器附表和scope核对，
不混入六条件的分母。两次fresh范围不是置信区间或独立声学重复。没有
适用故障的normal/duplicate new-inference recovery clock为NA，不是0。
冷Owner的原期限失败必须保留。Owner-before-durable与
Owner-after-durable不能合并。旧durable fact实际重放不等于新推理进展。

一张跨栏4-panel图，目标7.2×3.0 inch、8pt以上：

1. 原生audio buffer与post-trim decoder-token边界；两个量分单位。
2. 所有offered前沿的实际D与C延迟，保留原2s/8s门限；selected-edge
   own-prediction改变与unknown保留为逐格rug。D-C另存机器表，不能以
   相同差值掩盖D与C同时超期。
3. 实际1Hz协议历史：unpinned inbox terminals、各audit_retained类别的
   同行最大值、各live依赖类别的同行最大值；consumer pins与pending
   publications另列。不相加各自max，不称总占用。
4. 当前完整cut、当前输出文本的序列与Owner RSS分轴。immutable input
   和NVML GPU memory在机器附表分列；缺失worker torch alloc/reserved
   保留unknown。没有常量总RSS或常量当前模型状态结论。

全部8长流格、两个来源、两臂和两fresh均保留。绘图可使用每条run同一
秒内真实样本的max减少覆盖，必须记录这一变换；不得按效果抽点或删
负来源。所有准确计数与极值从未抽样的原序列计算并交付。实际worker
边界包含重算，不等于selected Canonical边数；selected-edge预测改变
由同Owner epoch/job的asr_early projection与实际durable next_state比较。
selected_correction或selection_changed是另一字段，不替代该定义。
min-max envelope仅在固定(source,arm)的两fresh内形成，不混合两个来源
或两臂。delay按原offered audio frontier对齐；history/RSS使用从原ORIGIN
起的实际wall time，保留最后输入后的drain/backlog尾部。两个原输入结束
时刻在wall面板标记，不能把音频秒与服务wall秒混为同一时钟。

## 不能跨越的证据层

- 原连续无restore参考及serialized-restore核对是参考控制，不能当服务图。
- 事后trace审计、观察性边界及绘图分配不是在线控制内存。
- history.inbox.terminal - pinned_terminals <= terminal_limit(64)；总terminal
  可超过64。audit_retained每类各自<=history_limit；issued_highwater与
  audit_total累计，不能作为live entries，也不能在内存图上冒称增长泄漏。
- live/view/outbox依赖类别的观测峰值与固定64的历史保留上限分开。
- local_reject_canonical_mutations=0不能推出所有安装合法，不能推出无
  错拒绝。非法安装与合法进展误拒绝必须来自对应独立精化/witness审计。
  输入缺失保持unknown；不得从PASS gate补造0。
- soft trim predicate与源推导L>=448只表示对应的计数事件，不证明位置
  越界或实际forward输入长度；阈值说明遵循NATIVE_CONTEXT_COUNT_DEFINITIONS。
- 有限synthetic流的覆盖不是自然发生率或普适保证。

## 导出与QA门

导出不调用模型、不写执行目录，仅从已完成的raw读取，并输出有界计数、
哈希、时序及summary。默认原样保留所有时序；输出上限超出即fail，不
静默截断。每个图表值必须追溯到冻结summary或有界序列及raw输入SHA。
正式产物包括PDF、SVG、300dpi PNG、可复算CSV/JSON、TeX表及run record。
正式operator的原冻结config与运行时echo是两份独立字节编码：原config
字节按精确plan SHA验证，echo完整JSON对象必须与其严格相等，echo字节
SHA另与导出和metrics回执核对。两SHA分别命名，不能冒称字节相同。

QA须核对：36/36格与source commit、每主条件2+2fresh、回归4与长流8独立
scope；原始missing D/C数；两个Owner条件的旧/新时钟；全8长流曲线；
上述逐row界限；所有文本字号>=8pt；SVG保留可编辑text、PDF无Type3字体；
PDF/SVG尺寸匹配且最终论文缩放后仍>=8pt；在实际主稿尺寸渲染，检查
裁切、重叠、单位、legend及grayscale可辨。只有数据与视觉核验均完成
才写正式分析gate，不能因为绘图无异常而称实验PASS。
