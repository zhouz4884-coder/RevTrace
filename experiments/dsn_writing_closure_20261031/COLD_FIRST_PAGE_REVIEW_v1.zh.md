# 第一页独立冷读评审 v1

评审范围：仅阅读 `Paper_DSN/revisions/20261031_dsn_story_progress/main.pdf` 第 1 页，通过 `pdftotext -f 1 -l 1 -layout` 提取全文。未阅读后续章节、结果文件或项目历史。本报告评估读者能否理解故事，不评估证明与实验是否成立。

## 1. 我读到的具体问题及其意义

一个流式语音系统已经按时显示了文本，随后可信纠正状态发生更新，系统用一个较短的新快照替换整个假设。旧文本的计算其实仍与新选定的反馈状态相容，却暂时从用户视图中消失。第一页的实例中，37 个字符按时出现，然后消失 2.176 秒；稍后又以相同文字返回。单独检查首次交付是否准时，会漏掉这种交付后的服务退步。

这值得关心，因为纠正结果又是后续识别的输入：新反馈确实可能使一部分旧工作失效，因此不能简单保留所有东西；但丢弃所有旧工作又会抹掉仍然有效的进展。系统需要同时维护计算的合法性和用户当前可用的完整输出。第一页给出的 12→17 次撤回说明，只增加计算复用甚至可能改善交付速度而恶化可见服务的连续性。

## 2. 一句话技术主张

RevTrace 把“旧调用的完整输入是否仍被选定父状态确认”“其结果是否仍由原选择过程授权”“消费者的整个当前假设是否仍有完整依赖支持”分开判断，再联合保留符合条件的计算与视图，使可信反馈更新不必撤回仍然有效的进展。

## 3. 与普通 memoization 有何机制差别

我理解的差别不在于保存和命中旧结果，而在于反馈状态变化后仍需满足的三个不同合法性条件。匹配文本、调用的出生版本或生产者是否存活，不能替代这些条件。旧调用可以在自身下一步预测错误时仍拥有有效输入；调用输入有效也不自动授权提交其结果；某一结果合法也不自动证明由多个依赖组成的整个显示视图合法。

原来的纠正与更新流程仍要执行，复用不能绕过其选择权。已接受结果还可能比其生产进程活得更久，因此存储、权限和视图支持不能都绑定到进程存活这一位状态。第一页已经说明这是一个协调协议的主张，但尚未给出足够具体的例子，让冷读者立刻看见三个判断各自改变哪个运行时动作。

## 4. 第一页承诺的证据及其边界

- **形式关系**：一个有条件的 selected-trace refinement 论证，把提前执行完整调用与被保护程序的选择历史联系起来。措辞是条件性论证；第一页没有给出全部假设，也没有使我理解为任意故障或任意反馈下的无条件保证。
- **交互效应**：预先声明的 24-speaker stratum，用因子控制区分计算保留与视图保留。计算单独保留使 frontier withdrawals 从 12 增为 17，联合保留为 0；联合臂增加 26.645 秒 deadline credit，总 offered 为 714.110 秒。这是指定评估层的证据，不能读成自然工作负载中的普遍发生率或普遍消除。
- **原生纠正执行**：匹配的 native correction 比较保留原选择历史，获得 66.340 秒中 65.822 秒的 credit，八次试验有六次通过两个 whole-run deadline；保守执行为零次通过。正文还给出保守臂 30.0 秒与独立请求七次通过作为上下文。我的理解是这个服务设置中的有限次数比较，不能外推为任意负载下的端到端保证。
- **失败边界**：故障与持续状态实验承诺暴露恢复、质量和资源成本。第一页明确保留 EOS misses、overload、cold recovery 与 no-reset quality failures，没有把这些场景包装为全面解决。

当前最难解读的是 credit 的分母和计量对象：这些“秒”如何由两类截止期及交付后保留共同累计，第一页没有定义。因此我能复述实验数值，却不能独立判断 26.645 秒提升的服务含义或把它与撤回次数直接对应。

## 5. 三个主要理解障碍与小幅措辞修复

### 1）“trusted feedback / selected parent / selected root”切换太快

“trusted”可能被理解为文本本身正确，也可能指被保护流程已经授权；第一页更像后者。parent 与 root 又在缺少一个实体例子的情况下出现，读者需要自己推断它们是不是同一条纠正依赖链中的不同位置。

**小修建议**：在首次出现时直接把事件写实，例如把 “when trusted feedback advances” 改为 “when the protected correction pipeline selects a new feedback state for later calls”。后续第一次使用 parent 时补 “the selected correction on which that call depends”。若 trusted 另有含义，应使用实际契约中的定义，避免上述句子替作者新增假设。

### 2）核心三元组仍像抽象标签，“joint retention”也省略了保留对象

“complete-input confirmation, original selection authority, and whole-view support”确实传达了三件事，但完整输入中包含什么、原选择何时授权结果、整个视图的支持何时需要重验，还不能从第一页直接操作化。它们是本稿的唯一核心贡献，值得把一次抽象列举换成一次动作说明。

**小修建议**：将其中一处列举换为：“Before retaining an old call, RevTrace checks its entire frozen input against the selected parent; its result still passes the original selection, and a new selected root separately triggers validation of the Consumer's entire displayed hypothesis.” 同时把首次 “joint retention” 写成 “joint retention of eligible computation and the supported displayed hypothesis”。这样明确两种保留对象，而无需展开状态机。

### 3）“deadline credit / offered / whole-run passes”先给高精度数字，后给意义

第一页在两个不同规模的实验中连续报告秒数、分母和通过次数，但 credit 尚未定义。冷读者容易把它误读为墙钟节省、音频时长、积分面积或普遍可用率；“两个 whole-run deadline”也不能直接等同于实例中单个区间的两个截止期。

**小修建议**：第一处先报告能直接理解的服务结果，再引入指标，例如：“Within the declared 24-speaker stratum, joint retention eliminates frontier withdrawals (0 versus 12/17) and adds 26.645 s of deadline credit under the accounting in Section V.” 紧接着补一句准确的 credit 计量定义以及 offered 的分母含义。原生比较则可先写 “Six of eight matched native trials meet both whole-run deadlines, versus zero for conservative execution”，再给 credit。这里不代拟指标定义，以免在冷读评审中发明作者的计分规则。

## 判断

系统审稿人仅凭第一页，**能够重建粗粒度的问题→障碍→方案→证据链**：已交付文本会被相容更新撤回；计算复用与可见服务连续性不是同一义务；三个合法性判断需要联合协调；因子、原生、故障和持续状态实验分别检验效果与边界。

但还不能从第一页独立重建可执行的保留判据，也不能解释 headline credit 的具体服务收益。问题陈述比机制与指标更直观。最值得补的不是更多贡献或更多实验数字，而是一个运行时动作句和一个指标定义句。第一页已有一个可辨认的核心贡献；“We make three contributions”最好始终被理解为同一协调契约的定义、实现与检验，而不是三个并列研究故事。
