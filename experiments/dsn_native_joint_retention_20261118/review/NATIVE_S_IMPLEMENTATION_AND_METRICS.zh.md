# Native S 消融：实现边界、指标及CPU前置

本文件是只读源码核查与实现建议。未改旧运行时、论文或执行GPU；未把下面的建议称为已运行结果。

## 1. S开关应放在哪里

实际路径为`resilience_trial.run_trial → SurvivorConsumer → Reconciler`，不是旧`stage_service.py`。

- `baseline_source_v3/resilience_consumer.py:9`把每个实际Consumer状态硬设为`Reconciler(..., True)`。
- `feedback_contract.py:56–72`已经实现独立的`retain`参数。`install`先根据旧steps与实际完整next_cut计算`compatible`，再按`compatible and retain`决定只删除覆盖前缀还是清空steps。
- 最小新源改动是给`SurvivorConsumer.__init__`加严格bool参数，默认True；`resilience_trial.py`从冻结配置传入。建议字段命名`consumer_retain_compatible_views`，防止被读成“关闭支持检查”。必须拒绝字符串`"False"`等会被`bool(...)`静默转True的值。
- S0=False在canonical应用时回到已认证快照；S1=True保留完整匹配、仍受支持的ahead后缀。两个模式都允许原先合法的Private首次发布。
- 不修改`_fact`的receipt/source/parent/full-result/durable-order检查，也不修改Private完整连续链验证、epoch/FIFO/重复消息屏障。Owner的FullSpecCoordinator.steps仍按原R策略维护，避免把S消融同时改成计算保留消融。
- R轴保持既有`arm=fullcall`与`arm=ready_only`。另加S字段/因子标签，不要用现有arm白名单不认识的`fullcall_s0`绕错入口。Ready-only当前配置本身没有S开关，不能只把arm改名就声称完成消融。

## 2. 两个容易漏掉的实际执行点

### 2.1 Canonical后紧接着一次Private快照

`resilience_owner.py:outcome`在canonical outcome上依次发送canonical publication和`view_event_snapshot`。因此S0清空ahead后，后一个实际Private应用可能很快恢复同一view。这个窗口可能很短，但应以实际Consumer的`observed`计量；不能假定一定等到下一次模型完成才恢复。

每次canonical应用至少保留：旧tip/新canonical完整身份、旧/新可见frontier、完整输入边界是否匹配、实际观测时间、随后实际恢复时间、是否遇到新canonical边界。不要用Owner emit或worker model_end替代实际Consumer时钟。

### 2.2 新源commit与严格参照

新协调源的commit可能进入`contract.stage_execution.source_commit`，从而使旧de0936 strict reference在metadata层不同。不得把新执行源标成旧commit。最稳妥的是沿用已有原程序reference generator，在新冻结源下产生所有四臂共用的新strict reference。若使用字段映射，必须预先声明并证明仅有原程序标记字段变化，实际协调commit仍单独真实记录；不能临时删除字段让比较过关。

## 3. 现成审计器如何适配

`opportunity_audit_source_v1/consumer_audit.py:audit_consumer`目前把重建的Reconciler硬设True，末尾逐字段检查真实row与预期状态。因此它会拒绝正确实现S0的轨迹，需要在新冻结审计源中参数化。

最小方案：初始化为配置的S值，其他dispatch/ASR/full receipt/step-kind/availability/durable身份检查全部保留。现成`Reconciler.install`返回的`compatible`由变更前steps独立计算，不依赖retain值，可以直接分类S0的兼容丢失。若增加独立分类器，则按序列化完整边界与连续依赖链直接重算，作为对共享Reconciler实现的交叉核验。

必须区分：

- `compatible_ahead_applications`：新canonical实际应用前有非空ahead视图，且完整边界相匹配。
- `avoidable_supported_view_losses`：上述兼容机会发生实际frontier下降。
- `necessary_incompatible_withdrawals`：被完整实际边界否证的ahead视图发生下降。
- 其他frontier下降（如空文本特殊处理、非ahead已选文本被原程序修改）单列，不能因分类器未覆盖就自动计为必要或可避免。
- 计数单位是应用边界机会，不是去重view身份；同一view在不同应用处可能出现多次。

轻量`resilience_metrics.consumer_audit`只验证durable facts的Consumer绑定，不验证全部Private路径；它不会替代这个完整支持审计。

## 4. Gap应给两本账

### 与H3表可比的全部frontier回退面积

H3的`aggregate_service_v5.py`使用每source历史可见frontier高水位，按实际时间积分`(high_water - actual_visible_frontier)/16000`，到原service end。它包含必要与可避免回退。不可直接命名为“unnecessary G”。

应报告全体回退次数、每次初始移除音频秒、总历史高水位缺失面积。全体面积按一条实际状态曲线积分，不能把多个重叠episode的面积简单相加。

### 完整支持分类下的同root丢失窗口

OPV1的`definitions.loss_window`从一次已分类下降开始，对旧tip与实际后续frontier的差积分，到恢复旧tip或下一次canonical应用为止；遇到新canonical边界/末尾会显式right-censor。此量更接近“仍合法的进展在当前支持窗口内丢失多少”，但不是跨任意后续root的完整面积。

因此总Gap与compatible/necessary窗口面积应并列保留、名称不同。首次D2/C8信用仍按原accepted obligation只算一次，撤回/恢复不重置时钟或重复计分。

## 5. 有意义的CPU前置控制

1. 同一个兼容ahead fixture：S1保留tip，S0清空到canonical；认证frontier、durable事实及C/U记录相同，S0仅产生可避免view丢失。
2. 同文本但完整状态不同：S0/S1都撤回，不能只用字符串判断支持。
3. 无ahead fixture：两个S模式输出相同，没有虚构激活机会。
4. 两S下均检查旧Owner publication、重复/跳号、伪造receipt/source、错误full-result身份仍被拒绝；不得以S0绕过完整路径检查。
5. Canonical后实际Private快照恢复：计数一次下降，积分到真实恢复，不把Owner发送时刻当Consumer显示时刻。
6. 多次部分恢复及重叠下降：全体高水位面积不重复计；同root窗口在新canonical处截断并保留删失标签。
7. 同一offered interval多次显示/撤回/恢复：首次credit最多一次，全部原offered/EOS分母保留。
8. 真实row文本、frontier、canonical_sha或private_job与实际完整路径不符必须使审计失败，而不是把它转成“无兼容机会”。
9. 每个R/S arm的完整selected state、原纠错和返回token IDs同strict reference核对；计时、worker区间和缺测神经阶段各保留原口径。

## 6. 实验解释

单独补Fullcall/S0只能识别固定R=1处的S简单效应。要称原生完整2×2，需要同期同新源的Full/Ready × S0/S1四臂；Conservative若另测，是额外锚点而不是同一个R0定义。

旧pilot只有少量兼容ahead应用，故技术pilot应先报告真实机会密度和实际损失窗口。无机会不等于审计失败，也不等于协议无效；不得通过关闭安全检查、sleep、错误donor或强制同文本制造机会。若S0产生损失，展示全输入/原输出保持与实际Consumer窗口；若差异很小，按测得的机会与时间尺度报告，不把计数放大成额外吞吐收益。
