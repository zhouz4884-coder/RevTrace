# 实验/工程修订历史（原始失败不删除）

| 事件 | 定性与处理 | 不可误读为 |
|---|---|---|
| 初次git ls-remote HTTPS reset | 只读身份核查换为已有GCM授权的gh API；没有新登录/token/可见性修改 | 不是仓库不存在或需要重新授权 |
| 16源非平稳空间未过门槛 | 全9scout与negative gate保留。固定rho2已距arrival GP上界约1.4%，没有高段Coarse Commit优势 | 不等于已经实测了Elastic算法失败；未伪造动态输出 |
| 单一跨batch资格修订 | 用户要求同run有实际必要性，追加预冻结32不同speaker、峰值超过MB16，全部三rho/三arrival公平复测；不改SLO/质量/保护 | 不撤销16negative，不混两集合做repeat，不继续无限筛负载 |
| 旧CPU审计等待器预发现变量遮蔽 | expected-count名与per-cell Render map重复；核对PID/UID/cmd/无child后仅停止该idle CPU waiter，v2独立审计执行 | 无GPU终止、无原始测量修改，旧脚本不冒充执行PASS |
| 全历史pytest收集19个缺失legacy依赖 | 公开独立SDK不含一批旧分析脚本/fixture，完整失败log保留；运行明确机制相关scope | 不声称所有历史测试已通过，也不把缺失fixture算作动态GPU失败 |
| 新安装护栏误检查终态残留auth_result | 首次sample-range强化后10失败138通过；对齐base的done/auth_done跳过条件，GPU前148项通过 | 不抹掉修复前log，不对已运行GPU静默改代码 |
| 研究载体重复Copy-Item产生未执行嵌套static tree | 原source archive/manifest完整保留；runtime sys.path不引用嵌套stress_sdk，正式加载根代码只有5项变化 | 不把未执行副本计为另一个算法/实验；导出和原档身份明确区分 |
| 动态预测成本不是Oracle | 287个真实过去批次的median/p90插值供启发式预测，formal内不调参，不用WER标签 | 不承诺精确服务时间/SLO，不把时间screen当神经输出 |
| CPU postflight第一次源哈希检查失败 | `fixed_sdk/SOURCE_MANIFEST.json`继承旧manifest自条目，生成新manifest后该元数据自哈希不一致。保留失败log及原source archive；v2显式记录prior/current元数据哈希，仅排除该生成自条目，逐一核验其余源码、全部模型权重和两版主统计一致 | 不是Python源码漂移；不改写测量archive，也不隐瞒元数据缺陷 |
| 正式联合规则未达三条成功门槛 | 同输入4重复、合法固定和简单动态、独立Render/WAL/consumer/规则重放均保留；判定C2算法升级NO-GO，关闭GPU队列 | 不把Deadline的单个正点估计当成联合算法成功；不调阈值直到获得正结果 |

最后正式结果/独立审计若有额外失败必须追加；没有结果表前不写成功。所有formal运行按冻结顺序完成或因真实错误停止，不为漂亮数字筛掉miss、触顶、未完成或负结果。

最终状态：42个真实GPU运行完成（18 scout + 24 formal），formal后未修改算法或测量结果。主判定三项均失败、质量非劣门槛通过；新增简单动态诊断只作描述，主判定字段与首次分析逐项完全一致。`collected/POSTFLIGHT.json`、`FORMAL_DECISION_INITIAL.json`和`FORMAL_DECISION.json`保留完整对应关系。
