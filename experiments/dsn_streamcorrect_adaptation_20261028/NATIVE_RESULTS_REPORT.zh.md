# Native StreamCorrect：原定范围完成后的研究结果

实际完成2个自然见证服务格与12个正式服务格。四个来源全部保留；三臂、fresh-process两次、原500ms边界及原D2/C8不变。两cohort各6格完整Canonical状态/输出历史一致；这证明语义保持，不代表所有服务点达到SLO。

## 主结果：保留减少重算，但当前双会话500ms点过载

每臂offered音频66.42975s。原插值/all-offered重计：三臂均0/4整格满足D2/C8；强两完整副本sequential信用18.5s，drop12.5s，joint17.0s。Joint相对drop增加4.5s信用，但未超过强sequential。不能把本点写成native部署SLO成功或泛化性能胜出。

|cohort|repeat|arm|D99(s)|C99(s)|双期限音频信用(s)|
|---|---:|---|---:|---:|---:|
|A|0|drop|18.289|19.150|3.500|
|A|0|joint|17.201|21.408|3.500|
|A|0|sequential|8.381|8.381|0.000|
|A|1|drop|17.033|18.300|2.500|
|A|1|joint|14.501|18.868|4.500|
|A|1|sequential|6.752|6.752|3.000|
|B|0|drop|15.438|16.671|3.500|
|B|0|joint|11.327|16.948|4.500|
|B|0|sequential|5.081|5.081|8.500|
|B|1|drop|17.231|17.673|3.000|
|B|1|joint|11.736|17.257|4.500|
|B|1|sequential|5.736|5.736|7.000|

分层不可省略：A的joint−sequential信用分别为+3.5/+1.5s，B分别为−4/−2.5s；不是所有来源一致受益。

## 质量、全状态相容与必要撤回

每臂48个raw-changed、80个raw-unchanged；按原非空内容谓词分别为44/76。三臂各16 character edits/182 reference chars，CER=8.79%，仅去空白的controlled-adaptation CER，不是原论文CER复现。144个正式raw变化均属于非空白表面变化，0个仅空白变化；仍不能据此称为语义纠错收益。

|arm|非空compatible+ahead|非空incompatible+ahead需丢弃|unchanged实际retained-ahead|实际可见音频回撤|native completions|
|---|---:|---:|---:|---:|---:|
|sequential|0|0|0|0|138|
|drop|15|2|0|2|345|
|joint|87|13|70|13|304|

Owner的incompatible+ahead必须丢弃事件与实际可见回撤分列；不能把全部回撤当作机制错误。Joint的87个compatible+ahead中有17个raw-changed，说明raw字符串变化不等同于完整状态不相容；13个incompatible+ahead均在raw-changed类中。Drop/joint的private completions为207/166，后者少41次。

## 下一步判断：有界stage profiling值得做，handoff收益尚未成立

全部14格中，实际模型同完整start/end输入配对384，其中完整最终endcut相同311、不同73。派发前controller-ready配对285，涉及276个唯一Authority jobs；其中244个配对有非空private文本。按配对加权的完整infer均值Authority0.7698s、Private0.4697s，差值不是精确C。

这支持测量真实A/C、完整beam和postASR状态的短profiling。候选packet是否可给原C消费应检查完整输入cut+音频/目标/原ASR配置，不应按预测最终endcut相同筛掉73个不同类。后续预测链仍要求前一步fullstate相容。固定双源pipeline的容量可能低于强双完整副本；应同时审视单源反馈关键路径，并加入两完整副本同样ASR早显的强对照。当前没有实现或测量handoff。

## 能耗与证据位置

14个实际双卡能耗JSON已取回并逐文件SHA记录。正式各4格service-window board能耗：sequential 25949.177J、drop 49783.878J、joint 47990.589J。Joint相对drop减少3.60%，但高于强sequential 84.94%。端点按原origin至Consumer drain，排除模型加载/预热；不得称为含冷启动的总进程能耗。

主scope gate SHA: ecbeeaffd7d1abb894570d26bb41646aec836d5eac5d454f01da9630c31fedfa。postanalysis SUMMARY SHA: 772179553156df83f1b2ffb40409c50717fc97129d8e853d04f3c5f9203c805f。原始日志/输入/模型留在指定B盘；本地IMMEDIATE_COLLECTION_MANIFEST逐项记录9个取回文件SHA。

实际神经source61c9afac00561f7ff1351f3eba9fd95adb239e8c、离线auditor-controllera0652a81a205483ba2091dfd345b85be72ee8b19分开。原v6初始化失败、v7无效域控制失败、v8原controller离线空显示断言失败均保留，未重标神经执行。
