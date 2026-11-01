# v7 增量编辑：独立主张范围审查

2026-11-01（Asia/Hong_Kong）。基点 `6240efceb007b9423b90871128f0cef1af79b3c2`。完整读取用户 Delta 文件和粘贴意见，核对 v7 的 introduction、system/feedback contract、native extension、selected-trace refinement、core evaluation 开头及 native 机会边界。此审查只判断主张与已有文字的范围；未运行实际 reader、模型、SSH 或原始日志扫描，未修改稿件/runtime/CURRENT，也不冒称本轮逐页视觉验收。

本轮应保留 v7 的主线和已完成工作；以下六项足以收紧论证。

| 优先项 | 必须收紧的内容 | 原文依据与建议动作 |
|---|---|---|
| 1. 区间级与整场级分开 | 首页 “A streaming service can meet its delivery deadlines” 容易把该区间两次 first delivery 达标提升为整场服务达标。 | `01_progress_introduction.tex:1–10`。改为 audio interval 的两项首次交付义务；所处 c16 整场仍失败。随后一处解释 trusted/selected 是原受保护选择所接受。案例小数集中在图注，正文保留问题和后果。 |
| 2. 三判断用不同后果解释 | 证据异步到达，同一事件对 view、未来调用、已接受结果的动作可以不同。只列“检查输入/结果/显示”仍不足。 | `03_native_extension.tex:12–32` 已有完整依据：调用先在预测输入上执行；真实父状态后来确认；自己的预测错误不反证输入。view 失支持应撤回，而未来 input UNKNOWN 既不授权 commit，也不是 refutation-cancel 的依据。图2应明确 already-running call 与 later evidence 合流，不画 EL 先于启动的时间串联。 |
| 3. 两种实例与三类实验作互补导航 | Core 的固定 Private/Authority 两卡分工不应被泛化到 native。Native matched 的45.2%→99.2%不能当作该 bank 上的 SUP 效果。 | `05_evaluation_core.tex:3–10` 与 `03_native_extension.tex:17`：core 独立 FP16 Private / FP32 Authority；native 两卡都有完整原 ASR–Correct/Update。`05_native_retention.tex:92–95` 明确 final matched 无 compatible-ahead 应用。导航分别写 core 因子检验计算到消费的协调、native 检验原递归任务的提前完整调用、failure 检验 accepted result 与 future message authority。 |
| 4. 两个性质的字母表与事件边界分开 | 推荐桥句 “continuity protects what remains available between advances” 仍可能被读成两次可信推进之间的无条件连续可用保证。 | `03_native_refinement_working.tex:10–15,38–43` 的投影只含 distinct durable selected facts；`03_continuation.tex` Prop2 仅在 authorized compatible application 且 ahead/support/no-independent-withdrawal 前提下保留 h。安全桥句：**“The refinement constrains which complete results may extend the durable selected prefix; the continuity condition separately preserves a supported ahead view at a compatible selected-state application.”** 不声称整个外部行为等价或全局单调。 |
| 5. Figure3中“支持”的两种含义不合并 | 在线依赖合法性 SUP 与事后同G选中文本一致不是同一分类。 | `05_evaluation_core.tex:55–60` 已明确二者不同。左右面板直接标 Core Qwen / 24 speakers / 714.110 s per arm 与 Native StreamCorrect / 4 speakers / 66.340 s per arm/bank；两段 timely 都可能是合法临时输出。保留匹配/不匹配/错过期限的中性名称，明示0.8%/3.3%小尾段；Pass仍分 matched trials 与 resident requests，不能把时长比例当请求成功率。 |
| 6. 拒绝末尾追加意见中的两个“硬化” | 不接受“引用必须21→30+”作为未经论证的门槛，也不接受“trades27.4ms forzero gap”。 | 引用建议未给出 DSN 官方数量门槛依据；只按真正支撑比较的对象与操作边界补主源。27.4ms 是 joint 相对 D2 的超时，**不是**相对 computation-only 的首显差；下面给出算术和因果边界。 |

## Fig1 算术与因果边界

已有测量值，不运行新 reader：

- Computation-only 首显 `1.4439057689160109 s`。
- Joint 首显 `2.0274376049637794 s`。
- Joint 相对2秒 D2 超时 `27.43760496377945 ms`。
- 两臂首显差 `583.5318360477685 ms`。

因此“trade27.4ms”首先是端点混用。即使改成583.5ms，也不能把不同执行交错的差值写成已识别的因果交换关系。宜写：**“The two observed executions separate first-delivery latency from availability after first delivery.”** 再由独立因子实验检验协调效应。

图(b)中的 “0 gap” 若放在图(a)整个 `1.544→3.720 s` 阴影对应位置也会误导：joint直到2.027s才首次覆盖该区间。可标 **“No later F14 coverage gap observed”**，明确是该运行首次交付之后的观察，不是全时域零损失、同事件反事实或生产发生率。

## 不应重做或削弱的内容

作者构造的 Alternative joint implementation 身份在 `05_evaluation_core.tex:36–40,99–103` 已清楚；其同效是完整组合正控行为，不应为了原创性要求它失败。v7 的命名、Findings、最终两臂前置及无全局跨会话优先描述均无需再做一次。最终6/8、resident7/8、全部15个headline whole-D2失败、共同drain窗口10.61%可靠性开销、无reset质量/期限失败、旧fact replay与新结果恢复不同都应保留。

本轮合理终点是上述语义闭环加真实PDF/灰度/冷读验收；没有由此产生新的神经机制实验缺口。

## 新稿文本闭环复核（2026-11-01）

只读工作目录 `Paper_DSN/revisions/20261101_dsn_editorial_revision` 的相关 TeX；此项不代替编译、原始数值复算或新图视觉验收。Root要求的实质边界目前均已落实，未发现新的文本主张越界：

- 首页首句明确为 audio interval 的两项首次交付义务，并一处定义 trusted feedback 的选择含义；Figure1仍保留joint的D2+27.4ms、不同交错和非事件匹配反事实。
- “证据在不同时间到达”已接到三种对象的不同动作；运行例保持先在预测输入上执行、真实父状态后来确认，原Correct/Update仍决定结果。
- II明确Canonical/Private是逻辑角色：core独立Private/Authority worker，native则是两个完整recognizer–corrector worker，未把物理分工跨实例泛化。
- V的三study导航分别指向core[EL]/[SUP]、native[EL]/[AU]与失效对象资格；native段已直接说明matched无compatible-ahead应用，45.2%→99.2%收益不归因于该bank的SUP。
- Refinement桥句已准确限定为compatible selected-state application时保留受支持ahead view，并说明后来publication仍可修订；没有采用between-advances的全时连续保证。原selected-fact投影和条件前提保留。
- 新Related Work正面承认KV复用、SGLang跨API原语投机和target-model token verification，比较其复用对象与本稿完整递归调用及实际whole-view动作，没有写成外部系统“不可能”。新增三条的原文与书目信息采用本轮独立primary-source核查；本次不冒称重新核了原论文，也不按引用数量评价覆盖。

摘要现在以“already received complete results”下的匹配保留/失配拒绝收尾，比泛称producer failure更准确；6.52%对最终Conservative的节能与10.61%相对早期RevTrace的开销、最终6/8及resident7/8等直接边界仍在正文。

剩余待验收的是新图实际输出与最终caption的一致性：特别是already-running调用的合流关系、实线/虚线定义、左右面板人群与单位、微小未及时尾段标签。这些不能只由当前TeX文字或旧v7图推断已经通过；图到位后在本文件追加一次简短复述即可，无需扩内容或新增实验。
