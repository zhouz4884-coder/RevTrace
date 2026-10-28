# 实际交互机会重计

`interaction_opportunities.py` 只读取已有本地完整记录，不导入运行时、不运行模型、不修改冻结源、冻结汇总或论文。它回答“实际出现多少可见进度保留机会”，不是新的性能实验或安全认证。

同一实际 Canonical `commit` 分列两个时刻，**不得把两套行相加**：

| 时刻 | 提前可见的定义 | 用途 |
|---|---|---|
| `owner_install` | `t0 + commit.installed` 之前已被 Consumer 观察到的最后一个视图 | 安装时已经可见的机会密度 |
| `consumer_apply` | 同一 version/F 的 Canonical 帧被实际 Consumer 应用前，FIFO 中的最后一个实际视图 | 显示策略真正面临的保留/撤回机会 |

分母始终是该 source/cell 的**全部实际 Canonical 更新**，不是只挑发生回退或可保留的更新。`matched_consumer_updates` 单列精确匹配的实际 Canonical 帧；缺失 Consumer 记录不从分母删除。完整文件缺失的 cell 留在 `COVERAGE` 中，并使分析 gate 为 incomplete，不能把缺失 cell 当成零机会。

一个 `ahead` 视图须满足此前实际 `valid_visible_frontier > new F`。脚本从该视图对应的真实 `display` 事件得到 Private job，再沿完整、已实际发布、同 session/source/contract/generation 的结果回溯：每个前驱的 `state_tokens` 必须逐 token 等于后继实际使用的 `prompt_tokens`，且前驱结果已在后继 enqueue 前收到；最终必须接到实际完整 Authority 结果选出的新 `(F,P)`。根边界采用 `chunk_id/end_window`，不能把绑定旧 Canonical 的 `audio_start_sample` 当成 Private 反馈边界。记录中的 `compatible_provisional_retained` 仅列出供比对，**不参与兼容性判定**。

选中 Authority 缺失/不匹配、缺失完整 Private 结果、前驱歧义或无精确视图来源均保留为 unresolved，连同原因和已走过的 job 链。部分输出、取消回执、未来才得到的结果及别的 source 的相同 token 不构成证明。脚本不为未生成该工作的 arm 构造反事实机会。

主要计数与比率：

- `ahead_updates / canonical_updates`：可见 ahead 的出现率。
- `compatible_opportunities / canonical_updates`：完整链与新 root 精确兼容的实际机会率。
- `compatible_opportunities / ahead_updates`：ahead 视图中可兼容的比例；unresolved 仍留在分母。
- `compatible_retained`、`compatible_cleared`、`compatible_changed`、`compatible_unmatched`：该兼容视图实际保留、清除、变成另一 ahead 视图或无精确应用记录的结果。
- `incompatible_cleared`、`incompatible_still_visible`：精确不兼容的旧视图实际清除或仍可见。它们不替代独立安全审计。

安装时另列实际已 enqueue、结束边界在新 F 之后的 `install_inflight_ahead_jobs` 与 `install_complete_unpublished_ahead_jobs`，并保留 job ID。完成时刻取实际完整行的 worker terminal 时钟；取消作业取取消确认时钟。这些是安装处的**作业出现次数**，同一作业可能跨多个安装被计数；尚未发布的作业可能已逻辑失效，绝不能把这些数量称为可计算复用机会或性能收益。脚本没有证明未完成计算能保留。因此“没有 visible-ahead”只能说明该时刻没有可见显示保留机会，不能推出没有计算保留机会。两项计算计数仅定义于 owner-install；Consumer-apply 表中为 null。

产物：`UPDATES` 保存每次安装/应用的证据与 unmatched 原因，`SOURCE_OPPORTUNITIES` 保存每个 source 两套完整分母，`STRATIFIED_RATES` 按 phase/adapter/rho/arrival/cohort/repeat/arm 分层，`SAME_CANONICAL_HISTORY_GROUPS` 只列同 paired block/source、同实际 Authority runtime、同完整 F/Z/P/text 历史的真实成员。后者没有效果估计；不同历史的分层率可以描述，不能直接解释成同历史的因果收益。`ANALYSIS_RECORD.json` 记录脚本哈希、输入文件哈希、命令、Python 环境、完整性 gate。

待 H3 完整原始记录已经落到本地后使用：

```powershell
python -B experiments/physical_retirement_20261028/analysis_tools/interaction_opportunities.py --plan experiments/physical_retirement_20261028/confirmation_design/PLAN_v3.json --results-root <本地完整confirmation_v3目录> --output <独立分析输出目录>
```

当前仅对 `service_opportunity_v2/{covered,row_complete}-F2-r{0,1}` 四个已有 bounded pilot 做了本地控制性重计，结果在 `interaction_bounded_check/`：每套时钟各 540 次实际 Canonical 更新，6 次可见兼容机会，全部实际保留；owner-install 另有 53 次在途 ahead 作业出现及 2 次完成但未发布的 ahead 作业出现。每个 cell 的 Consumer-apply 机会分别为 covered-r0 `2/135`、row_complete-r0 `0/135`、covered-r1 `2/135`、row_complete-r1 `2/135`。这些是**受控 F2、同 16 源两次重复**，不是 H3 自然发生率，也没有用跨 arm 的未知 Canonical 历史声称效果。

这一控制结果说明：只报零回退会遗漏大部分安装没有可见交互机会的事实；6 次保留本身也不足以证明组合优势。H3 若低密度且各 arm 收敛，是正常工作边界；若同实际 Canonical 历史、反复存在可证兼容机会时组合仍不改善实际停顿/撤回，则组合主张减弱。精确不兼容时撤回是必要行为，不能拿零撤回作为目标。仍须把机会率与独立质量、deadline、能耗及停顿结果联合解释。

最小验证：`python -B -m unittest discover -s experiments/physical_retirement_20261028/analysis_tools -p test_interaction_opportunities.py -v`。六个控制覆盖伪造 bool、错 session、partial/missing/future result、歧义 ancestry、逻辑反馈边界，以及 publish-before-install / observe-after-install / before-Canonical 的双时钟案例；另验证缺失选中完整 Authority 仍保留 Canonical 分母而不生成兼容证明。
