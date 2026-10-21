# 指标、时钟和证据口径

## 状态对象

- `F_commit`：本实现已持久化且安装、可供后续调度的认证音频前沿，单会话单调。独立记录WAL同步区间；安装通知可能还包含合法协调CPU工作，不等于单独fsync结束。
- `D_visible`：消费端当前有效视图的输入覆盖前沿，可回撤；不是词音时间戳或识别完整性证明。
- `D_ever`：截至该时刻曾合法显示的最大前沿，单调，但会掩盖当前内容被撤回。
- `P`：Qwen adapter跨调用token投影，不是跨调用数值KV缓存。`P`在同F相等，加完整因果链/冻结输入条件，才允许whole provisional假设重新锚定；不认证其未来内容，不做字符串后缀拼接。
- `text`：`rollback_prefix(parent,chunk)+decode(Z)`经parse_asr_output的累计可修订转录，不是简单的本音频区间增量。D1逐字节重建、比较P/text并把Render输入绑定入WAL。

## 计数与质量

- 回撤率为音频前沿下降次数/指定canonical publications；消费端canonical触发和private失效触发另列。每audio-minute、source/session、repeat和语言分列，不用复制slot扩大独立样本数。
- 字符擦除是`len(previous_text)-LCP(previous,new)`代理。它不是编辑距离、语义错误数、浏览器真实擦除或用户感知研究。
- `withdrawn_audio_wall_area`单位为audio-second×wall-second。零面积与快速首次显示是两个条件，不能靠隐藏临时输出宣称无代价消除回撤。
- WER/CER按明示正则/NFKC口径和唯一源统计，重复slot逐个保留结果供一致性审计。English WER与Chinese CER不混成一个单位。
- 暂时全文到达的质量只在确实被有效消费的完整录音hypothesis上计算，报告可用分母。canonical完整录音质量覆盖所有已完成会话；临时输出匹配authority不等于ground truth。

## 时限与成本

- 主SLO按每2s及准确末端的共同音频frontiers，包含未完成项；display以实际消费端完成view application的时钟为准，commit为持久安装时钟。联合Goodput按同一frontier的两期限同时满足的音频秒/完整wall。
- 整次run的双P99通过与部分音频秒的联合Goodput不是一回事。scout与fresh formal分层，三次repeat分别报告通过情况，不能只用中位数抹掉miss。
- CLI `result.json`的旧`display_p99_seconds`/`display_p99_2s_pass`是**事件口径辅助字段**，不是最终共同前沿/消费端容量判据。主表使用独立重算CSV。
- 新消费端同时记录dequeue receipt和view application完成；不是网络/浏览器绘制时延。早期preliminary carrier记录dequeue，最终carrier已修正，不能混合取中位数。
- Renderer/proof单项host wall与consumer thread CPU单列；GNU-time为整个cell（含初始化）的CPU/IO/RSS，不当作serving-only CPU或CPU焦耳。
- GPU能耗来自实际采样功率梯形积分，含device idle/排空，非CPU能耗或纯kernel效率；原始采样span与server计时边界分列，不把token数乘均值冒充GPU秒。
- 恢复分别记录ledger replay、model initialization、restart launch→first certified consumer、整段恢复/剩余输入drain。故障driver旧标记名ACK_FOR_KILL实际点为安装后、canonical发布前，不是consumer已ACK。

## 比较边界

- LocalAgreement2/3是有来源的显示策略适配，不是原生Whisper-Streaming完整系统复现。缺词音对齐时，稳定partial prefix的音频前沿只报certified-F保守下界，不能据此宣称原生LA的SLO必然失败。另有**离线选定文本prefix可见性**评估真实消费日志，不能替代主SLO或在线认证。
- Standard Safe Async独立重实现的是常规策略，复用相同executor/commit/WAL/renderer。非抢占Torch backend中已执行GPU调用只能逻辑退休；未来covered窗口实际不再派发，不虚报物理取消节省。
- 同rho规范化history比较包括版本/父/音频/身份/Z/P；contract/runtime指纹、私有失效计数和跨会话交错不要求字节相同。各自WAL全字段另行复核。
- 先前1.403×/32.18%/51.4%属于Phase N及更早指定口径，不与本轮live/UI矩阵合并。旧V0/V1NO-GO、长Whisper截断/内存边界保留。

## 证据层级

无注入的受控GPU replay不等于生产自然发生率；人工交付hold、实际消费F2、真实SIGKILL、CPU调度fixture、CPU processor重放、离线Oracle/指标各自标明。R5/R6是固定态GPU操作器，不是已上线服务或V2。源库警告不作静默Tokenizer/Φ修复。
