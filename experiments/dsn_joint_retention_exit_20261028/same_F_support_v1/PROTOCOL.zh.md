# 全 24 格 first-credit 的同 F 完整 Canonical 支持重计

本方案是 CPU-only、后验 trace 重计，没有新推理，不改旧 C3 服务结果或任何原始 D2/C8/first-credit。

主重计直接复用干净冻结源 `fde6272b494db43a66eebea7444d7c9d1037e687` 的 `run_analysis.py --components usefulness` 与 `canonical_usefulness_v1.py`；其实际代码 commit、完整 manifest 与脚本字节保持不变。新的 orchestration/补充脚本另有干净源和实际 commit，二者身份分开。

1. 全部原 24 格和全部 offered 前沿保留。每个原 dual-credited 音频区间按其首次实际 Consumer 完整 view 分类：已认证；ahead 且完整同 F Canon raw/norm 一致；ahead 且不同；同 F 不可得/未观察时 unknown。unknown 不能默认为不同，也不能退出分母。
2. 比较边界是首次实际 view 的完整可见 F。若它超过 offered frontier，也只能比较该可见 F 的完整 Canon。禁止把更长文本截到早 F，禁止只比较公共前缀。完整 Canon 必须来自实际 commit→选中 Authority 完整结果→同 F publication。
3. 首次交付信用完全沿用原 all-offered 的 D2/C8 审计；后验 raw/norm 支持是额外分区，不替换原指标。已选中但 Consumer 尚未观察与真正 future selected 分开。
4. 次目标固定为已冻结 c25b0655 诊断中的六个 sync 后继批、全部 96 行，包含原 miss→hit 的 R1 6/6/1 和 R0 4/2/6。逐行链接原 K1 job、Owner 完整 publication、首次实际 Consumer view、同 F Canon 与真实 worker fault flag；不按支持结果筛行。
5. 对原 v2 主重计已读取的 core raw/metadata 逐项复核 byte SHA，确保没有以新数据替换旧矩阵。任何缺失/对象矛盾/原期限或 first credit 改变都会 FAIL_PRESERVED；科学上的不同/unknown 是完整保留的结果。
6. 当前只做本地冻结与 synthetic CPU controls。native v8 正式 scope 与其 postanalysis 未完整结束时，不 stage、不执行远端重 IO。根分配一次短 CPU/IO 窗口后才运行；结束并有界取回后，在 12 格中点 GPU 前释放窗口。

后验与选中 Canon 一致不等于 groundtruth、语义正确、在线认证或部署时可用的 verifier；F2 实际错输入也不代表自然发生率。不得把最终 WER 相同代替首次内容支持检查。
