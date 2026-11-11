# 新独立来源：有界可用性核查与首选语料

2026-11-11。仅做旧catalog/排除表及官方新语料metadata的核查。没有读取/下载WAV音频、实际TRANS转录或模型权重/输出，没有启动GPU，没有改变CURRENT。新下载仅为官方metadata归档，原件保存在指定8TB；audio test归档仅发HEAD请求、未取body。

**结论：旧AISHELL载体不足以支持新增16位speaker与12–20秒层；首选下一步核验MAGICDATA官方test，已有43个真实test speaker IDs作为可能池。它尚未达到音频就绪或“16位符合6–20秒”的门。**

## 1. 旧AISHELL：只验证指定catalog与既有排除表的边界

本次独立读取远端 `projects/revtrace_dsn_native_confirmation_20261102/ARCHIVE_ENTRIES_0.json`，SHA256为 `efd03c4e9ef086548d353ead2efacb826afcc6440e1c5b866faf79d8e176ccc4`。只取 `StreamCorrect/aishell1_testset/*.wav` 的catalog元数据；共有20个speaker。

排除输入为20261102已冻结的43人联合旧历史表，以及那次实际选择的新8人（S0769/S0901/S0902/S0906/S0907/S0912/S0914/S0915）。两份输入SHA保存在 `METADATA_OPTIONS_BOUND_AUDIT_v1.json`。其余两人为：

| speaker | catalog估计[6,12)条数 | catalog估计[12,20]条数 | catalog内最长估计秒数 |
|---|---:|---:|---:|
| S0766 | 30 | 0 | 7.3789375 |
| S0904 | 15 | 0 | 6.8249375 |

时长使用原catalog `(WAV_bytes−44)/32000`，仍是PCM16/mono16k且44-byte头的**估计**，本次没有读WAV header。不是45位独立speaker，不是新音频已就绪，也不是当前全项目unused census。20261102之后的新工作、别名和跨项目历史尚需新完整census；这两人只可称“在所给历史输入下的剩余候选”。

## 2. 一个不同的官方ASR来源：MAGICDATA read Mandarin test

