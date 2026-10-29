# 原生完整调用确认16格：原服务端点与严格内容支持

**全部16格、276个offered前沿独立本地重计通过。** 每臂8次实际运行、66.42975s重复offered音频、138个前沿。完整推测的原D2/C8信用为66.29375s，保守完整执行为37.5s；按首次视图自身实际前沿G，与后来完整Canonical(G)文本严格相同的回顾性支持分别为56.287875s和33.5s。八个同source/repeat配对中，两种差值均为正，gross loss均为0。raw与仅去Unicode空白结果一致。

这是原4个development来源的fresh-process时序确认，不是新增独立声学样本。每个source分开运行一个反馈链，比较同资源保守与完整调用推测；不构成多source吞吐/容量优势，也没有把旧两副本并行任务替换成新的同任务对照。未改任何原Y、P99、miss、EOS分母或实际runtime；新端点仅为回顾性支持。

## 全八配对，不只汇总正点

表中箭头为“保守完整执行 → 完整调用推测”，Y仍是原信用；支持列以实际首次视图G为准确参考，不把较高前沿、EOS或文本前缀当同F替身。源名均省略公共前缀`BAC009`。

| 来源 | repeat | offered(s) | 原Y(s) | 同G raw整文本支持(s) | 原Y gross gain/loss(s) | 支持gross gain/loss(s) | D2 miss数 |
|---|---:|---:|---:|---:|---:|---:|---:|
| S0764W0209 | 0 | 8.068 | 3→8 | 3→6 | 5/0 | 3/0 | 11→1 |
| S0764W0209 | 1 | 8.068 | 3→8 | 3→6 | 5/0 | 3/0 | 11→1 |
| S0765W0203 | 0 | 8.334 | 5→8.334 | 5→7.5 | 3.334/0 | 2.5/0 | 7→0 |
| S0765W0203 | 1 | 8.334 | 5→8.334 | 5→7.5 | 3.334/0 | 2.5/0 | 7→0 |
| S0767W0329 | 0 | 8.6689375 | 5→8.6689375 | 4→7.5 | 3.6689375/0 | 3.5/0 | 8→0 |
| S0767W0329 | 1 | 8.6689375 | 5→8.6689375 | 4→7.5 | 3.6689375/0 | 3.5/0 | 8→0 |
| S0768W0136 | 0 | 8.1439375 | 6→8.1439375 | 5→7.1439375 | 2.1439375/0 | 2.1439375/0 | 5→0 |
| S0768W0136 | 1 | 8.1439375 | 5.5→8.1439375 | 4.5→7.1439375 | 2.6439375/0 | 2.6439375/0 | 6→0 |

原Y净增28.79375s，严格同G支持净增22.787875s。不能把前者全部当成与最终同F选择一致的首次内容，也不能把后者另命名为原服务信用。完整推测原信用中10.005875s首次整文本与后来同G选择不同，保守臂对应4.0s；这些观测均保留在逐前沿表中。

## 整轮时序与EOS

| 来源 | repeat | 保守D99 / C99(s) | 完整推测D99 / C99(s) | 完整推测整轮D2/C8 |
|---|---:|---:|---:|---|
| S0764W0209 | 0 | 5.095294 / 5.353938 | 2.520294 / 2.784263 | FAIL D2 |
| S0764W0209 | 1 | 5.393653 / 5.656154 | 2.603106 / 2.870143 | FAIL D2 |
| S0765W0203 | 0 | 3.845149 / 4.160602 | 1.016559 / 1.344281 | PASS |
| S0765W0203 | 1 | 3.870250 / 4.178595 | 1.025279 / 1.365121 | PASS |
| S0767W0329 | 0 | 4.498793 / 4.758838 | 1.222368 / 1.493484 | PASS |
| S0767W0329 | 1 | 4.305279 / 4.557580 | 1.202081 / 1.475122 | PASS |
| S0768W0136 | 0 | 3.296732 / 3.548810 | 0.889529 / 1.148915 | PASS |
| S0768W0136 | 1 | 3.450517 / 3.709405 | 0.942743 / 1.201753 | PASS |

完整推测6/8运行整轮通过；全部非EOS前沿D2 miss为0。余下2次miss是同一来源S0764W0209的0.068s EOS，D分别2.632589/2.718039s、C为2.896330/2.983505s，故0.136s仍不获原信用，两个整轮D99仍失败。保守臂0/8整轮通过，共63次D2 miss（55非EOS+8EOS）。全部16格C8 miss为0。这里报告每次原P99，不混池为新的分位数，不删尾后宣告整轮通过。

## 文本事件、higher-F cover与撤回

