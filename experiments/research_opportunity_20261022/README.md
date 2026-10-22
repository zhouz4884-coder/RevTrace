# RevTrace Research Opportunity Audit — 2026-10-22

先看[最终报告](FINAL_OPPORTUNITY_REPORT.zh.md)、[A裁定](A_DECISION.md)、[B裁定](B_DECISION.md)、[源码生命周期](SOURCE_LIFECYCLE_AUDIT.md)。本轮不修改论文，不预建完整系统。

核心结果：A在现有真实资产没有新增合法输入等价/实际重算机会，NO-GO。B经34项CPU负控、22个实际GPU故障单元证实有条件收养的净恢复收益，但不自动等于独立算法新颖性。最强普通结果跟踪组合仍是下一阶段必须允许的正控。

`source/`为本轮实际执行/核验的脚本，v1失败、v2主18、v3非空父4分别保留；不要把最后一份脚本当作所有运行的版本。源对象Git历史见research_source.bundle和SOURCE_IDENTITIES。原准入/Worker/WAL/Renderer/consumer未修改，依赖冻结的`../phase_d_20261021/runtime`。无模型/音频/凭据，无SSH自动运行。

公开有界证据`PUBLIC_BOUNDED_EVIDENCE.tar.gz`解压后的`B_gpu_v2/`和`B_gpu_nonempty/`是两个完成campaign；`B_gpu/`是必须保留的失败pilot。`A_*`和CPU指标不是新增GPU。第三方安装库源代码摘录不重分发；只删源摘录字段，不筛选科学结果，原哈希/路径保留。

在已有Python+NumPy及同仓库Phase D源码的本机，显式设置`REVTRACE_FROZEN_RUNTIME`指向该runtime，然后运行：

```text
python source/test_adoption.py
```

只运行CPU fixture，不连接SSH或占用GPU。GPU脚本是研究原型，仅在操作者合法取得相同模型/数据、配置全新8TB结果目录且资源空闲时手动复核；不允许当作在线Serving部署脚本。源码、运行配置/环境、完整原始路径、失败和逐文件哈希见EVIDENCE_INDEX。

所有报告里的RTO是SIGKILL到本地认证view应用完成，非网络/浏览器P99；每格两次，非自然故障统计。能耗仅用独立最终原始采样积分并附覆盖率。没有将Cold→Warm的模型重载差值算入Adoption的新算法收益。
