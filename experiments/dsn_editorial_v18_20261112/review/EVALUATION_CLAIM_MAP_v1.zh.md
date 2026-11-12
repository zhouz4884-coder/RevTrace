# v18评估改写：论证与证据映射

唯一论文写入目标：隔离v18树`sections/05_evaluation_v16.tex`。保留eq:credit、fig:main_evidence、tab:native_confirmation_v16、fig:native_confirmation_v16和五个Native宏；不改图、表、bib、main，不编译、不增加实验。

目标：用“为何同时度量及时性/持续性→原任务内为何可保留在飞调用→相同任务下服务/资源结果→实现与工作点边界”的顺序组织评估，不把native几组聚合均值写成普遍双峰规律。

| 论证块 | 证据与确切范围 | 写法 |
|---|---|---|
| B 联合价值跨cohort成立 | H3 primary/Qwen/rho1/staggered，A/B/C I=18.530/6.205/17.555s；originaldual_audio_fraction的sourcewise interaction均值5.89875pp、描述bootstrap[1.12939,10.27954]pp，24source、3共享队列cohort | 定义I=Y11−Y10−Y01+Y00；CI指源内fraction交互，不是joint-vscompute差、U_norm或部署总体CI |
| A 首次信用可与持续服务反排名 | 另一个c16开发银行r2，compute-only201.960 vsjoint194.735s，前者原D2读点缺失4.000audio-s、joint0；post-hoc secondary endpoint | 不是普遍支配；说明两个端点不能互换 |
| C 输入资格不等于自己预测正确 | 旧BDFA四source/16trial银行92实际model-active promotion，其中20 own tentative successor与原C/U选择不等 | 明确旧银行；原C/U继续决定结果，不能给它贴NNde09新N8身份 |
| 当前N8强对照 | 32 Full/Ready、8原有speaker、2repeat，93.90405% vs42.43308%，51.47097pp；worker223.21495/322.99054s；energy91.8797/117.8227kJ；3真实ready复用 | 保留strict2×2信用优势、8源资源同向、聚类留一；不转用旧CI，不跨runtime声称因果提升 |
| 机制pilot | 24cell/2source；Full/VDag各56actual handover；290job/install predicate rows、288unique qualified IDs，278currentlyconfirmed/12refuted | predicate与实际保留动作分开；未实现text-only性能臂不写实测失败 |
| 外部阅读规则 | LA2-CP为published-rule adaptation；fixedlag0.5是generic control；相同Full/SUP/记录日程 | 31.340125/32.340125s、0/4 edits；fixedlag26.840125、9 edits/3retreats；诊断tradeoff |
| 负例/机会范围 | negative paired_jitter A/r1 ΔR11−R10−4.245s、I−2.245s，仍5次兼容保留；primary-sync pooled Δ−.790、I+2.565，3次兼容保留 | 不是no-op/无ahead；机会计数是观察诊断，不是上线前预测法 |

顺序：setup/度量；joint factorial与反排名；当前Full/Ready；输入/输出及pilot机制；LA组合；资源与时序边界；简短安全检查。E原引擎参考与协议cost由Root单独整合，避免重复。删除跨runtime“相同决策结构”、two independent native banks、generic fixedlag“第二发表规则”、text equality“实测近无保留”、soundness推出completeness/普遍性能带等表述。