完整推测66.29375s原信用按首次cover所在实际row的文字事件分为57.29375s strict-append、9.0s unchanged；保守37.5s对应32.5s、5.0s。两臂均没有replacement/erase-only首次row贡献信用。**“恰逢追加”不是把音频秒数对齐给新增字符；unchanged也仍保留原前沿信用。**

每臂有5.0s原信用由G>offered F的首次视图覆盖：S0764每次1.0s，其余source每次0.5s。这些只能与Canonical(G)比较，不在offered F上冒充精确对齐。进一步只保留G=F且严格相同的子集，完整推测为51.287875s、保守28.5s；净差仍为22.787875s。raw/去空白两种标准不混用。

八个配对的完整`(offered F,实际首次G,首次完整text)`序列逐项相同，实际时刻不同；两臂的全部完整Canonical WAL在各source内也逐对象相同。这支持“同选择任务和同首次文本下更早交付”的解释，不是用不同输出挑出了更多成功内容。所有未获原信用的首次视图也保留；文件同时列出全部276个首cover、每个正G的首视图及不同(G,text)首次出现，不能把这些不同去重粒度当成独立样本量。

两臂各自全8次运行均为202个引入的LCP版本化codepoint occurrence、18个撤去、最终184个可见codepoint；每个配对的这三个数字相同。实际音频前沿withdrawal均为0。文字擦除与音频覆盖撤回分别记录，不能据此宣称临时文本已被内容认证或再次证明了R/S交互必要性。原生Consumer与核心kernel仍有各自实现/验证范围。

## 冻结与复算身份

- 新ID：`REVTRACE-SC-CONFIRMATION16-CONTENT-LOCAL-20261029-v1`。实际神经源码仍为`bdfa3b1307d267a5a4caf6484e1ad465c39a592e`，没有重跑模型或改写该源码。
- 每格分析函数、旧内容端点及5个原控制从`c12803e3ab411ad7898a34a2e257fdee313df81c`**原字节复制**。原CLI有3格/17步总层断言，未直接调用；仅增加16格batch/8配对算术driver，实际干净源码为`57803f3be2ae59e02eb461f1931f4b02814025be`。[完整manifest](CONFIRMATION_CONTENT_ANALYSIS_SOURCE_v1.json) SHA `6c8081e526af4ae7d0ae8f6114fb7d6a439701a6232a86b96f2fd2748331e1e8`；bundle位于`packages/CONFIRMATION_CONTENT_ANALYSIS_SOURCE_v1.bundle`。
- [冻结配置](CONFIRMATION_CONTENT_ANALYSIS_v1_FROZEN.json) SHA `b919232b582e46672a42d1175896c31fc6fcfe87fb30f58e3d8f7abb2488a5ec`。collection中96个本地输入逐项SHA核对，共4,563,776字节；逐格原Y/P99/miss与已有CONTENT重新计算均一致。实际输出共2,197,901字节。
- [分析门](CONFIRMATION_CONTENT_ANALYSIS_RESULTS_v1/GATE.json)：`PASS_ALL16_276_ORIGINAL_AND_CONTENT_RECOUNT`，SHA `1bf319ec3df2add226deb2b47e6a9cc733b599285d050978b5c2944c8dd449e4`。[RUN_RECORD](CONFIRMATION_CONTENT_ANALYSIS_RESULTS_v1/RUN_RECORD.json)保留配置、环境、源码、raw/summary/gate路径；[PAIRS](CONFIRMATION_CONTENT_ANALYSIS_RESULTS_v1/PAIRS.json)、[逐格RUNS](CONFIRMATION_CONTENT_ANALYSIS_RESULTS_v1/RUNS.json)、[全部逐前沿](CONFIRMATION_CONTENT_ANALYSIS_RESULTS_v1/FIRST_COVERS_WITH_EXACT_F_SUPPORT.json)可直接复查。
- [7项CPU控制日志](CONFIRMATION_CONTENT_ANALYSIS_CONTROLS_v1/RAW.log)和config/env/run-record/gate完整保存。原5项不变，另2项只检验“原信用增加但严格支持不增”和“净差零仍保留gross gain/loss”。控制门SHA `37a284be4e134375b27cfc8db5caf83ecb1d7f601cc6f59b1ac69bdb5c9686d7`，不当作服务证据。

**研究判断：本轮支持把作者新组合的full-call retention作为原生应用的优选实现，而非因stage交接未胜出就否定组合贡献。** 原信用和严格同前沿支持同时有一致方向的实测改善，但四来源单链、两次fresh repeat、EOS边界及修订内容必须一起保留。该16格没有ready-handoff臂，不能据此扩展其跨source排名；旧三臂pilot的负/边界结果仍成立。E机会仍只按独立profile门推进，不是当前结果的必要补丁。
