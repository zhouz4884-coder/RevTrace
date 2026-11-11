# 当前六臂服务入口审计：旧三臂代码是否被调用

2026-11-11，独立只读call-path审阅。实际对象：runtime `de0936b2e30179d63aeef6e235cd1af685578c58`、driver `f367c4e1068a9391a0e99d8537c94995a3388e13`、support `a13fa0a335529dc188f7e738877a3acd027ce4a7`。没有启动CPU/GPU测试或模型，没有修改任何冻结source、reference、config或CURRENT。

**结论：用户发现的旧三臂限制真实存在；如果调用旧入口，新臂确实会失败。但当前已冻结f367的handoff第6步、其实际Popen命令及整个transitive live调用链，均不调用那两个旧入口。没有发现由此要求修改de0936或重做已生成reference的缺陷。** 服务尚未启动，本结论是源码可达性与已登记CLI的审阅，不冒充实际服务进程执行证明。Root最终发出的命令仍须符合下述具名入口合同。

## 1. 旧入口确实有限制，不能简单扩展arm白名单

- `baseline_source_v3/stage_service.py:35` 的实际函数为 `run(config_path,manifest_path,out)`；第39行只接受 `two_full_early/two_full_spec_early/ready_handoff`，同时限制source数≤2。其 `__main__` 在第172行之后调用这个旧run。v2与v3该文件字节未改，所以查看v2指出这一点是有效警示。
- `baseline_source_v3/run_service_campaign.py:62` 确实构造 `stage_service.py` 子进程；第70–72行在pilot_thresholds存在时要求恰好3条旧arm结果并做旧机会筛选。

如果把新五主臂+辅助臂配置交给这条旧campaign→stage_service路线，它会失败，也不具有当前完整的Owner/FactStore/SurvivorConsumer路径。**不能为消除assert而把旧白名单改成六臂，这会把不同执行合同混在一起。** 正确做法是使用已冻结的新入口；旧文件保留历史功能和原测试，不改标签。

## 2. 当前实际CLI与模型路径逐级证明

已读取 `baseline_ops/PILOT_PREPARATION_V2/LAUNCH_HANDOFF.json` 的 `ordered_commands[5]`：

```text
python -B <pilot_driver_v2/source>/run_confirmation.py
  --plan <PILOT_PREPARATION_V2>/SERVICE_PLAN.json
  --manifest <pilot_driver_v2>/SOURCE.json
  --prelaunch <PILOT_PREPARATION_V2>/SERVICE_PRELAUNCH.json
  --out <PILOT24_V2>
```

根目录均在指定8TB。该handoff SHA为 `7d098db533cc5c557200f5d1eac35ed15c76e78623d1d81939f6e6eeef55a59e`，driver manifest SHA `c9c0fa0c14424fae51d3e822f35286ba69c28b11233fa6c2aef848a231ec724b`；runtime manifest SHA `ce99ca421f5f8b416a1545c57a600ee6a28f43e7d2c10294caa00f0d6636a7c9`。

| 层级 | 实际调用及固定代码位置 | 结果 |
|---|---|---|
| driver CLI | `run_confirmation.py:114–117`，CLI调用本模块run | 不是旧campaign.main |
| 每cell命令 | `run_confirmation.py:77` 明确构造 `base['source_root']/resilience_trial.py`；第78行把完整command和SHA写入cell PRELAUNCH，第83行Popen同一command | 没有stage_service替换或失败fallback |
| Supervisor CLI | `resilience_trial.py:180–182` 调用本模块 `run_trial`（定义在44行） | 与旧stage_service.run是不同函数 |
| Owner进程 | `resilience_trial.py:5` 导入 `resilience_owner.owner_main`；第82行 `ctx.Process(target=owner_main,...)` | 不经过StageCoordinator旧supervisor |
| 六臂选择 | `resilience_owner.py:25` 白名单为conservative/fullcall/safe_versioned/ready_only/dependency_versioned/uir；第122行选择相应coordinator；第124行共同RR dispatcher | 覆盖五主臂+辅助臂 |
| worker进程 | Owner第32行调用 `resilience_transport.start_worker`；transport第72行 `ctx.Process(target=worker_entry,...)` | 真实worker target有明确模块 |
| worker target | transport第67–69行在worker_entry中导入 `stage_worker.worker_main` 并传入mode=`authority` | 不是native_service中旧worker_main别名 |
| 完整神经调用 | `stage_worker.py:16` 构造CandidateBridge；第55–56行kind=`full`时调用 `model.full_step` | arm由Owner决定，不把六个arm名字当worker mode |
| 原ASR/C/U | CandidateBridge.full_step调用NativeBridge.step，继而原author engine.infer；共同before-C检查与早期view回调 | 不调用stage_service.run或旧campaign |

Supervisor实际构造的是 `SurvivorConsumer`，以当前facts.wal和完整支持验证处理publication；并非因为某些旧Consumer类仍在包内就切回旧服务路径。服务结束后的实际任务检查走 `resilience_metrics.analyze_trial`，严格reference_kind=`strict`的完整state/C/IDs门先通过，driver才继续外部审计。

