# 同两GPU的多会话资源对照

8/8真实GPU格完整完成，原任务和所有source端点检查通过，controller进程已退出、CUDA拥有者为空。运行实际NN为de0936，controller为7b83；所有source共享原输入时钟、500ms前沿、实际Consumer、持久化和原D2/C8。两GPU都能执行独立会话的canonical工作，不把Conservative人为限制在一个worker。

| 同时会话数 | 策略 | 两重复offered/audio-s | 双期限信用/audio-s | 覆盖率 |
|---|---|---:|---:|---:|
|2|Conservative|33.11625|10.5|31.706%|
|2|Fullcall|33.11625|11.5|34.726%|
|4|Conservative|66.91000|10.0|14.945%|
|4|Fullcall|66.91000|9.0|13.451%|

所有整场D2/C8检查均未通过，失败保留全部offered分母。这里的4位speaker来自既有来源，其中两位也是单链pilot来源；不是新增8位或8个声学独立单位。

这个对照回答资源分配问题：在共同的canonical-first round-robin调度下，多会话canonical需求占满worker时，单链在飞保留的较大收益不会自动转化为同样的多会话增益。2会话中Fullcall两重复各多0.5音频秒；4会话分别少1.0和相同。不能宣称任意并发下都提高容量。

已记录的实际派发也解释了这一现象：2会话Fullcall每次只有2次conditional派发；4会话两次都为0，69次派发全是canonical。与此同时，4会话记录到21／23个两类候选同时可用的派发点，2会话各8个。后者只是另一资源选择规则的可能作用点，不是另一个调度已经取得的收益；是否值得研究需要独立设计与fairness约束，不修改本批结果。

此结果作为同预算部署条件与公平资源对照保留；当前优先补Fullcall/Ready-only在更多speaker的确认，不把这8格改写成新的调度算法。源码、配置、逐source端点、GPU占用与能量均有独立角色及原始位置。顶层汇总SHA256：`e38e7a4976e23ae593d3e9e5abfa2123b82459a49336a9514bbfd0150672c7be`；数值表为`BOUNDED_PRIMARY_TABLE.json`。
