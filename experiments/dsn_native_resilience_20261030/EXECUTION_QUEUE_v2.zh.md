# 执行队列与当前实证身份

2026-10-30，本文件是运行交接索引，不是完成声明。以每run的冻结配置、RUN_RECORD、实际GATE和原始B盘记录为准。Root负责论文/最终Git；execution_continuation持有CURRENT与唯一NN窗口，未经新授权不push。

- 本地旧根HEAD7372133及dirty内容保留，不pull/reset。
- 最终候选native源码：`source_v2`，实际commit `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`，完整59files，manifest `packages/SOURCE_v2.json` SHA `60ae549fcc98165a74e5a3dc420bf93418296099fa12b410572b15d281b2c457`。相对9492仅long_reference生命周期/流式持久化+4CPU，以及trial/worker/longref的allocator观测字段；原NativeBridge/C/U/协议guards未改。
- `FROZEN_ENVIRONMENT_v2.json` SHA `bd09660f15b61bc173ddab57cea2d03fccc9ebd8eb97ddb485d6132cae90733d`，原packages/FP32/TF32禁用不变，新增唯一已验证allocator条件 `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`，别名 `PYTORCH_ALLOC_CONF` 为空；两个arms、每worker/replacement、独立reference均相同。
- `RUNTIME_PREREQUISITE_v2.json` SHA `69fd0f33cbee6f1fe58e07411cf2a4a76c1e1a0148f0847ee8a8ceea08a0447b`：253 Linux CPU零skip、26 model assets共10,099,049,234B全SHA、原authorBBB三文件/source/env/audio通过。其历史config是`SHORT_PILOT_v2`，该6格没有NN执行，不能改标为formal28完成。`7bbdc804e3d4985ff4e5cd84cb0bd07e7a3bee581d035bd290bbbc593f3f1181`另外指long-launch readiness gate，不能混作runtime prerequisite。
- 所有模型/env/audio/cache/raw大日志仍在 `/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9`。唯一SSH路线是本机approved helper的`ssh_client()`，不读/输出凭据。

## 已完成但不同scope的证据

- 旧9492开发6真实trials均17步完整任务通过，154files35,494,736B已全SHA收集。c4dde9 checker的6actual+35控制全部通过；这些保留9492身份，不重标为4f正式36格。
- short85固定参考已真实CPU导出：`SHORT_REFERENCE_EXPORT_RESULTS_v1`，DETAILS SHA `db1d90dc445ed9e63e9fe201e462e25bc8e2ae464bac002fc33ff25d5baa5785`，GATE SHA `9fc54b1d146f6c3da50e757e68f3aae2d7f9781bf2c17e4ca3dc449c6c1cd2cf`。原17+68 bdfa source markers全部保留，未把旧99重标。
- 原9492 long reference在S0770第95边OOM，旧94完整cuts仅在RAM、并未落盘；`LONG_REFERENCE_OOM_RESULTS_v1`8files587,812B保存此失败，不能声称这旧94条完整语义已核验。
- 独立diag_v1（a145）default95两fresh均94步后同95OOM，失败完整input SHA80cebc…相同；两个同输入95的原full_step均成功且end hash相同。
- diag_v2（a214）额外GPU storage观察器遇稀疏alignment buffer缺陷，原失败保留，无96结论。
- diag_v3（99f7）release-g默认allocator保住95，190严格语义配对全相同，实际最多释放约284MB，但96仍碎片OOM。release+expanded96随后真实PASS，额外与新95前缀匹配，共285完整start/end/C/IDs配对无投影。92files16,979,196B全部SHA收于`LONG_MEMORY_DIAGNOSTIC_RESULTS_v1`。它们是定位/环境控制，不是875全长或serving结果。

## 正在运行的全长参考

`LONG_REFERENCE_HANDLE_v2.json`：PID2187139/start510560842，UTC10:19:58。冻结plan在相邻sustained目录，SHA `2319d3c09a1415dcfe2ef072d5c5ad2a64219a7517cc2e109275db69555527da`。

