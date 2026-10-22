# 固定粒度优化空间：启动前冻结

同16条完整、每人1条独立LibriSpeech录音（PhaseD pool，不宣称本轮新未见语料），无复制槽/循环/截断。双3090，GPU0 FP16 proposer、GPU1 FP32 authority，eager、microbatch16、256预算，fine2s，原D1/严格whole-view连续性、decoupled-lazy、two-lane及group-ready WAL全部保持。固定rho1/2/3使用同一新carrier，只新增固定rho2和到达offset输入，不改变准入谓词或基线保护。

三种到达：sync全0；uniform-stagger sid×2s，明确不同于旧R4的0.25s；low-high-low的sid0/1在0s、sid2–13在10s、sid14/15在42s。实际活动/未完成量由trace复算，不凭设计名声称每刻都处于低或高负载。每个运行消费同16完整源，任何未完成/超时保留分母。

先9个scout（3rho×3arrival、1repeat、预先轮换次序）验证空间；不是统计性最终比较。主SLO显示2s/提交8s，共同2s及精确末端frontier，显示用真实FIFO view应用完成；完整2/5/8 × 4/8/12/16 deadline网格。联合Goodput为同时满足两期限音频秒/arrival+drain直到最后认证消费；整run双P99通过另外报告。未显示/未提交前沿为无穷延迟，不剔除。

质量约束：同音频Fine基线的逐唯一源English WER及CER，候选增加不超过0.5绝对百分点；触顶/未完整音频另列，不用合法性替代质量。在线调度不能看参考文本或将不同rho的Z/P拼成动态history。

GPU能耗同时报原device sample span积分、严格公共服务窗口的独立积分和覆盖率；主机能耗未测。重复interval共享batch服务去重；积累、parent eligibility、enqueue、worker preprocess/model/receive、Render/WAL分列。

进入Stage3条件：同集合scout有负载阶段交叉/队列积压且无单一固定设置同时覆盖全部质量/SLO/成本目标，或仅用真实服务时间（不使用神经输出）构成的乐观调度空间仍有≥5%Goodput/≥10%CommitP99或能耗改善机会。若没有，算法升级NO-GO，不为正结果变更SLO/样本/基线。

如门槛成立，最小Backlog-only、Deadline-only、联合规则冻结后才做CPU与GPU；非平稳formal预期6策略×4repeat=24fresh cells，同carrier含固定1/2/3，repeat轮换顺序。主要成功：联合Goodput≥5%且配对run/source聚类95%区间严格>0，并超过最佳合法固定和最佳简单动态；备选CommitP99≥10%且Goodput非劣2%，或能耗≥10%且质量/SLO非劣，均不得新增准入违规。CI只能解释本有限源池/运行，不能冒称通用最优。
