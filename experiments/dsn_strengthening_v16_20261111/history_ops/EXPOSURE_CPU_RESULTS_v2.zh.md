# 已展示后修改的字符秒、稳定前缀与最终全文核验

2026-11-11。正式v2主分析和独立实现均完整PASS，各6项控制、零skip，覆盖同一29格全部实际Consumer；零新GPU。本报告不修改v1冻结文件，不把曝光代理写成人类体验证据。

**H3主分层的正向补强：** 只保留计算R10到Joint的实际最优身份D/S修改数267→49（−81.65%）；已展示后再修改的码点秒203.297→134.207（−33.985%）。另一完整对齐规则为266→48及276.509→208.373码点秒（−24.642%）。原期限信用同时增加16.610秒。新全文逐source/逐臂hash核验也通过，最终actualConsumer原文相同，不再只是总长度或WER相同。

## 1. 精确定义与边界

修改曝光量为每个实际D或S关闭身份的 `关闭实际时刻−首次出现实际时刻` 之和，单位Unicode码点×墙钟秒。它随最优对齐身份约定变化，故两条完整规则分别保留。LCP后缀身份另列。右删失幸存身份的数量和已观察字符秒单列，不算入已修改曝光，不推测T之后的命运。

每source/mode的horizon T为该source最后一次实际Consumer观察。回看稳定前缀为 `LCP(当前文字, 此后所有实际文字直到T)`；输出实际时钟、距首次实际观察的时间、前缀长度、当前全文长度、volatile suffix及下一实际事件的阶梯时长。它只能事后得知，终点“全部稳定”在有限horizon下是空泛成立，其持续时间明确为0；T之后未知。没有补齐到较慢策略的horizon，没有CPU重放时钟或新期限信用。

主实现用反向LCP递推；独立实现逐个当前view对比所有未来view。独立字符秒从原birth/close/censor绝对时钟重新相减，再对实际文本长度逐时间段积分。888个source/mode/identity组全部满足：**已关闭身份字符秒＋右删失幸存身份字符秒＝实际全文长度阶梯面积。**

## 2. H3完整五臂，raw口径

| 臂 | D/S关闭身份（主/第二规则） | 修改曝光码点秒（主/第二） | LCP关闭曝光码点秒 | 右删失幸存已观察码点秒（主规则） |
|---|---:|---:|---:|---:|
| R00 |150/149|175.635 /247.988|1173.214|171431.499|
| R01 |49/48|135.565 /209.206|1116.717|171424.985|
| R10 |267/266|203.297 /276.509|1178.977|170012.008|
| R11 |49/48|134.207 /208.373|1138.541|173305.418|
| Standard |49/48|130.894 /204.093|1103.344|170386.981|

R00→R10使中间修改数与曝光都增加，R10→Joint两种规则均改善；这加强了“只保留计算会产生更多需再协调的中间内容”这一观察。但R01在修改数上已与Joint相同，曝光也接近，不能说两个因素对低修改量都必要。Joint的论点仍是及时性与连续性联合目标。

| 臂 | 回看稳定前缀阶梯面积 /码点秒 | 观察horizon总和 /source秒 |
|---|---:|---:|
| R00 |170433.920|820.207|
| R01 |170443.833|820.609|
| R10 |169036.328|816.840|
| R11 |172301.085|822.858|
| Standard |169414.531|816.522|

horizon总和是24个source窗口之和，不是一个用户阅读时间或一次episode墙钟。窗口长短与更早显示都会影响面积，不能把较大稳定前缀面积直接当吞吐提升。本账本的volatile-suffix面积等于LCP关闭身份曝光字符秒，符合两种定义的关系；它不是第二份独立样本或独立效应复现。

## 3. Native正式12保留相反代价

| 臂 | D/S修改曝光码点秒（主/第二规则） | LCP关闭曝光码点秒 | 右删失幸存已观察码点秒（主规则） |
|---|---:|---:|---:|
| Sequential |0 /0|0|1067.830|
| Drop |13.423 /12.267|13.964|2274.052|
| Joint |82.027 /82.027|89.612|2807.536|

较早展示更多临时内容可以付出更多实际修改曝光；不能只报H3的改善隐藏本表。原始期限结果、EOS及质量未改变。这是已观察文字活动的测量代理，不是用户真的阅读了82秒文字、认知负担增加82秒或已经有用户感知评估。开发Joint两witness另41.791码点秒（主/第二规则相同），LCP45.714，未混入正式表。

## 4. 最终actualConsumer全文确实逐source相同

本轮直接取每source最后实际Consumer的literal text，按UTF-8字节计算SHA256，逐source比较所有arm和旧native重复；没有从10575总长度、最终WER或Canonical历史相同推断显示全文相同。

