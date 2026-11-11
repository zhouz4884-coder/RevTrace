# baseline v2：独立守卫与事件顺序只读审查

审查对象：clean source `14ae77ee2f1f0c324be3f40b89fb6011972c35b9`。本次只读`retention_policy.py`、Owner入口/派发/hint路径、`fullspec_policy.py`、`versioned_policy.py`、`test_uir_policy.py`及实际Owner CPU fixture。没有修改或重跑该冻结源。

**未发现须在GPU pilot前修复的新增AU/durability/SUP或Ready-only边界缺陷。** 这不是whole-program正确性证明；原模型、加载、CUDA进程生命周期与实际异步时序仍需原定GPU pilot验证。

* UIR只抑制cooperative C-entry提示；实际Owner的arm校验、coordinator选择及conditional派发均包含`uir`。它仍调用 inherited invalidations，返回的完整结果仍经原`_reason`和真实parent `_commit`；新code没有绕开durable hook、Consumer SUP、channel/incarnation或terminal lease。
* Ready-only的定义已精确收窄为Owner已验证完整receipt。先收到完整socket frame但未在Owner出队处理，不算ready。每次串行install后给仍在`self.jobs`的call写policy fence，已在`completed_full`的原结果只在真实parent成立时安装；session epoch与policy token分开。
* `complete_receipt_order`在完整receipt验证后、实际install前获得统一policy sequence；`canonical_install_order`在实际`Reconciler.install`紧后生成。它们允许同一perf时间戳时的无歧义比较。
* Owner的`validated_full_receipt` journal row在`policy.receive_event`返回后写入，而实际install可能已经发生在该函数内。因此不能拿此journal row的`observed`与install时间直接判断ready先后；以嵌入的统一sequence为准。当前代码的Owner journal `canonical_install` row随后才写，不能把日志写入顺序误当动作发生时间。
* `other_ready_full_receipts_before_install`不含正在安装的chosen item：ready bank pop先于`_commit`，该item的receipt order在result中单列。新字段名字已准确反映此点；消费者/分析器须使用该字段，不再读取旧`ready_full_receipts_before_install`。
* Unsafe UseAll仅在CPU test里直接调用低层install构成反例，没有导出为合法online arm；不能把它的反例说成safe UIR的行为。UIR若同效，只回答cooperative提前停止无已证增益，不证明共享的使用前资格/AU/SUP冗余。

已有CPU控件分工足够支撑进入限定pilot：helper测试比较真实hint转发/抑制；coordinator测试完整非法结果discard、合法跨birth结果选择、直接AU拒绝、session fence；Owner fixture贯通真实Owner→FactStore→SurvivorConsumer及ready receipt顺序。没有必要为了凑测试数再写镜像断言。必须保留的pilot观察是：真实before-C取消点是否到达、UIR无用计算实际占用、完整IPC收到/Owner出队顺序、两GPU计费、实际Consumer反馈、物理退出/CUDA释放，以及所有offered/EOS和控制失败。

新loader observer/forced recovery fixture**不在这个冻结source中**。若后续纳入，要独立新commit/完整manifest及对应窄CPU验证，不能用此v2 gate给其背书。`LOADER_CONTROL_REVISION_v2.*`已经分别规定微诊断、受控故障/no-fault与自然主矩阵，不给五臂UIR比较添加隐含强制call或重采样。