两条合成连续输入S0770/S0903，各24原clips、228.51025/208.1003125秒，48 utterances、2 acoustic speakers，不称自然连续录音。原作者engine先连续insert/infer/export，步间不restore；然后每个实际原start恢复重跑，同GPU/同loaded original model，全875+875。只取最终原source4f整字段/C/IDs，无source marker投影。每完整边fsync，下一原输入亦先持久化。首不一致有原计划固定重复/连续legal-oracle控制。

观察CLI：`python -B experiments/dsn_native_resilience_20261030/ops/poll_long_reference_v2.py`。有需要再用`observe_long_boundaries_v2.py`，不要频繁poll或做性能前缀解读。最新已确认S0770连续458+restore458、mismatch0，S0903连续203/417时仍运行。S0770原continuous真实buffer shifts398/context改变353；派生`context_bound_still_exceeded342`必须保留，sustained_state正在解释它与真实_current_tokens的定义差异，不能据此直接称跨448硬界。

## 后续必须自主完成

1. 全1750成功且进程/GPU物理释放后，运行`ops/collect_long_reference_v2.py`。只收bounded summaries、comparison、telemetry与SHA索引，大DETAILS/JSONL留B；Gate必须875+875严格PASS。若硬门失败，保存并按同输入/重复/合法原oracle定位，不换来源或缩短875。
2. 正式短28已冻`FORMAL_SHORT28_v1_FROZEN.json`，SHA `dccc597b1b6b961439cfd85e158aa2beeb92ac52c1a300605502f175e3805c6f`。24主+4回归，原D2/C8/EOS/all-offered/max240，seed2026103031、r1换GPU/反序。
3. 独立formal operator_v2：`ce743ddab24112fa62bb32456011dfbafb558cbb`，5files，manifest SHA `705daddd78d9f4db7efe976d2d5570055753133752f8ba5ba47ee2bbc860d693`；26本地CPU零skip已通过。验证每cell引用同campaign reference、实际Consumer每durable fact恰一次、两初始及全部replacement worker actual allocator ready receipts。只读快审未发现short28阻断；long stage不可复用short85上传器。
4. 全reference结束后，先用`activate_source.py`切`CURRENT_FORMAL_OPERATOR_CANDIDATE_v2.json`，新record/backup名；再`stage_formal_operator_v2.py --execute`。该步骤只做short28/source/真实Linux26和inputs，绝不NN。需要CURRENT operatorce；输出`FORMAL_OPERATOR_PREREQUISITE_v2.json`。
5. 切回`CURRENT_RUNTIME_CANDIDATE_v2.json`并noarg。运行`launch_formal_campaign_v2.py --plan …/FORMAL_SHORT28_v1_FROZEN.json --label short28_v1`。用`poll_formal_campaign_v2.py --label short28_v1`仅看完整格数量/硬门，不解释性能前缀。Root无需再确认。
6. 用真实long Gate冻结`freeze_formal_long.py --freeze --version v1 --runtime-manifest …/SOURCE_v2.json --runtime-source …/source_v2 --reference-gate …/LONG_REFERENCE_RESULTS_v2/GATE.json --reference-gate-remote B/results/revtrace/dsn_native_resilience_20261030/long_reference_v2/GATE.json --reference-details-remote 同root/DETAILS.json`，并带同三个env参数（参考short命令）。2源×2arms×2fresh=8、max1200、原D2/C8/全部offered/EOS，不改界。
7. 短28完且GPU释放后，`stage_sustained_inputs_v1.py --execute`只stage新8configs/plan并重新核actual875 raw reference；复用operator26 CPU但明确保留它原short plan SHA，绝不改标。再`launch_formal_campaign_v2.py --plan …/FORMAL_SUSTAINED8_v1_FROZEN.json --label sustained8_v1`。
8. 两formal完整36格之后做独立实际trace/full-task/端点/paid-work重计、bounded collection与总Gate；cold故障原deadline失败及质量/未知/能耗全留。Root收齐后才更新完整10页DSN稿、编译/QA/Git；不在子任务停。

已有launch/stage helper均outside frozen source；不编辑source_v2或重标旧run。新代码修复必须新commit/manifest/source，重新必要CPU/环境门。每run保留unique ID、config/env/source hashes、raw/summary/decision路径。