- H3：24source×raw/去空白两口径＝48组，每组实际五臂完整；120条原末次观察各生成两口径共240个hash，48/48组全文hash相同，不增加独立观察数。
- native正式：4source×两口径＝8组，每组3臂×2重复；8/8全文hash相同。
- witness单臂另8组，保留但不当跨臂检验。

合计64组、其中56跨臂组，**不相同组0**。独立实现重新从原Consumer字节提取并验证全部hash。逐cell末次时钟、最终长度和hash在 `results/EXPOSURE_v2/FINAL_ACTUAL_TEXT_HASH_GROUPS.json`。

## 5. 曲线与证据文件

`results/EXPOSURE_v2/STABLE_PREFIX_CURVES.csv` 给出全部8,692个source/mode曲线行，对应4,346条原Consumer观察各两种文字口径，不能当8,692个独立样本。字段包含原cell/source/arm/cohort/repeat、原行号、原绝对时钟、相对首次观察时间、剩余horizon、全文/稳定前缀/volatile suffix长度和终点零时长标记。完整per-cell JSON留在8TB。图应使用实际阶梯与上述horizon标记，不能只连接终点或把终点全长当稳定认证。

逐source888个身份组在 `SOURCE_EXPOSURES.json`；全分层两对齐规则与LCP独立汇总在 `AGGREGATES.json`。这些全量数据适合后续固定绘图，不需要再读模型或新增服务运行。

## 6. 实际身份、SHA与资源闭合

| 项目 | 主分析 | 独立实现 |
|---|---|---|
| 实验ID | REVTRACE-V16-EXPOSURE-20261111-V2 | REVTRACE-V16-EXPOSURE-INDEPENDENT-20261111-V2 |
| 实际source commit | `fc096beb19c394e0637bb5d1dcb477ba97704236` | `52352a05fefc1fe8693eb67d7b158e309f62e706` |
| source manifest SHA256 | `48761e0cbe0d97ac47b03e6085d43c0b8e2da536d5fbdb19ba78db645cfe47e8` | `8baeaf2dc4524c6c1b6bd2c60be1f4b0e6ee63e43bf6b4f6c9e7024f20556300` |
| source bundle SHA256 | `f3040f6d71a72d5bfebf367b32abd8f4c51731b39034fe25b34ba71f595f36c1` | `e99c77089c2ae7adc756c1735d7770bd611577fbfed7772e1411852c1ad6c9b0` |
| 冻结config SHA256 | `fc45c678d6d26f473810eca47eae80e4a506787ea97ed35a6b4ed3ead2db06d9` | `bf10a29795991a6e482e8d04dd23b99e2f535e4b2d0af30df3e80d8d46b182f0` |
| environment SHA256 | `2bb763bc4e72fcecafdbd1f80a7313195cc9dec1bccf75e62ad2cd32ae897a82` |同左|
| SUMMARY SHA256 | `ec03602775216c49cc814c86c12fbf4eea3ff4e94bcbd1bbb7eb7ebe8450dba7` | `b9770e8d4e465db8a95b9f209af855cf77b6fb394f86ada86680ea3f2a456ac0` |
| GATE SHA256 | `a5380f8537b715964e38a9885a4753ce87048b6a7f57245214e350e25c8c5b94` | `d62782dbbd813acd70f14fe6ba0cefa9e44a20fc24701fc53eda73fd3f9c478d` |

数据文件SHA256：AGGREGATES `2773f18e9646b5f885515fa3e5b1c2323b022e0d563e881671224c22e6421b00`；SOURCE_EXPOSURES `0a9f2b82b26619fba455a07b7b0930fdbb26efa6da04f8152dda506595b6c87b`；FINAL_ACTUAL_TEXT_HASH_GROUPS `f54f8e714a81aa5f570b1c8c5f6edcecca232febe610ec68e3c1d10003a57d6d`；CURVES.csv `52f32b651dde7ae3fbff2b5054d10173f46c5dc8eae416cf256f90a780b35ce9`。

原始结果在8TB `.../results/revtrace/dsn_strengthening_v16_20261111/{exposure_v2,exposure_independent_v2}`。取回有界主分析10文件3,051,837字节、独立7文件407,569字节，逐SHA相符；完整literal/身份大数据留8TB。

`FINAL_CPU_RESOURCE_CLOSURE.json` 于10:10:55 UTC记录本子任务五个CPU实验原PID generation全部已消失、CUDA compute owners为空；fresh默认noarg仍为NN4f，五个source最终显式预检均通过。没有信号终止任何进程。后续若Root激活GPU driver改变CURRENT，此处是闭合时快照，不替后续状态作保证。本子任务不再启动CPU运行，除非另行协调。
