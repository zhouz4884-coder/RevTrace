# 本轮事前研究选择与统计合同

日期2026-11-02；基线论文v10，实际神经/协议实现NN4f保持不变。来源规模先由可审计metadata census确定，模型输出不参与选样。

## A. 已有端点敏感性

固定认证期限8s，显示期限0.5–6s、间隔0.25s，共23点；另输出全部实际有限D的event-exact曲线。每个实际offered区间按原音频时长计权，missing/C8失败/EOS仍留分母。原D2/C8信用、P99与6/8、7/8计数严格守恒，不生成放宽期限后的新pass数。

Matched与resident分别分析同四位说话人；两timing repeats在speaker内部合并，每speaker报告paired变化。四source min/max是描述范围，不是CI；不将544个frontier或两个bank当544/8个独立来源。曲线交叉/负增益是结果，不是技术失败或调网格依据。

## B. 新来源确认

选择优先级：同AISHELL-1 test split、同完整8–9s短会话范围、16kHz mono、未用于本研究模型调用/策略选择/调参/故障定位的speaker。需要同时核speaker、原WAV/PCM SHA、实际历史使用与别名；仅catalog候选/冻结未跑须与实际模型使用区分。若同split严格eligible人数不足12，采用可证明的实际N，不为凑数混speaker/split。若多于12，按事前metadata确定的顺序截取12。N与每speaker具体clip在首次新reference模型调用前冻结。

完整Conservative与RevTrace各两次fresh process，4N格。方法、模型、精度、500ms/noVAD、两完整worker、固定暖机、allocator、原D2/C8、每条原EOS与所有offered保持一致。source按固定seed20261102排序；每speaker r0策略顺序预存，r1直接反转该speaker r0顺序，按实际plan断言AB/BA；同repeat两策略GPU角色相同，第二repeat交换GPU。禁止block parity推断已实现counterbalance。

原程序连续reference与每个完整start的原full_step重执行先单独登记、冻结执行、收费。Reference结果不用于换clip或改预测。参考/C/U/state不一致先保留失败并按same-input/repeat/original关系诊断，不删source，不把reference模型费用记为服务收益。

正式集不参与继续调参。技术/身份/语义/资源失败保留并停止队列查因；性能miss不裁剪后续矩阵。每cell原配置/环境/实际source/原盘结果/aggregate/GATE先登记；Driver、原NN4f、生产support、checker及GitHub归档身份分开。原事实/Consumer/真实物理drain与双板共同窗口核验，原c4实际轨迹检查后单独闭合。

主结果：每speaker两repeat合并的A2,8配对变化；全offered时长加权覆盖率、逐speaker等权描述、原whole-run P99 pass。独立单位为speaker；不把repeat/transition当独立任务。所有source含负效应全部报告。实际内容/原任务保持、确认后的使用、未用但已付模型host工作和实际双板能量分别计量，不将并行host区间相加为service wall。

## C. 正文选择

冻结RevTrace现有主线，不新增selector、模型、调度器、日志系统或普遍必要/最优性理论。先完成主张/近邻/表注的有用修改，再按真实数据选择敏感性或独立确认的呈现方式。材料保留所有结果，正文只放影响核心论证的证据；若新数据实质改变旧headline的适用性，必须相应调整主张，不能靠不展示来维持错误泛化。
