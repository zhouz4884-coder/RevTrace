# Native原14格内容端点：已完成

[结果与正文措辞](RESULTS_FINDINGS.zh.md) · [冻结定义](PLAN_DEFINITION.zh.md) · [原14逐格结果](RESULTS_v1/RUNS.json) · [实际文字事件](RESULTS_v1/ACTUAL_TEXT_EVENTS.json) · [LCP版本身份及寿命](RESULTS_v1/LCP_OCCURRENCE_SPANS.json)

独立CPU源bd18bc8abfbe6d0b1ba7f2349e9cf2939956e64e，完整5文件manifest与bundle已冻结、导入root并在远端实核。8项最小语义控制通过；`CPU_CONTROLS_v2`记录实际config/environment文件byte哈希，v1原记录和其逻辑hash说明保留。全部原14信用逐格不变，10个结果1.77MB全部SHA一致，未调用模型、未改原SLO或神经source。

Formal Joint的17.0s全部首次cover关联strict append，没有unchanged-trigger信用；它仍是音频前沿端点，不是新增文字量。Sequential原18.5s中17.0s关联append、1.5s关联unchanged，Drop12.5s全关联append。不能据这个分区删去基线信用或另造胜负。

Raw/只去Unicode空白LCP引入/擦除/最终codepoint occurrences分别为Sequential184/0/184、Drop206/22/184、Joint241/57/184。所有字符出现/关闭时刻来自实际Consumer；没有猜测token/audio对齐、groundtruth或语义正确性。

原始42个小输入仅454KB，配置固定于`CONFIG_v1.json`并保留原文件SHA。远端入口是`projects/revtrace_dsn_native_content_20261029/CONFIG_v1.json`；输出中`CONFIG.json`为同一对象的LF/UTF-8序列化副本，冻结文件本身保持原字节，`RUN_RECORD`的frozen_config_sha256指向前者。原运行commit61c9与offline auditor a065分开保留。
