# RevTrace 方法图：可信安装、合法临时进展、物理释放

最终图：[PDF](FIGURES_v2/coordination_protocol.pdf)、[可编辑SVG](FIGURES_v2/coordination_protocol.svg)、[350dpi PNG](FIGURES_v2/coordination_protocol.png)、[完整PDF页预览](FIGURES_v2/coordination_protocol_PDF_PAGE.png)。固定宽7.15in、高4.45in；全部字体≥8pt，PDF嵌入字体、Type3=0；SVG保留text节点。已实际打开完整PDF页与导出PNG检查，没有裁切/拥挤。可直接采用的英文说明见[caption](caption.txt)。

图的中心结论是：**认证事实安装、合法临时进展保留和真实执行器释放并非同一个时刻。**

- 上半图以实际f0的Authority选择→受保护WAL/Canonical写入为蓝色路径；新的(F,P)供R检查。Private只保留完整结果和实际冻结输入，R依据同F/P及完整真实依赖决定可继续计算，不给Private认证权。
- 完整Private视图直接进入实际Consumer。S保留兼容的整个ahead hypothesis，并独立推进certified lane；不拼接后缀。完整视图通道刻意绕过R卡片，避免错误暗示S只有R开启时才能工作。不能保持兼容ahead时显示Canonical。
- 下半图使用真正已安装Canonical覆盖目标的K条件，区分CancelRequest、decode safe point、互斥RowComplete/RowCancelled、全行终态+device sync的BatchDrained，以及lease release。虚线标出自然完成和取消的竞争，RowComplete可以先交付而物理批次继续占用。

本图不包含未实现的原生候选交接、不表示任意GPU故障下有取消时限，也不借f0为native适配背书全部故障保证。F/Z/P的定义与状态合同应由正文给出，不把实验名、旧版本或安全检查清单塞入图内。

真实执行源 `f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf`，逐关系源码位置与字节hash见[source map](source_v2/SOURCE_MAP.json)；输入完整hash见[配置](CONFIG_v2.json)。最终绘图源独立干净提交 `a4fb90ccdcf4653a3a4a20a0fb2639a45c25a06f`，完整manifest/bundle为`SOURCE_v2.json/.bundle`，已导入主仓库ref `codex/coordination-figure-v2`。原v1绘图源与输出保留；v2仅明确S不兼容时的Canonical回退、完成竞争虚线，并移除本机不存在的Helvetica回退。没有改任何实际协议或运行结果。

图意/导出合同在[FIGURE_INTENT](source_v2/FIGURE_INTENT.md)，程序与完整页面QA在[QA](FIGURES_v2/QA.json)，实际全图目视检查及输出hash在[VISUAL_QA_FINAL](FIGURES_v2/VISUAL_QA_FINAL.json)。`PLOT_RECORD.json`记录源、配置、环境与所有输入；本图是方法示意，不是新的测量结果或GPU实验。
