# v16 最终读者路径审阅

审阅对象为实际已编译的11页PDF（10页技术正文+1页参考文献），SHA256 `f87a5e96ccbd34b68b6278fd6d064a5f8420dbb5a2558f597ecee3aa84ef55cf`。读取全部正文抽取，并视觉查看第1、2、7、8、9、10页。未修改稿件、运行编译/格式门、查网补引文或开展实验。此PDF是第一编译版本；Root随后已修改的source与待出的第二版PDF在下面分别标明。

## 总体判断

读者路径已经成立：2.176秒实测缺口→递归反馈依赖与三种实际使用→工作中的联合协议/可靠执行→24人组合机制→N8同原任务、同两完整FP32资源的Full/Ready主证据→竞争资源与已发表发布规则→实践结论。它读起来是一个有执行系统、协议动作和竞争实验的系统论文，已不是仅列三个谓词的提案。

N8表与图能够闭合主要承诺：93.9%对42.4%，10/16对0/16，223.215对322.991 occupied-worker秒，91.880对117.823两板kJ。工作时间没有被改称CUDA active time；能量图按offered audio归一，图注明确物理drain。主图也清楚区分前沿连续性和实际D+S修改。首2人pilot与后6人确认身份可见，重复没有当作额外声学样本。

## 必须修正：2项仍在当前source

1. **第7页V-C，原任务成功从“要求”改为“实际结果”，删除不存在的task-failure暗示。** 当前source仍写“Every run is required to match ...; the table retains task failures and deadline misses”，但表注及最终记录是32场全部通过完整state/C/U/IDs一致性。建议直接写：`All 32 runs match the original full states, corrections, and returned IDs; every offered interval and deadline miss remains in the denominator.` 这既增强实证表达，也避免读者以为表里有未通过原任务的运行。

2. **第7页V-C末，旧Conservative八人银行不可被“independently”误读为额外独立来源。** 当前source写“An earlier eight-speaker Conservative comparison independently preserves ...”。它复用同一既有八位说话人，只有runtime/比较身份不同。建议写：`An earlier Conservative comparison on the same speaker bank preserves the original task and final CER of 13.22%; its older runtime and endpoints remain separate historical support.` 不需要新增数据或更多限制段。

## 第一版PDF发现、Root已在source修正：无需重复修

- 第7页V-C的“zero realized [Ready-only] hits”若指N8会错：最终Ready确有3次真实complete-result reuse。Root已将主比较改为3次，零只留给V-D明确限定的两人pilot。
- 第一版引言native预览只有定性。Root已加入93.9%/42.4%及30.9%占用时间、22.0%能量主句。这正好把引言系统承诺接到表III，无须再堆更多数字。
- 图3caption和native表caption已有Root修订，等待统一第二次编译即可。本审阅不据旧渲染要求再改一次。

## 可选：2项文字收束

1. **把共同version-DAG解释尽量写成肯定句。** 现在p1、V-D、Related/Discussion多处用“不证明普遍等效/不是独占收益”等否定句。保留V-D一次精确范围说明即可；引言可用 `This supplies two implementations of the same complete-input lifetime contract.` 代替“their agreement does not remove these common conditions”。不删共享C1/input/retain/AU/SUP的实质，不把Vdag当作只查松散版本号。

2. **结论最后一句可更具体，避免被读成预测执行前已确认实际父输入。** `validate ... at execution, selection, and consumption`可以理解为角色内检查，但前文允许UNKNOWN输入先运行。可改为：`Safe reuse starts by freezing a call's input, then separately authorizes its original result and the whole view retained by the Consumer.` 这把实践结论接到实际动作，且减少再次列抽象权限的感觉。

## 无需扩张修改的部分

- Vdag说明准确：它共享核心完整输入与合法在途保留/原选择/SUP，仅额外ancestor fence在pilot无分歧；没有把全机制因此判死，也没有制造Full独有EL胜利。
- LA2-CP清楚标为AlignAtt kernel之上、固定计算schedule的只读发布规则；保留历史LA2/3位置，并明确不冒充Whisper-Streaming原生全系统/吞吐复现。这里的必要合同边界不是应一概删除的“防御性赘语”。
- 多会话结果直陈信用低、4会话零conditional分配以及全部D2失败，符合资源机会解释，没有把同步过载结果变成通用容量结论。
- 图1明确两次不同交错、interval级截止，不能被误读为whole-run通过或event-matched因果反事实。
- 实现/正确性部分给出动作、durable-before-install、真实Consumer与物理所有权，支持系统贡献；结论仍落到保持原程序任务，而不是自评创新或录用概率。

建议Root只处理上述两个现存语义句与已知source补丁，完成第二次统一编译后交付；不需要新实验、新引文或额外研究分支。
