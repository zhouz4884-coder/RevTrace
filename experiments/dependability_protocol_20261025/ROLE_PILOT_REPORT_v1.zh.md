# 受限Proposer故障pilot首版：真实输入消费成立，能耗边界需修复

8个prepared-input真实双GPU操作器案例，1条旧开发音频，4实际方法各
clean/controlled-corruption一次fresh process。不是8条独立音频，不是在线
SLO/自然攻击率。sourcef0eaae，Core408d756，父状态由真实FP32前奏0→2→4s
产生。固定6sOwn-Proposer内容故障后，保持已完成Authority6s结果暂未安装，
执行真实Private8s，再安装并继续真实Authority至音频EOF。所有物理工作付费。

独立核对167个原始文件字节，4对前奏/父状态/原始ProposerZ完全匹配；
真实角色/不可变输入、消息/Drain清单、保护选择证据、实际Consumer链、
WAL以及120个实际base-input/Native-Phi重放通过。所有保护方法都保留
相同强检查；Renderer-only是明确缺选择证据的弱负控，不是完整Standard。
Metadata-only是同一一致内容轨迹的判定影子，不算第五份GPU或成本样本。

## 当前能说清的结果

|实际方法|受控载荷进入Private8s实际处理ID|进入后续Canonical Authority实际输入|末端词错误(clean→corrupt)|末端原子串/完整三词实体|
|---|---|---|---|---|
|Renderer-only弱候选写入|是|8个后续真实调用均是|4/61→6/61|是/否|
|完整Correct-context Strict+实际Fallback|是|否|4/61→4/61|否/否|
|RevTrace独立可信生成|是|否|4/61→4/61|否/否|
|完整Standard正控|是|否|4/61→4/61|否/否|

载荷由Own-Proposer通道在实际模型完成后修改，不是GPU自己生成，原始Z
和修改Z分开。修改未触碰Authority/job/audio/Parent/epoch/runtime绑定。
后续实际Private输入包含固定词串，证明通道可达；保护方法并不保证
所有Private反馈纯净，但阻止它未经选择进入Canonical祖先链。

弱负控末端文本为`Violet Saturn Aldersey`，原冻结子串指标命中，但完整
三词实体`Violet Saturn Alder`未命中。保留两种核对，不改变载荷/算法来
提高成功率。此pilot新神经Z未复制完整目标词串；P/Y中的持续存在有
适配器继承前缀成分，不能称为已测神经放大或永久污染。

## 正确上下文验证的真实替代成本（单点操作，不是服务性能）

在6s目标，cleanStrict全序列验证约72.7ms并接受；受控损坏案例验证
70.3ms后拒绝，实际FP32完整Fallback579.3ms。独立生成受控案例约582.6ms，
完整Standard约594.1ms。两次额外真实FP32同目标Oracle也保留并付费，
不把诊断成本排除后冒充部署吞吐。验证可能便宜，也可能因回退更贵，
由候选/实际上下文决定，不是仅凭角色名字证明唯一方法。

## 功耗检查的负结果与测量修复

首版少数约9s窗口采样支撑只有97.8%–98%，不能标为完整窗口能耗。
WAL/模型时序检查通过，已观察支撑区间的积分和缺口单列；没有按idle或
额定TDP外推为实测总能量。该缺口不改变上述角色/输入/选择/识别核对。

正式扩展前，源码b08fa426只为所有方法统一增加.35s采样前/后缓冲，
原始操作窗口不延长，不改模型/目标/载荷/状态规则/基线。20Windows和
20LinuxCPU测试通过；相同8输入复测正在运行。必须独立确认输入、Native
历史及完整功耗支撑后才能开放64正式案例；首版全部原始与失败检查保留。

本pilot支持限定路径和原理，不支持自然发生率、部署对手成功率、
ASR跨域通用性、主机隔离、受损可信Authority防御或论文录用保证。
