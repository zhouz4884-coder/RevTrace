# 验证入口与依赖

最终源载体：`continuity_v6`，commit `2a4b56bc5d8dcbf3884f03f8213f9c39101f59f8`。
所有source/manifest与raw文件的具体SHA以交付索引为准，发布commit不替代实验源码commit。

## 不用GPU的核心回归

在展开的完整运行时，Python+NumPy+pytest：

```text
python -B -m pytest tests/test_consumer_bound_identity.py tests/test_continuity_proof.py tests/test_localagreement_display.py tests/test_certified_display.py tests/test_properties_abc.py tests/test_live_qwen.py tests/test_standard_async.py -q -p no:cacheprovider
```

该集合实测73项通过，不冒称独立声学样本。完整本地当前fixture整合395项及外部对抗6项是另一层，部分历史大fixture不随独立包复制。Tokenizer/processor/实际WAL语义复算需提供相同模型工件与Qwen库；不通过CPU脚本假装跑了GPU。

## 正确启动一个真实GPU方法单元（仅资源空闲时）

需要两张足够显存的独立GPU、冻结软件/完整音频manifest、明确实验ID和全新WAL路径，不能复用其他contract的日志。示意命令中的路径必须由操作者提供：

```text
python scripts/run_tc_live_qwen.py --model MODEL --manifest DATA_MANIFEST --output UNIQUE_OUTPUT --code-commit 2a4b56bc5d8dcbf3884f03f8213f9c39101f59f8 --study-id OWN_EXPERIMENT_ID --mode coarse --sessions 16 --proposal-barrier decoupled --proposal-reconciliation lazy --display-protocol canonical-snapshot-v1 --publish-canonical-display --trusted-text-binding --consumer-policy two_lane --retain-verified-private-prefix --phase-n-instrumentation --capture-model-inputs --durable-journal-path UNIQUE_WAL --journal-sync-mode group_ready
```

这不是让下载者自动连接实验室服务器或自动占卡。模型、音频、环境、cache和大日志不在有界GitHub包；须合法另行获得。`retain_verified_private_prefix`保留的是条件兼容的私有token投影链，不是KV-reuse fallback，不给proposer写canonical权限。D1+D2仅在声明的text-state adapter/固定χ/可靠本地FIFO范围通过测试。

恢复试验的SIGKILL仅能由专门driver在验证UID、准确命令、独立进程组和标记后发送。绝不按模糊进程名结束其他任务。网络、浏览器、掉电、存储丢失、zombie worker、长期有界内存不属于本协议的已验证范围。
