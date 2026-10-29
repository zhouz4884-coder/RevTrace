# 公开推理精度核查更正

原 profiling 与 native14 的 ASR、C 都实际采用 FP32；这项事实不变。此前从论文的 FP16/BF16 模型权重内存段推断“遗漏了作者推荐的优化推理精度”，证据不足，应更正。

固定作者仓库 `bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3` 的 [VAC 推理加载器](https://github.com/vu-duy-tung/StreamCorrect/blob/bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3/whisper_streaming/vac_online_processor.py#L104-L136) 对 Qwen2Audio 和 Ultravox 两条 C 路径均明确传 `torch_dtype=torch.float32`。README 介绍的单文件推理 [脚本](https://github.com/vu-duy-tung/StreamCorrect/blob/bbb9f7fde13fabb6c0940f5bae215150d1ea1cb3/runs/run_single_eval_aishell.sh#L61-L74) 带 `--vac`，即进入这一加载路径。原 C 的默认 FP32 与我们检查到的作者公开推理实现一致。

论文第7页的 FP16/BF16 语句讨论单副本模型权重内存及 H20 容量，不足以独立认定所有实验采用特定 dtype，也不构成唯一的推荐推理 dtype。训练配置中还同时存在 bf16/fp16 相关可选项与硬件注意事项，训练设置不能自动替代推理合同。

因此，不将“补精度网格或优化精度强对照”作为进入下一项候选交接实现的强制门。默认保留公开 FP32 推理合同；新源码允许显式配置 C dtype，并将其绑定进完整执行合同，但本轮不启动额外 dtype 实验。仍不能把当前3090受控服务结果直接称为重现或优于论文 H20 部署。真正需要加强的对照是两完整副本、同样 ASR 早显、以及每个实际 C 模型都完成固定的真实神经 warmup。

本地 `author_reference/MANIFEST.json` 保存上述公开文件的下载 URL、commit 和 SHA256，其中 VAC 源文件 SHA256 为 `0cb595097ff69d98cf49e1c9b016db827f547fa436aa5ff217c3e6c845871fa0`。旧冻结 plan 不重写，旧实验来源和实际 dtype 不重标。
