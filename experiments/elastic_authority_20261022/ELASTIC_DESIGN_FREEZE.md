# Stage3最小Elastic：formal前冻结

32源资格门槛已通过：低段Fine快4.62s，高段Coarse快13.82s，但所有固定高压点都有miss。此为实现许可，不是算法收益。16源negative gate保留。新模型、恢复worker、selector/KV课题不启动。

## 共同执行与信息边界

六策略同一新SDK：fixed1/2/3、backlog、deadline、joint；原Worker/dgft/WAL/Render/consumer保持，base仅把固定expected-count公式抽为可覆写hook。subclass负责计划及caller护栏。pending plans在首个fine音频已释放、当前parent合法且无在途Authority时选择；派发仍等实际目标音频，已派发计划/私有输入冻结。χ一次包含允许集合、规则/参数、服务表和resume语义。

在线只看当前已释放的流/未认证fine-window量、当前在途及已规划任务、当前F、历史服务表、最早共同frontier的8s期限。未出现的future cohorts、音频内容、参考标签不参与选择。已观测流尚未规划者在预测里用rho3，不是真正提前派发；EOF仅在已到达时缩短预测。实际job统一在选择后按流末端截断，不能越过释放。

历史成本来自32源固定scout的287个去重真实Authority批次，只读取batch大小与完整worker服务时钟，不读取Z/P/text/reference。按rho与batch size分段线性插值，上端线性外推、下端用最小观测成本；median用于需求估计，p90用于期限预测。formal内固定，不看质量标签更新、不引入学习器。成本预测是启发式，不承诺SLO。

## 精确候选

1. Backlog-only：当前已释放但未提交fine windows总数≤8选1，≤24选2，否则3。阈值固定，不在formal结果后调整。
2. Deadline-only：单Authority lane的当前余量和已观测流计划/预测队列做有限FIFO批模拟，选择最早共同frontier期限内最大的rho；无可行项时选预测最小lateness，再按单位音频work破平局。miss不授权跳过验证。
3. Joint：在同预测下，同时要求混合已规划/当前候选的需求估计≤0.95和期限可行，选最小rho；若无可行项，使用同least-lateness/work退化。这个规则不比Deadline基线拥有更多未来信息或额外GPU。

每次记录候选ETA/需求、队列观察、选择与计划时间。计划冻结前校验整数rho∈{1,2,3}；安装前核对parent/chunk/end窗口及精确sample范围。私有generation/whole-view兼容沿原规则，不认证字符串拼接。

## 测试、恢复、测量

本轮81种变长primitive/WAL序列已通过，原SDK机制回归和新增策略CPU协议148项通过。完整历史测试自动收集因19个不随公开SDK分发的旧分析脚本/fixture缺失而失败，原log保留，不声称全历史suite通过。新增sample guard首次复测暴露对终态auth_result未按base跳过的错误；GPU前修复，前后日志保留。

WAL恢复以实际F/P/ID为准，未派发计划丢弃后在同规则重新选择；历史服务表固定不漂移，未来文本可以不同，不保证无故障同终态。只做CPU协议恢复核对，不追加C3 GPU故障矩阵。

功率在服务时钟前/后各多保留0.25s采样以包围窗口；固定和动态均同样处理。主能耗使用严格共同服务窗口独立积分+覆盖率，保留原采样span值，额外等待不计为serving加速/延迟。

## Formal矩阵和停止

只LHL32源，6策略×4fresh repeat=24。顺序r0固定1/2/3/backlog/deadline/joint；r1左移2；r2左移4；r3逆序。每个运行保留604.85s全部音频，所有未完成frontier留分母；不混scout为repeat。固定及动态各自Canonical History独立审计，不要求彼此输出相同。

成功/质量/SLO阈值沿STAGE2_FREEZE不改。采用配对run/source聚类的条件bootstrap，并比较最佳合法固定及最佳简单动态；小样本/相同语料限制明确报告。未满足则C2算法升级NO-GO，原DGFT主张保留。formal后不为正结果调阈值/再筛负载。
