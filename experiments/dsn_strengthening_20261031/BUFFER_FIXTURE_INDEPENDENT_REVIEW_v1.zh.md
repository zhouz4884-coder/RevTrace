# 稀有完成缓冲交错夹具：独立审查 v1

日期：2026-10-31。审查方式：只读源码/manifest 检查及不写磁盘的纯 CPU 函数反例；未启动正式 CPU suite、NN、CUDA、远程任务或信号。仅新增本审查文档，未编辑夹具实现、共享 harness、NN 或 CURRENT，未执行 Git 写操作。

结论：**HOLD，先补两个确定的证据/路径校验缺口，再冻结并做正式 CPU/GPU。** 没有发现夹具替换模型结果、绕过 C/U 或扩大输入 eligibility 的实现。共享 harness 的硬超时边界另需在正式启动器中落实；这是执行保障缺口，不是已发生的 GPU 挂起或神经语义失败。

## 审查范围与当前身份

- fixture：`buffer_fixture.py`、`buffer_controller.py`、`audit_buffer_witness.py`、`run_buffer_fixture.py`、`build_buffer_plan.py`、CPU probe/driver/tests/README。
- shared harness：`paired_resident_source_dev` 的 resident Supervisor、独立 facts/reference/request-clock 审计、现有 campaign 外部超时与清理路径。
- NN：`dsn_native_resilience_20261030/source_v2`，HEAD 为 `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`，状态为空；`packages/SOURCE_v2.json` SHA256 为 `60ae549fcc98165a74e5a3dc420bf93418296099fa12b410572b15d281b2c457`。逐文件校验 59 项，0 项字节/长度不符。
- fixture 审查开始时为 10 个未提交文件；本文件是审查交付物，不是执行核心变化。冻结时应明确是否把它纳入完整 manifest，不能继续称新增后只有 10 个文件。

## F1 / P2：独立审计未把原生 fence 绑定回实际 child UID/物理身份

位置：`audit_buffer_witness.py:64-75` 与 `buffer_controller.py:129-139`。

`audit()` 从原始 dispatch/results 与 marker 获取 `cjob`，并用 `validate_buffer_binding()` 校验它；随后 `validate_release()` 却使用 release 自带的 `child_job`、`child_started` 校验四条 native fence，并未要求这两个对象等于前一步取得的原始 `cjob`、`started[(worker, incarnation)]`。因此审计证据中可以把另一 UID 的 preserved-completed fence 与当前 child 的 WAL/Consumer 安装拼接。最终结果仍报告当前 child UID，失去“同一个已完成缓冲在 producer 死亡后仍被保留”的完整交叉绑定。

已执行的无 I/O 反例：复用 `test_buffer_fixture.scenario(None)`，保持原始 parent marker、nonce 与实际 child `e0-j000000002`；把 release 中的 `child_job.job_id` 改为 `e0-j999999999`，四条原生证据里的 preserved UID 同步指向该外来 UID；仅 mock `read_reference` 返回这些内存行。`validate_release()` 返回成功且 `job_id=e0-j999999999`。输出：`accepted=true, neural_calls=0, signals=0`。这证明存在实际缺失的校验，**不表示正常 controller 已产生错误数据**；正常 `poll()` 当前确实填入正确对象。

最小修复：让 `validate_release()` 显式接收可信的 expected child job/started（或 child marker 的 SHA 和可解析的原始 dispatch/start 行），在 `validate_fence()` 前要求完整对象与 nonce/owner/slot/inc/PID/start-ticks 一致。在线 controller、等待中的 parent 以及独立 audit 都须使用同一绑定；audit 至少直接要求 `release['child_job'] == cjob` 且 `release['child_started'] == started[(cjob['worker'], cjob['worker_incarnation'])]`。增加“完整合法 fence 属于另一 UID/另一 incarnation”负控，而不仅是 forged boolean。

## F2 / P2：8 TB raw-root 只做字符串前缀判断，可以逃逸指定磁盘

位置：`build_buffer_plan.py:40-44`；实际写入入口 `run_buffer_fixture.py:39-59`、`resident_supervisor.py:59` 没有补充指定磁盘校验。

已执行的纯函数反例：`build(..., raw_root='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/../../../../tmp/revtrace-wrong-disk')` 被接受，POSIX 规范化结果为 `/tmp/revtrace-wrong-disk`。计划仍生成四个 raw-result 路径。当前 README 的直接正式调用还能传入任意 `--out`；没有启动器检查的话，raw/evidence 可实际写到指定盘之外。未执行任何此类写入。

最小修复：计划构造时按目标 POSIX 路径语义拒绝 `..`，或规范化后要求位于指定绝对 results 根下；Linux 实际启动时再用 `Path.resolve().is_relative_to(...)` 检查真实路径，覆盖 symlink。对 `--out` 做同样检查并要求它等于冻结 cell 的 raw-result 位置。不能只修 plan builder 而保留任意实际输出位置。