## 3. imported helpers并没有暗中回调旧campaign

不仅检查文件名，还检查了当前driver实际调用的函数及这些模块的顶层行为。

### a13支持模块run_paired_campaign

`run_confirmation.py:47` 动态import support的 `common/external_power/audit_results/run_paired_campaign`。该模块确实还含旧的32格run和smoke8停止分支，但当前driver只调用：

- 第89/91行：`capture_ready_environment`，采实际worker allocator/PID环境；
- 第91行：`ready_rows` 与 `check_ready`，读取并校验两完整FP32 READY；
- 第104行：失败路径 `stop_owned_processes`，按PID-generation证明清理本trial。

这些函数逐一检查后，没有调用该模块run、native campaign或stage_service。模块的run仅在其 `if __name__=='__main__'` 尾部CLI中调用；作为import时条件为假。`audit_results.audit_cell` 是已有事实/实际Consumer端点和独立energy审计，不启动旧服务campaign。`external_power` 和 `process_cleanup` 顶层只有定义；其实际调用是NVML观察或已拥有进程清理，不产生legacy模型worker。

### native_service与native_worker

当前Supervisor/Owner/Consumer导入native_service的Journal/verify_source；offline power_metrics还复用Power.energy。native_service顶层会导入native_worker.worker_main这个**函数定义**，但其模型导入与加载位于函数体内，没有顶层调用。native_service.main/serve仅在它自己的CLI路径被调用；新transport的实际worker target明确是另一模块的stage_worker.worker_main。

### 包内旧测试和旧入口

对driver、完整66文件runtime和18文件support检索全部 `stage_service/run_service_campaign/native_campaign/run_trial` 引用：stage_service在新live路径中没有import/call；它的StageConsumer只被旧CPU测试导入。run_service_campaign的辅助函数被旧test_service_campaign导入，但没有把main接入新driver。225项CPU测试包含旧测试并不意味着GPU服务会运行旧CLI，也不能反过来仅凭测试总数证明入口正确。

## 4. 具名launch-path合同

当前允许链为：

```text
f367 run_confirmation.run
  → de0936 resilience_trial.run_trial
  → de0936 resilience_owner.owner_main
  → de0936 resilience_transport.worker_entry
  → de0936 stage_worker.worker_main(mode=authority)
  → CandidateBridge.full_step → NativeBridge.step → 原engine.infer
```

禁止把下列函数用作这批服务的入口/回调：`stage_service.run`、`run_service_campaign.main`、`native_campaign.main`、`native_service.serve/main`、a13 `run_paired_campaign.run`。允许复用前述明确的journal/source验证、READY/observer/cleanup和offline审计helper。每cell PRELAUNCH中实际command的脚本必须为当前de0936独立checkout下的 `resilience_trial.py`，对应config arm必须来自当前六臂集合；driver本身仍须f367完整manifest校验。

如果Root实际准备的shell命令或PRELAUNCH command不符合这个合同，应停止并修正launcher；不能自动fallback、改旧arm白名单，或用旧入口的失败结果冒称新五臂运行。**这种launcher修正不等于修改神经runtime；若de0936与f367字节不变，无需仅因此重生成新NN reference。**

## 5. 有针对性的CPU入口核验建议（本审阅未执行）

可在独立、另行冻结的外部CPU harness中增加具名 `V16_SERVICE_ENTRYPOINT_REACHABILITY` 检查，保持de0936/f367不可变：

1. 从实际新SERVICE_PLAN/handoff取得当前source/manifest/config，拦截driver的Popen而不创建子进程，断言所有六臂生成的脚本均是绝对的de0936 `resilience_trial.py`；完整命令与PRELAUNCH记录一致。
2. 将旧stage_service.run、run_service_campaign.main、native_service.serve/main和support.run_paired_campaign.run设为遇到即失败的poison；实际driver只允许调用列出的helper。阻断torch/transformers/CUDA、真实Popen和NVML外部命令，避免“入口测试”意外启动模型。
3. 用fake Process/context检查Supervisor绑定的target确为Owner；用现有实际Owner合成harness覆盖六臂和RR；另以stub stage_worker.worker_main验证transport worker_entry传入authority，停止于模型构造之前。不得用一次仅检查字符串的测试冒称整个神经路径已跑过。
4. 如需负控，证明旧入口在新arm下会被其旧assert拒绝，再证明它未出现在当前捕获命令/poison调用中。该负控是路由检查，不是新策略性能结果。

上述检查可为后续CLI回归提供明确保护，但当前静态审阅已经证明用户指出的旧三臂assert不在已登记live路径。是否追加外部CPU harness由Root协调；本报告没有为源码无关的兼容性重写制造新NN commit、重标签reference或新增GPU实验。

**最终结论：当前source-specific service入口静态审计PASS；旧三臂限制不是已冻结新六臂路径的阻断缺陷。保留Root对实际最终command、源和物理资源的正常启动门。**
