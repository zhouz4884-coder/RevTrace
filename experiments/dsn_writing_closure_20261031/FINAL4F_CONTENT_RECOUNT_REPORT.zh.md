# 最终 4f 已有20 trial内容与可见性补算：完成

正式 gate：`PASS_COMPLETE20_CPU_CONTENT_EXACT_G_AND_DEPENDENCY_CONTINUITY`。一次完整只读 CPU 扫描完成20个既有trial、32个request-instance、544个原选定durable转移和1604条实际Consumer应用。新NN调用0、模型初始化0；这不是新增GPU实验。正式Linux反例控制15/15、零skip，之后才执行完整扫描。

## 可直接写入论文的对照

每行组均含4条既有声学来源×2次重复，每臂8个请求实例，offered音频66.33975秒、136个前沿，包含原EOS；matched每臂8独立trial，resident每臂2常驻trial。重复不增加独立声学来源。

| 原运行分层 / 臂 | 原D2/C8通过 | 原双期限前沿信用 / s | 首次实际G全文事后支持信用 / s | 失配信用 / s | 未知信用 / s | 引入 / 撤回 / 末次仍可见 code-point occurrences |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| matched Conservative | 0/8 | 30.0 | 22.5 | 7.5 | 0 | 180 / 14 / 166 |
| matched Full-call | 6/8 | 65.821625 | 51.0 | 14.821625 | 0 | 180 / 14 / 166 |
| resident Conservative | 0/8 | 31.0 | 24.0 | 7.0 | 0 | 180 / 14 / 166 |
| resident Full-call | 7/8 | 64.118875 | 50.2590625 | 13.8598125 | 0 | 180 / 14 / 166 |

raw与whitespace-stripped结果一致。matched既有完整字段逐cell与原SUMMARY独立重算完全守恒，没有重复神经推理。resident新增内容数字使用每个sid自己的REQUEST_ORIGINS/ledger起点，完整保留原500ms、EOS、全部offered与失败请求；不能把后续请求接到trial的首次起点。

全部offered前沿的supported/mismatching计数，两类分层中均为Conservative **106/30**、Full-call **104/32**，各分母136，unknown=0。因此更高的“及时且事后全文相等的前沿信用”并不意味着临时全文总体匹配率提高，也不意味着新增文字变多。14次撤回是Unicode code-point出现次数，并非14个音频前沿或14次视图撤回。

建议主文用语：**“On the final implementation, timely frontier credit whose whole first view agrees retrospectively with the selected text at that view’s actual frontier rises from 22.5 to 51.0 seconds; introduced and retracted code-point occurrences remain equal across arms. The resident trials show the same distinction, with supported credit of 24.0 versus 50.259 seconds.”** 它不是人工文字正确率、在线G认证、token/音频对齐吞吐或生产可用率。早期bdfa的29.0→51.518125秒不能迁入最终4f表格。

## 连续可用性的实测分母

先用原c4 checker验证每个完整调用回执、durable frame、publication与实际Consumer快照，再按完整cut与依赖链重建可见对象；不是以最终文字相同替代因果合法性。

| 分层 / 臂 | compatible-ahead完整机会 / 实际保留 | 其中非空实际view | 必要不兼容撤回 | 错误兼容撤回 | 未知依赖事件 |
| --- | ---: | ---: | ---: | ---: | ---: |
| matched Conservative | 0 / 0 | 0 | 0 | 0 | 0 |
| matched Full-call | 0 / 0 | 0 | 2 | 0 | 0 |
| resident Conservative | 0 / 0 | 0 | 0 | 0 | 0 |
| resident Full-call | 1 / 1 | 1 | 2 | 0 | 0 |

matched中的compatible分母为0，不能写“100%保留”或用它验证兼容保留能力。resident仅有1次非空compatible-ahead更新，实际保留原tip和job身份；它是一个有限实机见证，不估计总体保留率或自然发生率。F旧actual36的90/90另属于其原轨迹分母，不能加到这一批里。

唯一见证位于 `SC_RESIDENT4_V2_fullcall_r0` 的 `BAC009S0905W0246`：实际Consumer row24首次显示完整tip frontier80000（5秒音频），row25安装兼容Canonical frontier72000（4.5秒）时，前后完整tip SHA均为 `b5bdce77911264f787b9954a9d0b290c02d76844cf4f1ec877bd74dd3b241ae0`，原 `e0-j000000011` 保留。该非空12-code-point对象从perf **5185848.456899025** 保持到 **5185849.273758644**，跨过兼容更新perf **5185848.563842505**，完整连续观察区间 **0.816859619691968秒**；row29因合法supersession结束，该区间本身未被右删失。它不是“避免了0.817秒宕机”或新期限信用。

所有间隔只覆盖同源连续实际Consumer应用之间的逻辑快照保持；末尾对象在**最后实际同源观察**右删失，不延长到SERVICE_END、下个请求或假想浏览器关闭。空text而内部tip ahead的对象单独计数；本批compatible事件中的empty-tip为0。unknown依赖为0是完整重建通过后的结果；缺路径会FAIL，缺少G的Canonical文字会unknown，均不会补0。物理浏览器、网络可达性与人工正确性不在此观测中。

