# 研究归档边界（不是匿名投稿包）

用户已指定公开GitHub仓库，本轮只追加独立`experiments/phase_d_20261021/`有界研究包。不得覆盖旧源码、论文或用户工作树；不得把公开仓库称匿名镜像。本轮不更新/核验anonymous.4open，也不投稿。

包内包含：最终实际测量runtime/测试、实际实验source archives与Git对象bundle、方法/设计冻结/GO-NO-GO、CSV/JSON指标、逐文件原始证据hash索引和有界压缩证据。原始trace/power/完整WAL、所有音频、权重、环境/cache留在8TB盘。服务端文件复制不可被称新GPU试验。

`verify_portable.py`只校验文件并运行独立CPUfixture；不会连接实验室SSH、自动占GPU或声称神经效果复现。真实GPU重跑需要合法获取模型/音频、完全匹配的环境/源码和空闲资源。源码Git身份与GitHub发布commit分别记录，不能混成一个。

早期preliminary数据、旧错误LA对照和未运行源码版本均保留明示标签，不混入最终矩阵中位数。最终manifest生成后不修改包内文件；远端所有新增blob及Markdown/有界archive回读校验通过后才宣布同步完成。