## F3 / P2：直接 fixture 调用没有独立硬墙钟上限

位置：`run_buffer_fixture.py:58-59`、`resident_supervisor.py:36-48`，特别是 `:45`；NN 的 `resilience_transport.py:96-103` 是已有冻结依赖。

fixture 的 parent/startup/service deadline 都依赖 Python 控制循环继续运行；共享清理的 `nvidia-smi` 调用无 subprocess timeout，NN `wait_cuda_release()` 的两次 CLI 调用同样无 timeout。某次 CLI 阻塞会使其后面的 20/30 秒循环期限无效；此时 controller 也无法继续 poll。当前直接 `python run_buffer_fixture.py ...` 路径没有独立 watchdog。**没有观察或制造实际 CLI/GPU 挂起，此项是可定位的执行边界缺口，不是实测失败。**

最小修复：正式 fixture 四试验启动器应使用外部进程、冻结 `maximum_process_seconds`，在独立循环中执行硬超时，并按本次登记的 PID/start-ticks/Owner group 清理及记录失败。现有 `run_resident_campaign.py:29-42` 的外部墙钟机制可参考，但它的正常两 worker 条件不适合直接复用有替换 worker 的 fixture。共享 harness 中新增 CLI timeout 后必须重新冻结其身份；不要修改 59 文件 NN 来掩盖已有依赖。清理须只杀本次登记组，不能对所有 CUDA PID 执行全局 kill。

## 已核对的正向实现

1. spawn/monkeypatch 路径真实有效：Owner 导入的 `start_worker` 是 `resilience_transport` 定义的函数，调用时读取该模块全局 `worker_entry`；`timing_owner_entry` 在同一模块对象上替换它，spawn 目标是可导入的 `buffer_fixture.timing_worker_entry`。它再调用原始 `stage_worker.worker_main`，没有替换 full pipeline。现有 CPU spawn probe 直接测试 timing worker 入口，Owner patch 的单测另有覆盖；两者本次只读审查，没有把它们称作已执行正式 spawn gate。
2. `TimingFramedSender.put()` 先执行原始 `super().put(event)`，再建立 immutable marker 和等待。父目标是完整 ASR 帧发送后、callback 返回前；原始 `CandidateBridge` 之后才继续 correction/update。child 完整结果也先发送后等待。`record_resources=False` 被明确冻结并拒绝开启，避免资源快照造成 marker/原始事件 fingerprint 分歧。
3. 正/负目标使用原始 `BAC009S0908W0369`，parent end 分别为 24000/32000；历史 complete-state SHA 仅作为当前运行必须重现的前提，没有直接用历史输出替换新结果。
4. controller 的正常 kill 路径要求原始 dispatch、两条原始收到事件、Owner 的 `actual_original_full_conditional_closed_node` publication、nonce、PID/start-ticks、slot/incarnation 和语义 payload hash。仅有 marker 或 raw completed 不足以 kill；它不直接写 Canonical/WAL/Consumer。
5. controller 正常 release 要求原始 OS exitcode -9、CUDA release、joined/closed result/control、sealed old-channel、worker_lost 保留 completed UID、replacement/incarnation fence，且检查它们的时钟顺序。父进程还重新读取引用的原始行校验。这套链条应保留，F1 是缺少目标交叉绑定，而不是应删除这些检查。
6. 正向最终检查要求原始 old job/birth/inc 完整对象、record/end-state 字节语义相等、原始事实链及 post-fence Canonical install + actual Consumer。负向要求同 frontier 的完整输入不符 proof、原 old UID 不得安装；后续新 UID 会透过已经绑定一次的 marker，原始正常重算不会再次被 barrier 卡住。
7. 可选 follow-up 走原始 resident 的 actual EOS 闭环准入、每 request 原始 500ms/EOS obligations、完整原始 reference 和同 Owner 检查；未构造重复 source alias。结果标签明确是一个受控交错，不宣称自然 prevalence、调度性能或长流质量。
8. 清理没有全局杀 CUDA PID 的代码；controller 只对绑定 child 发送 SIGKILL，shared harness 正常清理针对登记的 Owner process group。已有 `kill_owner_group` 会把其他 CUDA 进程视为不能确认全空闲而失败，不会主动杀它们；因此正式运行仍应先确认独占 GPU，并让外部 watchdog 只处理本次拥有的组。

## 需要由正式验证关闭的范围

本审查未运行正式 CPU suite、四次真实 NN 或可选 follow-up，因此没有“缓冲实际存活/安装成功”的实验结论。建议在 F1/F2 与外部墙钟启动机制落实后重新冻结 fixture/harness，完成 nonce/identity/path/watchdog 负控，再按固定四试验保留所有触发失败、负例和原始证据。若新数据未复现冻结的精确-state SHA，应当记为本受控 site 失败，先做同输入/重复运行/合法原始 reference 对照，不得改历史 hash 或放宽 whole-state equality 来获取 PASS。
