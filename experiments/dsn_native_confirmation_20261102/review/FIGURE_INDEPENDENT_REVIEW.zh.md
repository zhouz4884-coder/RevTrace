# 最终 native_content 图只读复核

**PASS，可复制入稿。** 审核对象为冻结Root renderer `2c78b70fb7a244fa3ef3b6f9267b722e54c82de7` 及 `figures/FIGURES_v11_v2` 导出；没有运行绘图/reader/模型，没有改源、CURRENT或TeX。

实际PDF为3.48×2.75in，直接提取的最小字号8.0pt；DejaVu Sans普通/粗体均已嵌入，Type0、无Type3。PDF全部文字框位于页面内，PNG目视100刻度完整、legend无框，未见文字重叠；6.5%紫色小分区和6.1%/3.3%灰色尾部均有清楚标注。

四行数值与INPUTS_v11完全一致，输入SHA为 `326017933c785b7a77e340fd499d519aab8ad2e0ee7086fa8246bed0035a873b`。每行partition闭合：Independent各自137.864125s，Resident各自66.33975s，没有跨bank合并分母。unknown四行均0，省略其legend正确；Pass留在表中。蓝深填、紫斜纹与浅灰/边界具备灰度区分通道。

具体PDF字体、页面边界、文件SHA与数值核对见同目录 `FIGURE_INDEPENDENT_REVIEW.json`。Matching标签应继续由正文/图注解释为后来同前沿selected whole-text的一致性，不写成人工正确率或在线SUP授权。
