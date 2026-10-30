# v2开发控件定位：两个fixture过早触发正确守卫

27项中25项通过；两项并非不变量被突破，而是测试尚未到达它想测的边界：

* 最终root别名fixture按固定index选中了Canonical publication，被“publication改变原durable事实”守卫提前拒绝。v3改为找出root=1的private snapshot并只修改它，从而专门检验其绑定实际Consumer当前root。
* 三域epoch fixture先发送过ASR，又重复调用project，因此先触发“ASR非首次owned阶段”去重。v3在发送ASR之前做session fence，使该事件确由session域而非重复阶段被拒绝。

所有旧失败记录保留。v3不改变模型转移、不删测试、不扩大接受条件、不改变两个BFS profile及state cap；这次只窄修fixture。没有模型/GPU或真实服务结果受影响。
