# R0：实际发布与回撤审计

基线 GitHub commit `217aafb8e0e02e6d6561341ba0a965ca937e8ea0` 的 107 个 runtime 文件已逐个匹配 Git blob；正式 T1v4/T3/calibration archive 与上轮冻结 SHA 一致。原工作树未覆盖，520 个现行 TeX/Bib/PDF 文件已冻结哈希。

对 T1 全 18 cells、3393 canonical transitions 逐事件重算。正式 Fine-D：77/279、61/279、77/279；Coarse-D：2/98、2/98、15/98。Barrier 的音频前沿回撤为零，但并非无文本修订。Fine 擦除字符2069/1732/2135，Coarse529/529/730，与原报告一致。

Fine-D withdrawn-audio wall area 为263.487/216.459/268.146 audio-second×wall-second；Coarse-D2.265/0.652/64.917。音频回撤与字符删改分列；复制slot与repeat不计独立声学来源。每 source/session 的分母、深度、恢复删失与lag见 CSV。

这支持进入 R1 的受控因果实验，不支持从rho差异断言单独的延迟因果；分段、条件与提交次数同时改变。`full_snapshot_covers_ahead_private` 仅是事件分类，尚不证明能安全无损保留后缀。规范内容修订也不能不经参考就称错误识别。

R0 的 CSV/JSON 由8TB盘实际 events、config、sessions、worker lifecycle、commit/ACK独立复算，原始sha逐cell保留。trace中没有下游consumer观测；server emit不是client已看到。

## Authority Token → Adapter → Text → WAL → Publication

| 边界 | 冻结基线实际行为 | 能保证/不能保证 |
|---|---|---|
| Authority选择Z | 独立FP32 worker在声明parent/audio前沿上生成；owner核对runtime、audio与父状态 | 保证以受信caller/Authority和固定实现为前提；不是GPU执行attestation或对恶意Authority的证明 |
| Adapter生成P | chunk<2时prefix为空；之后将parent解码再回退5tokens并避开残缺Unicode，拼接当前生成Z的解码；P为该raw串重编码 | 是现有χ的跨调用text-state投影，不是数值KV；不同chunk/音频切分会改变条件，不把rho差异全归为调度 |
| Text生成 | parse_asr_output作用于上述raw串并使用请求language | 是累计且可修订转录，不是新音频区间文字直接append；预算耗尽仍可产生合法但不完整内容 |
| 旧owner/WAL | 选择证书绑定Z/P等，但直接把result.text写入event/WAL并使用 | frame checksum只保护记录字节完整性，不能证明先前worker字段就是Renderχ(Z,parent)；CPUtext-only篡改4/4发布确认此缺口 |
| D0发布 | WAL成功/安装后发版本化full snapshot，再install-ack | 是正确安全基线，允许覆盖超前private而回撤；F与D_ever单调不等于当前view/字符串单调 |
| 新D1/消费 | 独立Render校验、绑定与重放；新receiver映射WAL事实并区分certified与provisional | 新保证只在固定χ/受信依赖/可靠本地FIFO及声明epoch范围；不扩成浏览器绘制、网络exactly-once或识别正确性 |

新D1的text绑定不是“hash一个未经验证字段”：必须先独立由Z和冻结parent重建P及UTF8文本，校验后才写WAL。恢复重新Render并核对选择摘要，文本与证书接口版本均不可静默漂移。对old基线完整3393转移离线匹配并不等于old路径具备在线fail-closed保护，两层证据分开。
