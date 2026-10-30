# 完整调用精化：正式有限规格模型结果

正式CPU运行在指定8TB盘完成，不是开发smoke代替正式结果。source_v3实际commit为`deb3260655e2f3312499a34597cc0be6fc15484b`，6文件完整manifest SHA `e2ceaad9d1a6e5f4051689a71b158a75244840be3fa2ccca8829b95a7c39d497`；root切CURRENT并无参preflight后，B盘从bundle独立clone、逐字节核对并登记真实环境/配置/原结果位置后启动。

实际PID2121954/start509435193/cmd9d66c4…已经gone，全部12个有界输出逐远端SHA取回；没有Torch、模型或GPU调用。原始结果在`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_native_refinement_20261030/formal_model_v3`；本地`FORMAL_RESULTS_v3`。GATE SHA为`0def56212a5596e6a1e931a9b7190a5bf2f4b11606004725e0c90bb6c0b8a1f4`。

| 预先冻结profile | 实际状态 | 实际边 | 深度边界处状态 | 边界 |
|---|---:|---:|---:|---|
| normal_two_frontiers | 6231 | 11142 | 2144 | 2前沿、至多3发起、12事件、无故障 |
| failure_one_frontier | 14074 | 25799 | 2828 | 1前沿、至多2发起、12事件、至多1次Owner/worker/session fence |

27/27命名控件通过、零skip；总计20305个有限状态、36941条有限边。没有触及150000状态cap；声明的12事件深度边界确实截断了后续行为，不能叫无限穷尽或无限活性证明。两profile不同界不合并为一套覆盖所有三前沿故障的模型。三前沿/四调用的祖先失配后再收敛由独立命名控制显式构造。

## 新检查的实质对象

* UNKNOWN、CONFIRMED、REFUTED完整输入与覆盖用途分开；祖先失配不能单独授权取消未来未定完整输入。
* 完成早于/晚于确认、未来结果缓冲以及按真实父状态安装；自己的输出预测出错不否定当前输入。
* Owner namespace、session epoch、worker incarnation三个域分开；worker-only重启后已拥有的完整buffer保留原incarnation，不重签。
* 原C/U完成不等于持久接纳；只有完整durable事实才允许Canonical安装和实际认证消费。Owner崩溃后重放事实是stuttering，不是新神经工作。
* 实际Consumer整视图、必要不兼容撤销、每次commit自身root快照。预测视图不得越权推进认证前沿。
* 局部拒绝已知重复/旧域后仍可继续；真实物理exit确认前不能重用槽，接受输入与原时钟不得丢失/重置。

控件含可观测的非法变体：投影假冒C/U、未确认输入准备写入、快照消费撤掉兼容view、用最终root替前一commit的publication、未fsync安装、旧epoch重新授权、提前复用物理槽以及重置原输入时钟。它们是规格层反例控制，不是自然故障频率，也不意味着实际runtime存在相同bug。

## 与最终实现的范围关系

数学命题与守卫/日志映射见[MODEL_DESIGN_AND_CODE_MAP_v1.zh.md](MODEL_DESIGN_AND_CODE_MAP_v1.zh.md)。原保护程序允许关系可以非确定；精化检查不把任意GPU重跑与一条固定参考逐位相等作为前提。

此模型手写而非Python/CUDA机械抽取。一个bit代表完整不透明状态的等/不等关系，不能说两个值覆盖任意数量不同真实cut的全部交错。通用归纳论证依赖声明完整状态、忠实原C/U执行、Owner独占接纳、durable前缀与消息身份前提；有限模型提供有界可检查支持。

规格v3恢复时允许显式epoch fence撤销旧Private steps，Supervisor已认证事实保持；实际SurvivorConsumer.begin_owner保留更多既有view。不会把这个有限恢复profile冒称机械覆盖后者的全部路径；独立actual-trace checker将直接重建实际publication/Consumer记录，验证compatible实际应用以及原调用来源。

开发v1的helper漏参和v2的两个fixture定位错误分别保留失败日志与说明；v3修复后按原profile bounds重跑，未删除测试或调整cap。它们没有改变神经runtime、数据来源、原期限或实际服务结果。