选择对象是 **OpenSLR68 MAGICDATA Mandarin Chinese Read Speech Corpus的官方test split**。它是普通话手机朗读语音，保持现有原ASR→Correct→Update任务，不切换为翻译、TTS、对话分离或多通道任务。官方提供独立train/dev/test下载；test约2.2GB，metadata约3.8MB；页面标注CC BY-NC-ND 4.0及非商业研究用途。[官方OpenSLR68页面](https://www.openslr.org/68/)

本次下载的[官方metadata归档](https://openslr.magicdatatech.com/resources/68/metadata.tar.gz)为3,886,385 bytes，SHA256 `1f71e2dfea4706e76177158a6d45f2be838042af5ecc442f447f8369d40764c9`。内含Usage_Instruction、技术docx、SPKINFO和train/dev/test.scp，没有音频或TRANS成员。本次只解析技术说明、SPKINFO及test.scp的filename/path字段。

**官方test metadata实数，而非按总人数推算：**

* `test.scp`为1,723,809 bytes，SHA256 `c1dc8d289fb8a245359428d0ad30624cc3eff620c3ada4b7b1359f532e6be600`。
* 24,279个唯一原始WAV条目，43个speaker IDs，全部在SPKINFO找到；SPKINFO共有1,080个唯一speaker IDs。test namespace例子：`wav/test/38_5715/38_5715_20170914193306.wav`；完整43人表在 `MAGICDATA_TEST_METADATA_VERIFIED_v2.json`。
* 每条scp有basename与relative path两个别名，不能算成两条语句。首次schema探针的speaker数量43正确，但逐speaker计数误计双别名；v2已按唯一basename复核，保留v1并明确supersede，不使用其重复计数。
* 官方技术说明称test为28.08小时；旧Usage/docx写总speaker数1000，SPKINFO实际1080与当前OpenSLR页面1080一致。保留差异，选择时以实际身份表和test成员映射为准，不能将1000/1080推为test人数。

这些数据来自官方发布的metadata，不是读取TRANS反推ID。实际转录另在corpus的TRANS.txt；Kaldi官方语料准备脚本也将wav、speaker与text分开处理，后续不能运行其TRANS过滤/文本规范化步骤来选择样本。[Kaldi MAGICDATA数据准备脚本](https://github.com/kaldi-asr/kaldi/blob/master/egs/multi_cn/s5/local/magicdata_data_prep.sh)

## 3. ≥16人与6–20秒分别处于什么证据层

43个test身份说明**至少16个metadata speaker有可能被选择**，不说明16个都具有自然6–20秒片段。官方test.scp只有WAV名字和相对路径，**没有duration、file bytes或sample-rate字段**。本次未读音频头，因此未确认任何具体条目的6–12/12–20秒、mono16k或PCM16属性；更不能先保证长层16人。

下一步技术门必须先形成原test全成员的非内容header/长度索引，保持原WAV不裁剪、不拼接、不改边界、不为凑长层重采样。对全43人分别输出两个时长层的合格条数、sample rate/channel/format异常和实际可用N；只依此及新全历史census冻结speaker/utterance，再允许读取相应转录或运行模型。若原音频格式不符合现有输入合同，则不静默转码。

实验历史unused必须对MAGICDATA corpus namespace/原路径/ID/别名做新census。不能用AISHELL的43人排除表宣称MAGICDATA从未实验过；不能把不同语料ID证明为跨库同一自然人的绝对不重合，更不主张预训练未见。

## 4. 访问与成本可行性

官方CN镜像对test归档HEAD实测返回200，Content-Length为 **2,201,936,013 bytes**、application/x-gzip、Accept-Ranges=bytes，未下载audio body。元数据原件保存在 `/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_strengthening_v16_20261111/metadata_options_v1/`。

没有验证到官方逐WAV下载URL、逐文件长度/时长表或gzip随机访问索引。现有scp不提供offset；不能像旧ZIP central directory那样假设HTTP Range可直接只取16条WAV。**可预见的最坏正常获取量是仅test约2.20GB，而非train的52GB；是否具备更小官方访问路线仍待核实。** 此量在8TB容量上有界；本次不以此自动启动大包获取。后续若下载官方test，先完整归档/校验，先读header作技术metadata，不能先看识别效果挑样本。

官方页面标注的许可与归档Usage的旧条款有额外差异（后者还限制修改/格式转换等）；应保留原WAV、注明来源、不再分发派生音频。本报告没有给出法律解释或擅自扩展授权，也没有发送邮件或申请外部访问。[官方许可与发布说明](https://www.openslr.org/68/)

## 5. 选择与后备分支

**首选：MAGICDATA官方test，进入“metadata/header可用性核验”阶段。** 理由是来源不同、官方test身份明确、43人实数超过16目标，且仅test包的获取成本可界定；原任务与普通话来源相符。现在不冻结16人GPU表，不把speaker可能池当时长合格池。

**后备：接受同一官方test内实际合格N，而非强凑16。** 少于16则按新冻结方案使用真实N并完整报告；长层不足就保留该层缺口，不能混入train/dev、裁拼或从模型结果挑长句。如果MAGICDATA技术/访问条件无法达到合同，可将现有AISHELL两位作为单独的短层补充候选（仍需新census与header），但它不能冒充新的16人/跨来源长层验证；另一个新来源须再独立选择和冻结。

本报告没有推荐扩大原算法主张。新语料完成技术就绪后，仍须同一冻结执行器、相同Conservative/Ready-only/dependency-versioned/RevTrace/UIR协议、原500ms步长、完整EOS与所有失败计入，才可谈新增独立来源的性能结论。

## 6. 证据位置

* `METADATA_OPTIONS_BOUND_AUDIT_v1.json`：旧catalog SHA、20人、43+8输入、逐speaker时长估计与metadata-only下载索引。
* `MAGICDATA_METADATA_DOCUMENTS_v1.json`：官方技术文档、SPKINFO头及逐成员SHA；包含旧说明人数差异。
* `MAGICDATA_TEST_METADATA_VERIFIED_v2.json`：43个test ID、唯一条目计数、SPKINFO映射，明确duration仍pending。
* `MAGICDATA_TEST_HEAD_ONLY_v1.json`：官方test HEAD响应，没有audio body。
* `METADATA_SOURCE_CHOICE_v1.json`：本报告的机器可读选择、限制、后备及artifact hashes。

两个元数据读取脚本的开发问题（编码别名、Windows终端GBK输出）没有导致音频/文本接触或更改原数据；已保留已生成的技术JSON，修正终端输出。文件成员名和speaker统计的探针/最终版本均保留，不将开发错误误称语料数据缺陷。
