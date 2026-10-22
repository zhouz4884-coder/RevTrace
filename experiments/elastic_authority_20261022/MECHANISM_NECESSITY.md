# 第一阶段：动态Authority粒度的必要性和安全义务

原PDF Theorem1见物理第4页、证明第5页，逐页核对。它证明accepted-history的局部准入归纳不依赖区间长度，允许不同粒度产生不同合法文本；不是最优调度、质量、活性或当前实现已支持动态rho的结论。

## 可扩展的归纳与不能省略的前提

若每步由当前已提交父状态开始，选择rho_k∈{1,2,3}、正的下一连续区间，且实际调用只消费已释放音频、输入冻结、每次通过同一V，Lemma1/2的归纳可逐步用于可变长度。不能仅凭“对任意常数rho”推导任意有bug的在线切换器安全。Lemma3的私有因果条件和PropertyD的文本/消费条件另行保持，WAL假设也不合并成无条件保证。

## 实现逐项审计

| 对象 | PhaseD正式实现 | 动态化必须补的义务 |
|---|---|---|
| Parent/F/P | `_make_job`、`_commit_ready`绑定当前state | 仅已安装parent，单会话至多一在途Authority；不能中途改变在途区间或P |
| 区间/Chunk | `_begin_segment`用固定`segment_start+self.rho` | 每次计划记录start/end、nominal/effective rho；chunk仍是2s细窗口索引，不是提交次数 |
| 音频 | `_ready_time`按目标音频前沿释放，restart以剩余后缀时钟重放 | 可先规划未来目标，但不可提前执行；使用当前可见队列而非未来音频/未来负载 |
| Private Generation | 有序single-flight、eligible-parent rebase、精确P链保留 | 计划变化不得改写冻结private调用；新的实际提交到达后才按原护栏rebase/保留 |
| 事务ID | sid:start:end，原request digest含parent、Z/P、χ/runtime等 | 区间不同就是不同ID；同ID冲突仍fail-closed，不用“第几次提交×rho”恢复前沿 |
| χ/策略 | 固定rho写在config/contract digest中 | χ一次声明允许集合、选择规则、参数/成本初始化、恢复reset语义；不可每次改rho就重算χ冒充同会话 |
| V | `dgft.validate_segment_job`不读取rho，只检查显式parent/范围等 | 仍保留V；caller增加策略允许集合及计划一致性检查。opaque χ不自动验证策略内部实现 |
| 完整性计数 | `run()`用ceil(remaining_windows/self.rho)推expected commits | 动态计划必须用明确连续区间覆盖和最终前沿审计，不能沿用固定次数公式或只比已完成数 |
| WAL Resume | 直接恢复实际F/P/已消费ID并增加epoch；未持久保存未派发计划 | 可重新计划但不得覆盖旧事实；C中声明队列/标定状态reset。已安装区间逐条重放，未来动态文本不要求与无故障运行一致 |
| D1/D | 独立Render+WAL字节绑定，双通道和whole-view精确兼容 | 全保留；不存在“选择了更大rho就可免检/拼接推测后缀”的路径 |
| 质量 | rho改变切分及条件，合法不等于识别更好 | 真实GPU分别生成整条历史，逐源WER/CER/触顶；不能拿固定rho的输出片段拼成动态Oracle |

`adaptive_audio_plan()`是已给定音频上的能量极小值分段工具，使用整段prefix-sum及候选邻域，既不观察Authority backlog，也不是既成在线Elastic调度器；直接把整段未来音频交给它会越过本轮信息边界。它不能证明当前固定`LiveQwenScheduler`原封不动就可动态认证。

它返回的边界还不保证落在live的2s细窗口格点（默认能量候选步长0.05s）。原WAL Resume对非终态F要求`F % chunk_samples == 0`，而Chunk是细窗口索引。故原样替换为能量切分会破坏当前恢复接口；本轮离散rho集合保证中间前沿仍在格点，只有真实EOF尾段可不足一个fine窗口。

## 原证据可支持的趋势

T1同12-source/16slot固定配置中，Fine/Coarse有限到达窗口需求可比较：r0 Authority worker service46.104/22.814s、同步model-call40.275/20.164s、到达窗口40.295s。它不等于稳态U，也不能把重叠parent/capacity等待相加为“纯锁因果份额”。

R4低负载和高负载来自新池不同嵌套源数及到达方式，不能拼成同一个模型运行的在线交叉证据。第一阶段CSV独立重算service、积累、eligible和queue；新第二阶段固定同16完整源才检验真正非平稳空间。

## 审计裁定

存在清楚的理论可行域，也存在必须改动的运行时点。**安全必要性GO不等于性能优化空间GO。** 先补固定rho2及同集合负载比较，未见空间不实现完整Elastic、不改变原DGFT贡献主张。

## A/B/C/D与论文C1/C2/C3不要混名

Phase N的运行时A/B/C不是论文三个贡献的缩写：A拒绝新的过时private发布；B在有限reconciliation中跳过已覆盖窗口、保证进展；C在安装后发布真正的canonical纠正。Phase D再补可信Render和版本化实际消费/whole-view兼容D。原稿“exactly one obligation”不能替代这些已修订的实现义务。本轮保留全部护栏，不把“rebase安全”当作“显示/恢复全安全”。

Qwen实际Worker仍消费截至目标b的**完整音频prefix**，并按当前chunk索引从P回退5tokens；证书另绑定当前连续覆盖区间[a,b)。rho改变调用次数、实际条件和可能的生成内容，不只是让同一神经输出晚一点发布。成本表因此只作历史预测，不被解释为无条件可加的固定6秒算子。
