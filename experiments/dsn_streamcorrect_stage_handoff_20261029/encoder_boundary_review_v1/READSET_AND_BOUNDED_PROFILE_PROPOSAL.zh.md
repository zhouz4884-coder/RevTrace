# 完整反馈输入失配后，音频编码子计算是否仍可保留

**判断：存在一个有实际轨迹见证、值得一次有界测量的机会；目前只能判静态可分离，不能判有部署收益。** 它与“等在途完整 ASR 完成”的 join 不同：这里完整 ASR/D/C 调用的输入已经确实不相容，当前调用不能保留，但它内部尚未读反馈文字的 E 子结果仍可能用于正确反馈分支。原完整调用保留的正结果不会因这个方向不成功而作废。

## 已核实的读集与实际4对输入

原作者固定 `simul_whisper.py` SHA256 `9f016f71df780c05b04719633ed302b502a457ff18a086eb5412a394b05cacb7` 的 infer 先检查音频buffer长度，再拼接 segments、log-mel、pad/trim至3000帧、调用 `self.model.encoder(mel)`；之后才 trim_context、拼接 current_tokens、fire/beam decoding、原纠错 C 与反馈 U。

本地重新通过作者官方 GitHub 固定 commit `bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3` 阅读并缓存了 [audio.py](https://github.com/vu-duy-tung/StreamCorrect/blob/bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3/simul_whisper/whisper/audio.py) 和 [model.py](https://github.com/vu-duy-tung/StreamCorrect/blob/bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3/simul_whisper/whisper/model.py)。AudioEncoder 是卷积/GELU、位置buffer、self-attention blocks、LayerNorm；其 block 不接 decoder KV 或文本。原构造器的 KV/attention hooks 只装在 decoder。E 的网络计算依赖实际 mel、固定 encoder 参数/位置buffer、精度和计算实现；不读 feedback tokens、context文本、transcript或last_attend_frame。这里只是固定源码/调用路径的具体审阅，并非任意第三方encoder的纯函数证明。

Source0实际fullspec pilot中四组被拒绝的完整调用与正确回退如下：

| 已失效调用 → 正确回退 | F → target | old → new GPU | 完整 start 不同字段 | ordered PCM buffer |
|---|---:|---:|---|---|
| j11 → j12 | 80000 → 88000 | 0 → 1 | tokens、transcript | 全10个chunk描述精确相同 |
| j15 → j16 | 104000 → 112000 | 0 → 1 | tokens、transcript | 全13个chunk描述精确相同 |
| j18 → j19 | 120000 → 128000 | 1 → 0 | tokens、transcript | 全15个chunk描述精确相同 |
| j20 → j21 | 128000 → 129088 | 1 → 0 | tokens、transcript | 全16个chunk描述精确相同 |

每对 source SHA、buffer的有序dtype/sample-count/SHA、start F、target、新增不可变音频区间和固定backend合同均相同。其余完整start字段（包括context与last_attend_frame）也相同；差异确实仅是token反馈和累计文字。原restore_cut会从已哈希源重建并检查每个PCM chunk，随后按同区间插入新音频。本源8.068s没有触发30s buffer trim。因此它们有相同原音频预处理输入的具体结构性见证，不能简化为“同F所以相同”。

静态CPU结果：4对见证、8个读集key正反控制全部通过；未import Torch、未加载模型、未运行GPU。分析源 `6cacee199c8ad9818dcc4fef6d4a72079f6675fd`，完整manifest/bundle/快照、config/env/run/gate齐全，root Git可解析。`RESULTS_v1/SUMMARY.json` SHA `d370f438c1b59918c8281029979200925bf26e7215c16e83d254abcc35ed6f71`。

这些CPU控制只证明结构key对已声明字段的区分，不冒充神经张量数值一致性。现有服务日志没有保存实际mel/E、E结束时间或copy成本。

## 不可省略的合法性条件

1. 使用**受保护原E执行路径**的结果，绑定原权重、encoder/audio源码、mel_filters.npz、n_mels、480000 padding、3000 trim、实际完整PCM及长度、FP32/eval/autocast/TF32/SDPA等计算合同。不能只依赖source ID、F、部分音频或固定shape。log-mel在trim前有全量max归一化，不能任意只哈希前30s而忽略其余实际输入。
2. 单独的 E 结果类型不携带已通过 D/C/U 的权限。调用者以**当前完整Canonical反馈cut**正常运行原D/C/U；只替换其相同E输入的编码结果。不能移植旧decoder KV、token、alignment、C选择或错误endcut。
3. E是否数值可交换必须先做实际同输入/重复/跨卡与原完整调用oracle。不能从输入相同推出任意GPU执行都bitwise相等，更不能据此省掉最终任务保真检查。
4. 原birth/worker/job、可信通道、输入watermark、epoch与安装前完整Root检查仍保留。E结果只满足自己的读集，不能给整个旧Root重新授权。
5. 如果E-return wrapper给了更早的known-invalid取消机会，无E复用的强fullspec对照也应获得相同E边界检查/清理权限。不能把更早省D伪装成编码复用收益。

## 真正的性能难点

四次正确回退都落到另一GPU，单卡本地保留会在这四次产生零跨卡复用。大-v2 FP32 E预计是 `[1,1500,1280]`、7,680,000B，**shape/字节数必须在实际profile中确认**。本点有14个实际推测dispatch（10保留、4否定）；若每个都eager导出E，则至少是14次capture/export/传输以换4次使用，预计原始feature流量107.52MB，不能只记4个命中免费。

同时，正确回退开始比旧错误调用最终退出提前约123–397ms。等旧调用到了原C-entry才返还E已经太迟。机会取决于编码完成后立即得到的E-ready元数据与实际跨卡交付，旧ASR总时长435ms不能当成E时间。若选择GPU本地保留、按需才搬运，可减少无用传输，但当旧worker仍忙D时如何响应copy请求、CUDA同步和allocator生命周期都需要实际协议与成本，不能先假设免费。

EOS单点需要节省约666ms才达到D2，且其父状态安装已晚于deadline约160ms。只消掉EOS一次E不自动解决它；前面j12/j16/j19的正确链是否也提前，取决于完整调度与输入到达。四次节省不能直接累加成部署尾延迟，也不能让offline critical-path估算替代实际服务对照。

## 建议的唯一有界profile（等待16格全部释放后再审批冻结）

不实现cache、不改bdfa。新profile源码用原完整infer的encoder forwarding wrapper计时/捕获，原C/U保持；数据只用该固定source0 pilot的21个真实dispatch输入（20次原E，0.5s初始调用无E）。预先固定全部14个推测调用都计捕获/导出成本，不挑4个成功可能重用点才计开销。

- 按原实际GPU角色回放21个固定start/target；原encoder前后同步记录mel、E形状/dtype/stride/finite、E原始耗时、E-ready相对完整调用位置。14个预先标记推测输入全部测独立拥有clone、CPU中转Queue导出及验证/保存开销，4个实际回退测同一真实跨进程路径的跨卡import；任何不做的部分必须明确标未测。
- 检查4对实际mel与E完整逐bit相同（并保留任何差异）。再在4个**正确**fallback cut上，用受保护E替代原encoder返回，继续原infer的D/C/U，与同输入原完整结果比较 selected C、IDs、closed反馈cut与全文；单独重复EOS原完整调用一次作为fresh控制。总scope最多26次原infer，不增加来源、训练、精度或服务负载点。
- 冷load/原NN-ready成本另报；所有feature/raw留B盘，取回仅有界hash/timing/差异摘要。GPU同步/拷贝的测量扰动单独记，operator/copy与offline回放不能写成服务加速比。
- profile第一门是完整输入/神经/原任务保真；失败先按同输入、重复、原full oracle分因。经济性至少同时列 `4×可省E − 14×实际capture/export − 4×actual import/check` 的总资源账与E实际ready/交付关键窗口。若eager账没有净空间，不直接进入cache工程；若只在按需保留下可能有空间，则需先明确并测该协议，不能用理想on-demand数替代它。
- 只有精确门通过且相对**已经有用的fullspec**仍有清楚的净关键路径空间，才讨论一项后续小服务实现；服务成功标准继续使用原信用/延迟/能耗，并保持相同退出切面。若空间不足，冻结这个局部边界的有据STOP，保留当前完整调用贡献。

这个方向的论文价值，是在真实可信纠错反馈中区分“完整父状态不再支持的调用”与“其依赖音频仍未改变的受保护子计算”，从而把依赖合同细化到合适对象。编码缓存/中间特征复用本身并不需要被写成首次发明；是否成为正文贡献，应由实际合同、保真和服务收益共同决定。当前证据只支持继续这一次测量。
