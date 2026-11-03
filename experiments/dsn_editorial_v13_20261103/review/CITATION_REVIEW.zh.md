# RevTrace DSN v13：31项引用一手来源独立审计

审计ID：`REVTRACE-DSN-EDITORIAL-V13-CITATION-AUDIT-20261103`。日期：2026-11-03。基点为冻结v12的实际`main.bbl`、可达TeX与三份`.bib`；v13只记录当前引用键快照。本审计只写本目录两份审阅文件，未修改论文、图、实验或Git。

**结论：31/31身份可由当前一手来源核实；未发现虚构文献、作者/年份/venue错误，或把四项预印本冒充正式发表。**正文、bbl和三份bib的键集合一致，无重复/遗漏键。确认一处表述精度修订及三项书目呈现改进。完整作者、正式题名、年份/版本、出处、正文逐次位置和来源URL见`CITATION_MAPPING.json`。

## 可直接采用的四项小改动

1. **MVCC概括拆开。** v12相关工作92–95行把OCC与MVCC概括为共同分离validation/commit阶段。Bernstein–Goodman原文§4、§5分别讨论timestamping和locking等算法，MVCC范式并不统一采用OCC式末尾验证。建议：`Optimistic concurrency control validates concurrent work before commit; multiversion control manages reads across data versions, while snapshot isolation supplies a distinct transaction guarantee.` [原文§4–5](https://www.cs.cmu.edu/afs/cs.cmu.edu/academic/class/15712-f17/www/papers/bernstein83.pdf#page=11)。
2. **Qwen可定位性。** 当前`.bib`有`eprint=2601.21337`，但IEEEtran生成的bbl未显示编号或URL。加入明确[arXiv v2 URL](https://arxiv.org/abs/2601.21337v2)或把`arXiv:2601.21337`写入journal/note；无需改变2026年份。
3. **vLLM页码。** 为Kwon等补SOSP 2023的`611--626`。现有作者、题名、venue、年份正确。[出版方登记元数据](https://api.crossref.org/works/10.1145/3600006.3613165)。
4. **Whisper-Streaming条目类型。** 将`@article`及`journal`改为`@inproceedings`及`booktitle`，并可补[ACL官方URL](https://aclanthology.org/2023.ijcnlp-demo.3/)。现有题名、作者、2023年、17–24页正确。

## 最近邻的核验结论

- **SSBD**：所引v2为2026-01-04，v1为2025-09-26。§3.2–3.4确实联合旧输出draft重验和display-only mask；Table3有β=0。不能仅按有偏/普通离线token方法作弱比较。本文差异应落在完整已执行调用输入、原选择和实际整视图支持。[v2与机制](https://arxiv.org/html/2509.21740v2#S3.SS2)。
- **PredGen**：COLM2025官方接收页确认题名/作者；arXiv v2 §3/Algorithm1及App.B.2支持演进输入上的候选重验、文本和TTS预计算。Greedy、Top-K、reflection的语义不能混同。OpenReview验证页无法直接读取不构成引用错误。[接收身份](https://colmweb.org/2025/AcceptedPapers)，[机制](https://arxiv.org/html/2506.15556v2#S3)。
- **SGLang**：2024正式稿§5清楚描述忽略stop继续生成，保存额外输出并匹配后续primitive；现有API-speculation句子成立。不能只把它归为RadixAttention。[正式稿§5](https://proceedings.neurips.cc/paper_files/paper/2024/file/724be4472168f31ba1c9ac630f15dec8-Paper-Conference.pdf#page=6)。
- **StreamCorrect/RelayS2S**：ACL官方记录均为2026年10月。前者§3.1–3.2的纠错前缀确实进入后续识别；后者§2.4–2.5以learned verifier提交快路径前缀并约束慢路径续写。当前主要比较准确；不把本文受控适配配置归成原论文设置。[StreamCorrect](https://aclanthology.org/2026.emnlp-industry.142/)，[RelayS2S](https://aclanthology.org/2026.findings-emnlp.1201/)。
- **Retire/Alignment Drift**：分别确认`2610.01160v1`（2026-10-01）和`2608.12703v1`（2026-08-13），作者/题名匹配。Retire也协调publication authority、继承与回收，应按应用合同边界区分；Alignment Drift支持音频位置跟踪及成本的重要性。两项保持预印本身份。[Retire](https://arxiv.org/html/2610.01160v1#S5.SS1)，[Alignment Drift](https://arxiv.org/html/2608.12703v1#S4)。

“未在本文运行复现/原文未规定”均不等于“外部系统不能实现”。本审计不支持全SOTA性能排名或无前例声明。

## 全31项简短映射

下表按v12实际bbl顺序列出。正文精确位置与完整上下文在JSON逐项保存；表中机制是原论文/官方资源实际支持的对象。

|# / key|身份与状态|正文用途 → 原论文锚点|判断|
|---|---|---|---|
|1 `vu2026streamcorrect`|[Vu等，2026；会议](https://aclanthology.org/2026.emnlp-industry.142/)|选中的纠错会改变后续ASR输入；原生适配保留原纠错/更新。 → [§3.1–3.2; PDF pp.2393,2395](https://aclanthology.org/2026.emnlp-industry.142.pdf#page=3)|支持，保留范围|
|2 `schlangen2011incremental`|[Schlangen等，2011；期刊](https://aclanthology.org/2011.dnd-2.11/)|增量依赖/撤销基础，以及提交前沿与活动进展的区分。 → [§3.3.2–3.4.2; §5.2.2/Figs.12–13](https://aclanthology.org/2011.dnd-2.11.pdf#page=24)|支持，保留范围|
|3 `hammer2014adapton`|[Hammer等，2014；会议](https://doi.org/10.1145/2594291.2594324)|按依赖检查复用计算已有成熟基础。 → [§2–3.2; Figs.4,6](https://matthewhammer.org/adapton/adapton-pldi2014.pdf#page=4)|支持，保留范围|
|4 `hammer2015names`|[Hammer等，2015；会议](https://doi.org/10.1145/2814270.2814305)|Nominal Adapton结合名字、参数与依赖检查复用。 → [§4; §5.2 Implementing Reuse](https://arxiv.org/html/1503.07792v2#S5.SS2)|支持，保留范围|
|5 `zeng2026ssbd`|[Zeng等，2026；预印本](https://arxiv.org/abs/2509.21740v2)|SSBD协调旧输出draft复用和显示mask，并包含无偏配置。 → [§3.2–3.4; Table3 β=0; App.A.1](https://arxiv.org/html/2509.21740v2#S3.SS2)|支持，保留范围|
|6 `li2025predgen`|[Li等，2025；会议](https://colmweb.org/2025/AcceptedPapers)|不断变化的语音输入期间推测下游生成与TTS。 → [§3/Algorithm1; §3.1–3.5; App.B.2](https://arxiv.org/html/2506.15556v2#S3)|支持，保留范围|
|7 `schneider1990statemachine`|[Schneider等，1990；期刊](https://doi.org/10.1145/98163.98167)|把服务执行与有序命令关联的状态机背景。 → [§1 State Machines; §3.2 Order and Stability](https://www.cs.cornell.edu/fbs/publications/SMSurvey.pdf#page=2)|支持，保留范围|
|8 `abadi1991refinement`|[Abadi等，1991；期刊](https://doi.org/10.1016/0304-3975(91)90224-P)|删除推测、等待、重复交付等步骤的受限投影采用stuttering观点。 → [§1.1; §2/Refinement mapping R3; author technical report](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/abadi-existence.pdf#page=7)|支持，保留范围|
|9 `mohan1992aries`|[Mohan等，1992；期刊](https://doi.org/10.1145/128765.128770)|write-ahead recovery作为持久化、重放与身份记录的常规基础。 → [原论文title/abstract; WAL与LSN/restart recovery](https://people.eecs.berkeley.edu/~brewer/cs262/Aries2.pdf#page=1)|支持，保留范围|
|10 `birrell1984rpc`|[Birrell等，1984；期刊](https://www.microsoft.com/en-us/research/publication/implementing-remote-procedure-calls/)|Owner/issue编号与worker incarnation采用RPC身份原则。 → [§2.3; §3.2 Simple Calls, pp.50–51](https://web.eecs.umich.edu/~mosharaf/Readings/RPC.pdf#page=12)|支持，保留范围|
|11 `shi2026qwen3asr`|[Shi等，2026；预印本](https://arxiv.org/abs/2601.21337v2)|主实验使用Qwen3-ASR 1.7B这一模型身份。 → [abstract/model-family description](https://arxiv.org/abs/2601.21337v2)|书目呈现改进|
|12 `radford2023whisper`|[Radford等，2023；会议](https://proceedings.mlr.press/v202/radford23a.html)|第二状态适配器使用Whisper base.en。 → [official proceedings abstract; model family](https://proceedings.mlr.press/v202/radford23a.html)|支持，保留范围|
|13 `panayotov2015librispeech`|[Panayotov等，2015；会议](https://doi.org/10.1109/ICASSP.2015.7178964)|独立确认来源来自LibriSpeech。 → [official corpus description/OpenSLR12](https://www.openslr.org/12/)|支持，保留范围|
|14 `bu2017aishell`|[Bu等，2017；会议](https://doi.org/10.1109/ICSDA.2017.8384449)|八名此前未用AISHELL-1 test speaker来源身份。 → [official corpus description/OpenSLR33](https://openslr.org/33/)|支持，保留范围|
|15 `mcsherry2013differential`|[McSherry等，2013；会议](https://www.microsoft.com/en-us/research/publication/differential-dataflow/)|跨演进版本维护增量计算已有系统基础。 → [§3.1–3.4; §4](https://www.cidrdb.org/cidr2013/Papers/CIDR13_Paper111.pdf#page=3)|支持，保留范围|
|16 `machacek2023whisperstreaming`|[Macháček等，2023；会议](https://aclanthology.org/2023.ijcnlp-demo.3/)|Whisper-Streaming通过LocalAgreement转为增量服务。 → [§3; LocalAgreement](https://aclanthology.org/2023.ijcnlp-demo.3.pdf#page=2)|书目呈现改进|
|17 `mai2026relays2s`|[Mai等，2026；会议](https://aclanthology.org/2026.findings-emnlp.1201/)|learned verifier提交fast-path prefix并约束后续slow path。 → [§2.4 Prefix Verifier; §2.5 Slow Path](https://aclanthology.org/2026.findings-emnlp.1201.pdf#page=4)|支持，保留范围|
|18 `wang2026alignmentdrift`|[Wang等，2026；预印本](https://arxiv.org/abs/2608.12703v1)|音频位置状态的重要性与成本。 → [§4 Alignment Drift; §5 Correction and Cost](https://arxiv.org/html/2608.12703v1#S4)|支持，保留范围|
|19 `yu2022orca`|[Yu等，2022；会议](https://www.usenix.org/conference/osdi22/presentation/yu)|Orca处理iteration-level transformer scheduling。 → [official abstract; iteration-level scheduling/selective batching](https://www.usenix.org/conference/osdi22/presentation/yu)|支持，保留范围|
|20 `kwon2023pagedattention`|[Kwon等，2023；会议](https://doi.org/10.1145/3600006.3613165)|vLLM在请求内外共享KV块。 → [§4.1–4.4; sharing/COW](https://arxiv.org/html/2309.06180#S4.SS4)|书目呈现改进|
|21 `zheng2024sglang`|[Zheng等，2024；会议](https://proceedings.neurips.cc/paper_files/paper/2024/hash/724be4472168f31ba1c9ac630f15dec8-Abstract-Conference.html)|两句分别描述RadixAttention和API speculation。 → [published §3 RadixAttention; §5 API Speculative Execution](https://proceedings.neurips.cc/paper_files/paper/2024/file/724be4472168f31ba1c9ac630f15dec8-Paper-Conference.pdf#page=6)|支持，保留范围|
|22 `leviathan2023speculative`|[Leviathan等，2023；会议](https://proceedings.mlr.press/v202/leviathan23a.html)|target模型验证draft且保持其输出分布。 → [official abstract; exact speculative sampling](https://proceedings.mlr.press/v202/leviathan23a.html)|支持，保留范围|
|23 `zhang2026retire`|[Zhang等，2026；预印本](https://arxiv.org/abs/2610.01160v1)|按runtime-supplied scopes/contracts执行revocation、state inheritance和reclamation。 → [§3.1; §5.1–5.3; App.A.1](https://arxiv.org/html/2610.01160v1#S5.SS1)|支持，保留范围|
|24 `kung1981occ`|[Kung等，1981；期刊](https://doi.org/10.1145/319566.319567)|并发执行与验证/提交分离的经典OCC基础。 → [§1–3; read/validation/write phases](https://people.eecs.berkeley.edu/~brewer/cs262/kung.pdf#page=3)|支持，保留范围|
|25 `bernstein1983mvcc`|[Bernstein等，1983；期刊](https://doi.org/10.1145/319996.319998)|MVCC与OCC一起作为并发状态管理背景。 → [§1; §4 timestamping; §5 locking; §6 mixed](https://www.cs.cmu.edu/afs/cs.cmu.edu/academic/class/15712-f17/www/papers/bernstein83.pdf#page=11)|拆开OCC/MVCC概括|
|26 `berenson1995isolation`|[Berenson等，1995；会议](https://doi.org/10.1145/223784.223785)|读快照不等于完整事务保证。 → [§4.2 Snapshot Isolation; §4.3 Other Multi-Version Systems](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-95-51.pdf#page=9)|支持，保留范围|
|27 `chandy1985snapshots`|[Chandy等，1985；期刊](https://doi.org/10.1145/214451.214456)|distributed snapshots捕获进程/channel状态。 → [§2 model; §3 snapshot algorithm](https://lamport.azurewebsites.net/pubs/chandy.pdf#page=7)|支持，保留范围|
|28 `zaharia2013dstreams`|[Zaharia等，2013；会议](https://doi.org/10.1145/2517349.2522737)|stream processing以lineage恢复状态。 → [§3 model; Fig.3/lineage recovery](https://people.eecs.berkeley.edu/~matei/papers/2013/sosp_spark_streaming.pdf#page=4)|支持，保留范围|
|29 `carbone2017flinkstate`|[Carbone等，2017；期刊](https://doi.org/10.14778/3137765.3137777)|stream processing以coordinated snapshots恢复状态。 → [§3.1 managed state; §3.2 snapshots; §3.3 recovery](https://www.vldb.org/pvldb/vol10/p1718-carbone.pdf#page=4)|支持，保留范围|
|30 `gray1989leases`|[Gray等，1989；会议](https://doi.org/10.1145/74850.74870)|time-bounded cache leases与terminal/drain式物理ownership区别。 → [§2 Leases and Cache Consistency](https://web.stanford.edu/class/cs240/readings/leases.pdf#page=1)|支持，保留范围|
|31 `welsh2001seda`|[Welsh等，2001；会议](https://doi.org/10.1145/502034.502057)|资格决定可保留，queue-based admission决定何时启动更多工作。 → [§3 architecture; resource controllers/load conditioning](https://people.eecs.berkeley.edu/~brewer/papers/SEDA-sosp.pdf#page=4)|支持，保留范围|

## 方法、访问限制与停止边界

先读已有有界近邻/书目审计，再用ACL、arXiv、COLM、NeurIPS、PMLR、USENIX、机构/作者原文、大学托管原论文和出版方登记Crossref元数据逐项核对。仅使用公开文献，不上传稿件。JSON对冻结输入和既有审计文件记录SHA-256，并把当前工作区HEAD标为上下文身份，不冒充任何实验execution commit。

已遇到并记录：OpenReview challenge；ACM403；部分作者PDF/Stanford PDF超时；Python默认TLS验证失败；一次Crossref429与NeurIPS初次超时。没有关闭证书验证或绕过挑战。可用替代原论文核实了RPC和经典并发机制；ARIES仅以原论文摘要/题名确认本段一般WAL背景，未重新通读全部恢复细节。这些访问限制不等于文献错误。

四项preprint为SSBD、Qwen3-ASR、Alignment Drift、Retire；没有在本次有界检查中确认其正式venue，不能把“未确认”写成“没有发表”。PredGen的COLM身份由官方接收页独立确认。Differential Dataflow保留官方CIDR2013身份；Abadi–Lamport保留1991 TCS发表版，较早技术报告/会议身份不应覆盖正式引用。

本轮未发现需要新GPU、模型、外部系统运行或实验重开的引用问题。完成条件是31项都具备可追溯身份、正文用途与原机制锚点；具体全程序证明/性能比较仍只由对应本地证据承担。
