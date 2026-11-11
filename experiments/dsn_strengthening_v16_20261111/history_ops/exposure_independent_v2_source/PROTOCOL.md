# v2：已显示后修改的字符秒与稳定前缀时间曲线

状态：2026-11-11已作者化纯函数与6项控制，**尚未冻结、测试或正式执行**。等待Root纳入计划，不修改v1两个已冻结source、配置、结果或CURRENT。

## 输入与实验合同

新CPU ID建议 `REVTRACE-V16-EXPOSURE-STABLE-PREFIX-20261111-V2`，另有独立核对ID。新source须独立commit/fullmanifest/bundle、root可解析ref、默认4f noarg预检。新config/env/prelaunch各自记录完整SHA、8TB原始路径、summary和gate，禁止拿v1 source commit为新代码贴标签。

冻结同一29格：native旧正式12与witness2分开；H3五臂×三cohort15格分开。每格原actualConsumer路径/hash与schema、session_source_map来自v1冻结config；每格v1 `EDIT_AND_LCP_OCCURRENCE_LIFETIMES.json` 和事件ledger另逐SHA绑定。输入仍在8TB。所有完整曲线、字符身份和大ledger留8TB；只取回有界source/arm/stage/convention汇总和必要示例。

## 指标1：已显示后修改的字符秒

对v1两条完整最优对齐身份历史分别计算：

`E_modified = Σ_{D/S关闭身份} (实际关闭时刻 − 实际首次出现时刻)`。

单位为Unicode码点×墙钟秒，D与S分别可列；一个码点出现后被改写多次，各次版本身份分别计数。两种tie-break分别完整报告，不取较好值。LCP后缀身份另算、另命名，不和真正D/S身份混合。它是**实际Consumer曝光的测量代理**，不是经验证的人类阅读时间、认知负担、感知闪烁或用户满意度。

右删失单列：每个同源最后实际观察时刻T仍可见身份的数量，以及 `Σ(T − birth)` 的已观察字符秒。它们尚未观察到修改，不能放进E_modified，也不能假定未来永不修改或把寿命延长到进程退出/假想UI关闭。

独立守恒：已关闭身份字符秒＋幸存身份已观察字符秒，必须等于实际文字长度阶梯曲线的面积 `Σ len(h_i)·(t_{i+1}−t_i)`。这对两条最优对齐历史和LCP身份都成立。它能发现漏掉首段、时间排序或生命周期账本错误。

## 指标2：回看稳定前缀曲线

在每个source/mode的实际顺序 `h_0,...,h_n`，冻结 horizon `T=t_n`，定义

`p_i = LCP(h_i,h_{i+1},...,h_n)`。

逐实际Consumer行输出：原行号、原实际clock、相对该source首次实际观察的秒数、当前文字长度、到T不再改变的前缀长度、其余suffix长度、到下次实际观察的阶梯持续时间及到T的剩余观察长度。不得排序制造新的时钟，不以CPU重放clock替代；raw和仅去Unicode空白分别输出。

这条曲线仅事后可知，不是在线稳定性证书、准确率或新部署收益。T之后未知。末行“全部前缀稳定”在冻结horizon下为真，但持续时间为零、信息受删失，图和表必须显式标记，不能拿终点高值宣传最终稳定。不同策略T各为自己同源最后实际观察；不补齐到较慢策略的T。跨source可汇总session-codepoint-seconds，但不表示某个用户同时阅读全部会话。

原始图建议保留实际阶梯：每source两策略/三策略面板，文字总长与回看稳定前缀同轴；并列E_modified、右删失字符秒和实际观察horizon。所有已有负结果、三cohort及witness身份保留，不能按曲线漂亮挑样。完整源数据CSV先验收，再按项目既有Python绘图流程冻结导出。

## 独立核对与门

准备源：`../history_metrics_v2_dev/exposure_curves.py`、`test_exposure_curves.py`。6项未执行控制覆盖未来修订限制前缀、字符秒/面积守恒、LCP/编辑分离、单行horizon删失、反向clock拒绝、错误面积拒绝。

正式执行前另写只做实际row/ledger适配的冻结driver；同时第二实现用逐时段当前视图长度积分、后续所有字符串逐一比较前缀，而非复用主函数。所有29格与两种文字口径、三个身份约定全量核对。即便E_modified使Joint显得更差也完整报告。

通过门：source/config/env/input前后字节不变；所有source原事件和horizon守恒；三种身份分别满足字符秒面积守恒；stable-prefix曲线单调且不超过当前文字长度；终点持续时间为0；完整分层未删格。失败保留原gate，按新source版本修复，不覆盖v1。
