# 角色受限反馈污染64正式单元：C1的可观察未来损害与边界

四段预先冻结的历史开发音频×四个实际方法×clean/coherent Proposer×两次
fresh process=64；两轮8单元pilot不入正式分母。实际同一输入的原生前奏/
候选Z均匹配；32组clean/corrupt配对及32组跨重复规范化Canonical历史
核对完成。1315原始文件123,206,933bytes留8TB；压缩原始包8,956,959bytes，
SHA256a29f2900759c522255b744e4c6be45ebabcb8557a65472fcbadb97ef20d90670。
原控制器9754/start471652164与128个Worker退出；GPU队列关闭。

原始收据/实际输入/选择证据/Consumer/WAL/完整功率窗口均通过独立只读
核验；960个原始Worker完成批经CPU处理链核对，真实神经phase952次，
其中128次是实际执行并计费的诊断参考，不冒称服务请求。最终P/Z/Y
只是解码已记录ID；没有以CPU重解释冒充新父状态下的模型生成。

## 主要结果（每格8corrupt cases=4音频×2次重复）

|方法|未来Private实际输入含载荷|暂时Private可见|未来Canonical模型输入含载荷|最终子串/完整三词实体|clean→corrupt WER|
|---|---:|---:|---:|---:|---:|
|Renderer-only弱候选写入|8/8|8/8|8/8|8/8；4/8|3.540%→10.619%|
|Strict正确上下文+实付Fallback|8/8|8/8|0/8|0/8；0/8|3.540%→3.540%|
|RevTrace独立FP32选择|8/8|8/8|0/8|0/8；0/8|3.540%→3.540%|
|完整Standard|8/8|8/8|0/8|0/8；0/8|3.540%→3.540%|

每次重复的四条独特文本共226参考词，弱路径8→24词错；合并重复为
16/452→48/452，不能把重复算成8段独立声学来源。三个受保护方法每次
重复均8/226，无该载荷造成的最终词错增加。这不是线上72单元的764词
分母，两个协议不能因16/48恰好相同而混用。Metadata-only复用同一个
一致候选trace作shadow，不是额外第五种GPU或能量样本。

低信任能力只改变自己Proposer的六个内容字段及其未加密checksum对应
清单；不改Job/Parent/audio/runtime/Authority。Renderer一致性不产生
trusted-selection证据。负控故意省略选择，因此不是完整Standard，
也不是当前完整RevTrace存在未修漏洞的证据。客户端仅显示Y的路径无
服务端反馈写回，依旧判不可达；同UID部署不提供OS/TEE隔离保证。

## P/Z/Y揭示的真正机制

所有受污染case的8s Private确实在处理后模型输入中消费载荷，且暂时
可显示它。后续Private与真实Authority的新增神经Z都没有重新生成完整
冻结三词子串；载荷由Adapter前缀/P投影携带，进入弱路径未来真实
神经条件输入并留在最终Y。实体形态变化使完整三词检测只中4/8，而
预冻结substring指标为8/8；两个读数同时保留，不改payload追求更漂亮
结果。结论是**实际反馈消费和可观察最终识别损害**，不是神经放大、
永久不恢复或任意攻击成功率。保护的是Canonical写权限，不是所有
Private内容的可信性。

## 实际代价与停止

下列是6s目标选择动作的真实神经phase总时间中位数；不是在线吞吐、
P99或系统能耗优势。每种方法的8个原值、全case功率与Worker初始化
另存。完整操作耗能已包括原生候选、两次真实FP32诊断及所有Fallback。

- strict-clean: 0.072000s。
- strict-coherent-proposer: 0.652003s。
- revtrace-clean: 0.583162s。
- revtrace-coherent-proposer: 0.579581s。
- standard-clean: 0.583799s。
- standard-coherent-proposer: 0.589354s。

Strict clean8/8一次验证通过，corrupt8/8实际完整Fallback；受保护选定
完整Z/P与两个独立同输入FP32Oracle一致。验证可以合法省工作，也会
支付拒绝代价，不能笼统说它不如独立生成。全操作者成本保留诊断工作，
不能用warm目标phase替换真实在线服务收益。

功率测量v1边缘支持不完整如实保留；measurement-onlyv2同8输入重复
证明原生输入/Z/P/Y/Stop未变后才开64正式单元，正式所有功率窗口支持
完整。两个CPU辅助工具的导入/schema错误及修复保留，不重跑GPU。
本方向以边界证据GO收口，不再扩音频/载荷或发明调度名字。新CDE
性能NO-GO不被本C1证据推翻。原稿仍未修改，接着生成独立候选。
