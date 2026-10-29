# 实际交错：可信前沿推进，仍合法的可见进展反而被撤回

已有36格中的机制例图，无新GPU调用，不估计发生率。固定c16-staggered、repeat0，只比较R1S0与R1S1。先要求两臂在同一来源、同一个Canonical F都实际观察到完整兼容ahead，再按固定块内R1S0来源回撤面积最大选择，平局按source ID。结果为sid7 / 3570-5694-0003，F=288000 samples=18s。全局面积最大sid13没有Joint ahead交错，不适合用于同边界清除/保留解释；它和其余来源仍保留在完整矩阵中。全部候选及规则已在提取前冻结到CONFIG_v1.json。

从实际consumer/events与该sid完整Authority/Private输出重算：

- 两臂完整Canonical F/Z/P/text历史完全相同。
- 两臂已经显示的整个Private Z/P/text也完全相同，前沿为19.025s。
- Private实际消费的prompt逐token等于随后F=18s选中的P；独立得到exact_selected_root，不依赖retention flag。
- R1S0在原session相对时间21.421743s应用可信F=18s更新，把19.025s撤到18s；1.025秒音频被撤回1.017951秒墙钟，至22.439694s恢复。
- Joint在自己原session相对时间21.399446s应用同F更新时保留19.025s完整view；18s之外仍为provisional。

两幅x轴均为observed_perf减去(episode.origin_perf+session.offset)，未对齐Canonical事件，没有把一次运行的时间移到另一次运行，也没有用离线回放创造服务收益。

[论文PDF](FIGURES_v3/actual_compatible_progress.pdf)、[可编辑SVG](FIGURES_v3/actual_compatible_progress.svg)、[完整PDF页预览](FIGURES_v3/actual_compatible_progress_PDF_PAGE.png)、[绘图及输入SHA记录](FIGURES_v3/PLOT_RECORD.json)。19个有界实际数据文件共1,511,478字节，全部逐文件核对远端SHA256。

该例说明首个deadline信用不足以完整评价服务：首次及时消费之后，可信推进仍可能清掉完整且合法的可见进展。它不代表所有相位有同样事件，也不将provisional变成certified suffix。

提取源c9e8a89a7df2f269fad0007a4891922da02d728d；冻结配置SHA bb0b4157b892155dfee352f92969009ceee59817e0ac76d40fbd738dfdfed18a。最终绘图源e1213e8ba5bc13ef9db58402c8030f87579d6ce2，完整byte manifest为TRACE_SOURCE_v3.json。首次绘图QA拒绝了实际窗口之外的自动tick；修复仅限定tick位置。新Windows clone曾发生autocrlf转换，预启动source gate同样拒绝；只将独立CPU checkout恢复为HEAD原始blob字节，另冻完整manifest。没有改legacy或神经源，旧失败记录保留，未重跑或重标神经结果。

最终图宽7.15in、字号8–9pt、嵌入字体、Type3=0，完整PDF页目视检查通过。
