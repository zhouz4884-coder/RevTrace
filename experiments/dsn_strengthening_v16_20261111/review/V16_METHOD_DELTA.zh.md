# v16合同/方法改写与claim–evidence map

写作位置：`C:/Users/LENOVO/.codex/worktrees/revtrace-dsn-v16-writing/RevTrace/Paper_DSN/revisions/20261111_dsn2027_release_v16/`。本任务只改`sections/02_contract.tex`、新增`sections/03_design_v16.tex`；没有改main/bib/其它章节/图片，Root负责合并includes、编译与视觉核验。使用`latex-paper-en`的section-writing模块及唯一method guide；无新实验、测试、模型或memory写入。

## 章节目标与骨架

目标：让第一次读稿的人按一个真实完整call、一个实际selected parent和一个当前whole view理解“合法工作如何留下来”，再看动作守卫如何保证它没有越过原程序。

* Section2先定义原反馈程序、closed cut、冻结call、typed forecast/full node、selected fact及真实whole view，再给实际Owner/两full worker/FIFO Consumer/WAL与故障模型。
* Section3按call continuation→原result/current parent串行join→同步/安装→Consumer whole-view reconciliation组织；EL/AU/SUP是不同用途，非三套独立物理证书。
* 精化命题从输入/result/parent/WAL guards建立归纳项；installed是verified durable prefix，含合法sync/install gap；不假设所有newfact已经legal再重述。
* 原35控件中A/B/C/D的state-convergence case进入方法解释：Bfull buffer先释放worker、Cbirth仍旧，A否定B输入，D以原程序重算到C冻结start，C才被确认/选中。selected chain无洞、不回滚；这只是有限协议案例。

## 主要修改

`02_contract`保留`eq:canonical`和`eq:node`，为node增加明确type；避免把早期ASR projection与完整original C/U混称complete result。F写为selected state/input frontier，另说明buffer-only不自动获得neural-processing credit，避免将state advance、visible text与模型工作混同。故障边界以真实native Owner-group/worker crash-stop、late/duplicate/fencedincarnation、幸存Supervisor/Consumer/intactFS表述；host receipt不被写成GPU arithmetic/Byzantine保证。

`03_design_v16`替代旧five-part03 include，保留`fig:protocol`、`tab:decision_objects`、`tab:coordinator`、`eq:edge`、`prop:refinement`、`prop:continuity`、`subsec:native_full_calls`、`subsec:native_refinement`。协议图由Section2移到方法，旧图文件未改；新caption不增加实测时间含义。仅两条紧凑propositions，去掉单独rerooting proposition及反复定义，避免“充分条件堆叠”遮住系统动作。

原`prop:rebase`只在已不再包含的legacy03内部被引用；未为不存在的第三命题保留虚假编号。最后静态核对时，Root已将main中的五条legacy03输入替换为唯一`sections/03_design_v16`；legacy文件保留但不参与编译。原程序关系`A,X`在Section2先定义，SUP命题前提明确指本次incoming selected fact，避免误用旧root的支持关系。

## Claim–evidence map

| 正文主张 | 对应证据 | 状态与边界 |
|---|---|---|
| 完整call input可pending，祖先失配不直接refute未来start | NNde09 FullSpec `_reason`/witnesses；aa9db5既有`unknown_future_input_survives_ancestor_loss_then_converges` | 支持条件性协议能力；不称pilot自然出现ancestor分歧 |
| 原ASR forecast不是原C结果，必须完整C/U后join实际parent | CandidateBridge typed forecast+FullSpec.complete+Resilient._commit+FactStore.validate | 已有source/controls/actualreceipt对应；忠实原worker/完整state声明为前提，不作GPU算术证明 |
| 每个selected edge由守卫建立且sync先于install | 14ae/de09共享AU/WALguards；aa9db5 state/action checks | 条件性动作归纳；unknown callback冻结新写；不假设installed始终tail |
| 同步后install前crash是合法prefix gap | aa9db5原27的post_sync_preinstall控制+新增phase controls | 既有有限CPU证据，不是本文新run；replay不增加原神经边 |
| view支持独立，compatible应用可保留whole tip | actualConsumer/Reconciler、原continuity negative control、独立source/trace绑定器 | per-application；不称全局文字单调/Consumer-render crash保证 |
| already-owned fullbuffer可在worker-only fence后保留原身份 | Resilient.worker_lost/replace_worker；已封存通道与buffer fixtures | 不推广为Owner epoch间adoption；Owner-group只replay durablefacts |
| 版本可绑定完整input，safeUIR可defer end-use验证 | 强DependencyVersioned继承FullSpec fullcut分类；UIR只抑制hint | 不称三独立证据/全局最小性，不构造“立即discard或unsafe use”的无逃逸两难 |
| state-convergence可产生contiguous chain中的birth-parent gap2 | 既有aa9db5 T58–70；A0/B1/C2/D3动作见理论audit | 有限符号原允许关系见证，非当前NN3自然率/独占速度证明；test本身未执行Consumer应用 |
| 有限检查不是whole-program refinement | 6231/14074 states、depth12、2144/2828 cutoffs、35=27+8 controls | counts均来自正式旧冻结记录；不把27再加到35，不给无限覆盖率 |
| spec recovery与实际survivingConsumer仍有映射缺口 | F.recover清provisional vs actualbegin_owner保留readview | 正文明示，实际applications另由source controls/trace audits验证 |

## 未纳入的主张

没有纳入外部divergence四文件的“连续链强迫gap1”“无withdrawal故无ancestorrefutation”“旧69秒全被丢弃”“Vdagtie验证定理”或制造frontier洞提案。外部文件未冻结身份/全输入/环境/运行/gate闭环，详见`ADVICE_THEORY_AND_DIVERGENCE_AUDIT_v1`。亦未把coarse-observation信息引理提升为全局必要性：safe retain/defer/AU与input-bound versions均保留。

没有新增某个“65 tests”数：当前确证的formal数量为35含原27；closed源码另有各自protocol CPU/trace evidence，NN3 manifest是66文件而非65测试。Root若需给源级控制精确总数，应从其对应closed gate核对后填写，不能与formal数量相加。

## 自审与交接

对象先于缩写；每个动作说明输入/输出、动机与安全作用；保留已有citation keys`vu2026streamcorrect`、`schneider1990statemachine`、`abadi1991refinement`，没有新增未核对引用。新算法用现有tabular/booktabs，不引入额外LaTeX包。仅做静态源阅读/标签检查，没有编译或新科学检查；页数、float位置、表格换行与全稿交叉引用由Root统一编译检查。若需要压篇幅，优先精简重复叙述，不删除source/fault/proof端点。