## 完整方法、身份与门

实际CPU分析source：`6eb6639478a87e6be971e23282bd2f31789f242f`；完整20文件manifest SHA256 `2dac41b61a84c5de8846564bdcb7c7c6bd8159e51b35012f385c6e781282637c`。原NN执行source仍为 `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`；resident controller仍为a13。GitHub archive441、CPU commit和NN commit未混用。

新源按字节vendor了4f内容/metrics/storage、c4结构checker和a13的resident clock/endpoint等12个实际消费依赖；完整文件SHA和原commit在 `content_source_v4/DEPENDENCIES.json`。这些原模块未改；新增adapter只将每个resident sid接到自己的原时钟。主reader采用原LCP出现次数函数和原posterior first-G函数；支持分类取第一条满足目标F的实际显示行自己的G，并把整段text与选定Canonical `(sid,G)` 全文比较，不以F、最终history/低CER代替。

正式experiment IDs：`SC_FINAL4F_EXISTING20_CONTENT_CONTROLS_V4` 与 `SC_FINAL4F_EXISTING20_CONTENT_COMPLETE20_V4`。Frozen config SHA分别为 `26c1a720cfd937c344e1af129679cabf3129631a1c75ae7c47f4e3fda17d1306` / `5c8b1933fb9734170740468ec342ff8238686b5005771e31a139b011ab71783f`；实际CPU环境 SHA `20754f9b6698153792f6ebe14538172f0da2b7980d8b249b9b6aecee733ffbec`。Python为8TB环境中的3.12.13，CUDA_VISIBLE_DEVICES明确为空；未导入模型/神经runtime模块。

330个指定输入（含两份完整原RAW_INDEX）共 **131134574 bytes**；全白名单逐字节SHA在扫描前后相同，`INPUT_HASHES_BEFORE/AFTER.json` 均为 `c5bfc93224c758371c138734b7a78e1201950c92438634d5d175685f6193ff9c`。config/env/rootgate/manifest也显式前后相同，`CONTROL_HASHES_BEFORE/AFTER.json` 均为 `9a8f8e2d9a9c9249aefdbb5cebabf9354e956133ed894a14553d36bbf6e75f5d`。source在执行前后均clean且完整manifest匹配。

Root真实CURRENT/noarg v4通过后，本地两份prelaunch record还分别得到 `run_record_prelaunch_checked=true`；远端实际config/env、原raw白名单、stdout/stderr、summary/gate路径在任何CLI前冻结。实际CLI先controls再complete20，二者exit0。输出目录独占、不覆盖，原raw和原summary/gate未改。

正式输出仅在指定8TB：

- `/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_writing_closure_20261031/content_cpu_controls_v4`
- `/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_writing_closure_20261031/final4f_existing20_content_cpu_v4`

本地仅收集 **3054652 bytes** 的有界结果与元数据，位于 `CONTENT_CPU_V4_RESULTS`；每文件远端/本地长度和SHA在 `COLLECTION_INDEX.json` 对照通过，没有搬回原raw。正式complete20 `SUMMARY.json` SHA为 `a3c9292ecccebc3660870e181e491d1d41d778941827b51cffa5914f64a26e33`，`GATE.json` SHA为 `812c8ae8d2614f5ac42573ce3b892ae90789cc84f3ac22266922d3e36bd28ee8`。

收集时GPU compute owners为空，两个CPU experiment lease已释放；Root已恢复4f CURRENT，`ROOT_NOARG_FINAL4F_RESTORED.json` 真实通过原59文件source预检。本agent没有修改CURRENT。独立QA只读本地有界包，不做第二次全raw扫描。

**独立最终QA已通过。** `CONTENT_READER_INDEPENDENT_REVIEW_v1.zh.md` 的正式结果附录核对38个有界文件全部长度/SHA、20/32/544覆盖、330个输入与4个控制文件前后同值、逐请求first-G分桶和端点守恒；1604条实际Consumer行对应1572个同源观察区间、676个完整tip segment和32个末段右删失。唯一compatible非空segment及全部4次必要不兼容撤回均跨事件、逐trial和group汇总相符。QA没有第二次访问远端raw或运行NN。

## 保留的开发/阶段问题

开发期两个RAM fixture错误（raw/ws spans双计数断言、Windows内存路径分隔符）保留。v2补空tip/非空view分母，v3补控制文件前后SHA，v4修正实际CURRENT分析源与原NN4f分离；v1–v3没有被用作最终正式扫描身份。正式前SFTP `xb`写标志错误留下空bundle文件，改用exclusive `wx`和新UPLOAD1文件名，旧空文件未删除或覆盖；环境本地镜像最初CRLF哈希不符，保留后另建byte-exact LF镜像。以上均发生在正式CLI前，无原raw变动、无新增NN，不改变科学端点。
