# E 子计算保留：神经保真通过，当前 eager 二进制路线停止

**13次固定组件调用全部完成：完整反馈输入已失配的4个原E，与正确分支的原E逐bit相同；接收这些受保护E后继续原D/C/U，4次完整selected C、IDs、闭合反馈state/全文均保持原任务，固定EOS重复也一致。** 但把所有14个潜在推测输出都导出、只复用4次时，完整成本模型净增加0.305s工作，因此不进入这条eager路线的live cache实现。

这不是部署服务实验，没有新的SLO、吞吐、能耗或自然E-ready率结论。原已经验证有效的完整调用保留实现 `bdfa3b1307d267a5a4caf6484e1ad465c39a592e` 全程保持字节不变。

## 实际范围与结果

使用原source0 pilot全部4个wrong-start→正确fallback对，未按输出筛选。每对做一次原infer到E结束后停止、一次正确P下原完整infer、一次正确P下以收到E替换encoder返回后原完整infer；另做一次固定EOS原完整重复，共13次profile调用。两份完整模型各自原1.5→2s learned-C预热及加载另列于READY，不属于这13个组件样本。没有wrong-branch D/C/U结果或反馈cut进入Canonical。

| 原wrong → correct | 原E计算 | 完整生产路由成本 | 实际消费路由成本 | mel / 原E bits / 原C、IDs、完整cut |
|---|---:|---:|---:|---|
| j11 → j12 | 166.23ms | 70.86ms | 28.87ms | 全通过 |
| j15 → j16 | 164.09ms | 56.21ms | 37.76ms | 全通过 |
| j18 → j19 | 170.83ms | 59.88ms | 36.42ms | 全通过 |
| j20 → j21 | 169.13ms | 53.99ms | 28.99ms | 全通过 |

真实E形状为`[1,1500,1280]`、FP32、7,680,000B；实际mel为`[1,80,3000]`。四对全是跨GPU搬运。原wrong与correct完整start仅tokens/transcript不同、其他字段相同，actual mel与两GPU的原E都相同，这给出了“完整调用不再受支持，但其读集未变的子计算仍合法”的具体神经见证。

接收端E的SHA字段是已验证wire payload的digest；本轮没有独立把接收GPU tensor读回重哈希，不能称远端GPU逐bit证明/硬件证明。实际H2D同步后执行的原D/C/U完整结果是独立测得的，4对和EOS重复都与冻结原full oracle一致。所有实际mel和feature均finite。

## 成本为何使该路线停止

原GPU E真正完成后才计ready，Python forward返回不当成CUDA完成。生产成本覆盖完整E-entry→E-begin guard、E-return→sent尾部（包括feature/wire hash、finite检查与保守E-only cleanup）、真实首Queue hop和parent完整验证。消费成本覆盖真实次Queue hop、完整actual-mel guard、decode/验证/CPU准备、H2D同步/finite检查，没有把这些税从端到端账中删掉。

- 四个可替代原E共`0.670274741s`。
- 按真实固定使用率4/14，对14个潜在生产对象计完整生产成本期望`0.843307295s`。
- 四次真实消费路由共`0.132044404s`。
- 冻结资源门净值：`0.670274741 − 0.843307295 − 0.132044404 = −0.305076958s`；未达到约100ms正余量。

这是由4个实际payload路由测量估计14次eager生产的组件账，**不是观测到了14条新服务缓存事件，也不是测得部署变慢0.305s**。不同调用的重叠、input release、后续队列和调度没有被该求和模型模拟。原full调用为了数值诊断还额外捕获/读回feature，因此它的整体wall不能当成未插桩服务基线，也没有把这段诊断耗时算作可节省的E时间。

局部分解显示E网络计算约167.6ms，GPU-owned clone仅0.056–0.065ms，D2H约1.03–1.84ms。主要代价是完整post-E尾部约19ms、首Queue hop21.5–32.4ms和parent验证6.35–14.36ms，每个潜在输出都支付会抵消低使用率的收益。不能把GPU复制本身误判为全部瓶颈，也不能把只计clone/D2H的低数字当成已经完成IPC。

四个新组件 E-complete 相对本次wrong-call开始约176–185ms；旧pilot中wrong-call开始至正确fallback model-start间隔约267–357ms。这只表示组件量级可能存在一个提前窗口。两者来自不同运行，不能据此声称本次部署在fallback到达时已经ready。

## 尚开放的边界与当前选择

这个STOP仅适用于已经测过的eager完整payload路线，不否定子计算合同或所有可能的carrier。若14次只保留GPU-owned E并发小metadata、仅4次仍按本轮完整搬运成本计费，在**零请求/寿命管理成本**下乐观work余量约0.26s。这是成本下界对应的条件性乐观收益；它没有测量忙worker响应、共享存储容量、stream同步、读者持有、释放/回收或重算时序，不能据此宣称GO。若全部14次预先建CPU共享feature，额外的D2H、CPU准备/hash也必须另计，不能套用GPU按需的条件性余量。

本轮不实现新的共享内存cache或按需copy，不增加模型/来源/精度/负载点。若未来继续，需要先把具体请求/生命周期协议和相同E退出切面给强对照，不能让cache臂额外获得更早取消D的权限。当前更有论文价值的主线，是先确认已经成功的完整调用保留组合在独立来源上的服务价值；E实验作为边界和对象选择的证据保留，避免把所有可分离子计算都当成应当部署的优化。

## 可审计定位

- 实际generator源码：`316b102ac591f3440dcefe4f49f62afa1fd010d5`，8文件完整manifest；导入runtime为独立的bdfa完整38文件，均clean/逐byte核验，full commit已导入本地root可解析。
- 原v1在launch前被完整成本/措辞审阅修正，NN调用0，source/plan原样留存；v2实际Linux17控制、零skip通过。CPU新增反控证明漏掉post-pack wire hash/guard税可能把负余量误判GO。
- 冻结plan SHA：`789f0069a563f4cbc4e454c5259da9b482f588b8d6a708605d31ef134258a960`。
- 26个模型资产10,099,049,234B和4个原audio重哈希通过；原作者audio/model文件及mel_filters官方Git blob核验通过；ROOT current-pointer无参数preflight通过后才启动。
- 实际controller：PID1820713/start502680971/cmdSHA`8c86ad6ba0e38776379afa3d8bdd38b754bf7a4326724789482f8f27e8c4f024`，已退出；两模型worker退出、GPU compute apps空，资源已释放。
- B盘raw：`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_streamcorrect_encoder_profile_20261029/profile_v2`；4个原始feature二进制留B，未发布。
- 本地有界21 JSON共970,166B，逐远端SHA一致，见`RESULTS_v2/COLLECTION_MANIFEST.json`。
- `GATE.json` SHA：`251a67b093650a4d97ff6e57c41cdd35bd045a5d0ce9329397ba518036c042d8`，状态`PASS_COMPLETE_13_COMPONENT_CALLS_AND_NEURAL_ORACLES`，经济门decision为STOP。
- `SUMMARY.json` SHA：`5001b5ff442b2f22b0874309e6acef8bfd062c55fe7fc5ee355b0c040d3a8911`。
