# Elastic C2 的形式化义务（设计，尚未宣称实现/实证）

允许的扩展是适应性区间序列，不是放松准入。令g=2s，单会话已安装状态L_k的音频前沿F_k，策略读取已发生观察O_t并选择r_k∈R={1,2,3}；名义目标F_k+r_kg，实际末端只允许已声明EOF截断。

## 安全扩展命题

在原可信caller、单owner、不可变输入/χ、受信Authority及WAL假设下，若每个实际派发J_k满足(a) parent=L_k；(b)start=F_k,end>start且实际end音频已释放；(c)绑定当次选定的Z/P；(d)使用同一V与原WAL顺序；(e)派发后J_k冻结，则任意依赖过去O_t的r_k序列仍满足Theorem1的祖先和无间隙/重叠不变量。

证明：初态由χ固定。归纳步只读取当前父、唯一ID及连续区间，并经同V/WAL安装；不依赖r_k与先前r_j相同。r_k可随过去变化，但不能改变已执行或已提交步骤。本命题不提供SLO、质量、最优性、无故障/有故障终态相同或无界流量活性保证。

## 必须实现并测试的义务

1. 策略只在无在途Authority且父状态有效时选段；记录观察时点、名义/实际粒度和冻结的end，不能在结果返回后为其重新挑选parent/范围。
2. 策略信息边界：合法parent、已释放frontier、当前队列/worker占用、过去成本、固定deadline。不能读取未来文本、参考标签、未来到达表来作在线决策；离线仿真若使用未来必须另标Oracle/上界。
3. 先规划目标不授权提前调用，实际dispatch仍以`audio_ready_perf`为门槛。缺少足够可用音频就等或按预先声明的重选规则在**尚未派发**时改计划。
4. χ静态包含R、规则版本、成本初值/更新、deadline、恢复reset；每步选择不改变χ。V保留，caller另外验证集合/区间与计划一致，不能把opaque χ当成自动执行规则检查。
5. Private single-flight/in-order、eligible-root<F_target和generation围栏不变；所有pending输入冻结，D1/whole-view兼容检查不因新rho绕过。
6. 原sid:start:end身份与request digest继续使用。尾段名义rho和实际区间可不同，尾段剪裁记录清楚，不能让零长区间或跨epoch旧结果重新安装。
7. WAL只依已成功事实恢复F/P/身份，不以commit_count×某个rho重建；未提交计划可在新epoch按声明规则重选。参数变化需新χ，旧日志不静默复用。
8. 质量独立：不同合法切分可能生成不同Canonical History。每条历史做独立准入/Render/WAL和真实WER/CER；禁止固定轨迹片段拼接或CPU重解释旧Z作动态生成证据。

本阶段只冻结义务。若优化空间门槛失败，不以“已经能证明安全”作为继续实现算法的理由。
