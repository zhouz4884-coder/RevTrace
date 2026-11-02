# 已有final4f期限敏感性：独立数字/视觉/范围审查

2026-11-02。只读本地RESULTS_v1、FIGURES_v1、FIGURE_EXPORT_v1与旧已归档端点；使用PDF技能复用三张已生成PNG做视觉检查。没有重跑分析、模型、远端、CURRENT或修改冻结源。

## 判断与v11最短英文

这组结果有价值：它直接回应单一D2截点是否驱动结论，并展示同一speaker的配对方向。它仍重用旧四个speaker，不构成新的独立泛化确认。**建议v11主文加两句并指向artifact，暂不另加一张全宽图**，将主图空间优先留给新八speaker的独立确认与原机制链。

> With C8 fixed, the prespecified 0.5–6-s display-budget sweep shows a broad coverage shift toward earlier delivery. At the original D2, all four speakers improve in both banks (matched: 48.4–60.8 pp; resident: 34.9–59.0 pp), while the original 6/8 trial and 7/8 request pass counts remain unchanged.

两句支持的是这个固定原生调用对照的timely coverage稳健性，不是新的R×S消融、每个来源在所有预算下支配、在线文本正确性或原方法已跨全部工作负载兑现期限。

## 数字核对

正式analysis92c29c5b1df764496393a66737bf789a84833efa，manifestaa78c7da…，原神经源4f，原端点/a13源未重新归属。SUMMARY/GATE均为 `PASS_FROZEN_D2_POSITIVE_CONTROL_AND_SOURCE_PAIRED_SENSITIVITY`。32原请求含544个原offered端点；matched16trial与resident4trial/16request分开。

每bank每策略分母66.33975s；C8不合格/缺D的质量均为0，因此本组曲线的有限极限为100%。这来自完整端点，不是筛掉失败质量后归一化。

| bank | D2信用Conservative→RevTrace / audio-s | 原始通过数 | D2加权覆盖率 |
|---|---:|---:|---:|
| Matched |30.0→65.821625|0/8→6/8trial|45.22%→99.22%|
| Resident |31.0→64.118875|0/8→7/8request|46.73%→96.65%|

高audio coverage与whole-request P99通过数是不同对象；没有用放宽预算将原失败改绿。

| 原speaker | Matched配对增益 / pp | Resident配对增益 / pp |
|---|---:|---:|
|S0905|60.829|59.039|
|S0908|48.432|34.865|
|S0913|49.698|52.657|
|S0916|57.133|53.062|

每值先在同一source内合两次时序重复；8行来自相同四人跨两个bank，不是8个独立speaker。source-paired图的开放点/线段是两次重复范围，不是CI。

曲线不只是D2处有间距。例如τd=1s时matched覆盖率18.09%→53.44%、resident18.84%→49.59%；τd=3s时分别62.56%→100%、67.08%→100%。宽松到6s两策略收敛100%。这解释时序收益与预算的关系，不将6s替换为投稿主期限。

## 三图审查

九个PDF/SVG/PNG的长度与SHA逐项符合FIGURE_EXPORT_v1记录，全部true。此检查绑定导出身份；不冒充新的原raw重算或v11最终栏宽验收。

- `deadline_sensitivity`：0–100%完整纵轴，0.5–6s预声明横轴，原D2竖线清晰；两策略实/虚线在灰度中仍可辨，精确step曲线没有虚构平滑。两bank形状相近，完整单独一图的信息密度对11页正文偏低。
- `full_latency_CDF`：0起点与全有限范围保留；它与主敏感性图大部分重复，适合artifact完整性，不需正文同时出现。
- `source_paired_D2`：蓝方块对应source内两repeat合并结果，开放圆/线是repeat范围；所有source正方向直观。两个长xlabel在中缝较紧，若将来进入正文，建议共同简短xlabel `Gain at D2 (pp)`，并在caption明确方块/圆点与非CI。当前未改图。

曲线阴影必须在caption称为**四source的描述性min–max范围**，不能当置信带或统计显著性；纵轴为audio-duration weighted deadline coverage，不能写request availability或new correct text。

## 是否加正文图

推荐：主文两句，现有三张图全部留artifact。新八speaker结果将提供比旧四人重复bank更重要的竞争力增量；不要为“图够多”挤掉任务保持/保留对象/故障见证。

若编排后尚有空间且审稿风险明确集中于deadline选择，可只用deadline_sensitivity，单独不再加fullCDF与source-paired第二张图。其caption至少说明C8固定、每bank66.340s、同四speaker/两repeat、阴影非CI、原6/8和7/8不变；图须按原7.125in完整宽度放置或另冻实际栏宽渲染，避免8.5pt标签被缩至半宽。
