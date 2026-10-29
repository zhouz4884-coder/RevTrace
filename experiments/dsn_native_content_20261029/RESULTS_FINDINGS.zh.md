# Native old14内容端点：原信用不变，文字活动另列

全部14格（2 witness+12 formal）一次只读重算完成。原14格D2/C8及first-credit逐格完全一致；读取42个已冻结SHA的小文件共454,248字节，不读模型、音频或native_jobs，不调用模型。10个结果文件1,774,215字节均逐项对照远端SHA。新分析源bd18bc8abfbe6d0b1ba7f2349e9cf2939956e64e，原神经源仍61c9afac00561f7ff1351f3eba9fd95adb239e8c；原offline auditor另为a0652a81a205483ba2091dfd345b85be72ee8b19，均未重标。

## 最重要的澄清

v8 Consumer只在累计text全空时令visible_F=0。累计text已非空、当前轮没有新文字时，F仍可能推进。因此原17.0s是原定义下的音频前沿信用，不是17.0s新增转录文字。

但本次事实也不能被反向夸大：**formal Joint的17.0s中，first-cover实际row全部为strict text append，unchanged-trigger信用为0。** 这项补强没有发现Joint的17.0s由“旧文字不变而F推进”的首次cover所解释。一个append row仍可能首次cover多个音频区间；没有token/audio对齐，所以它也不能给新增文字分配音频秒数。

| formal每臂4格 | 原音频信用s | 首cover关联append的信用s | 首cover关联unchanged的信用s | LCP引入codepoint occurrences | LCP擦除 | 最后可见codepoints |
|---|---:|---:|---:|---:|---:|---:|
| Sequential两完整副本 | 18.5 | 17.0 | 1.5 | 184 | 0 | 184 |
| Drop | 12.5 | 12.5 | 0 | 206 | 22 | 184 |
| Joint | 17.0 | 17.0 | 0 | 241 | 57 | 184 |

三臂原offered分母均66.42975s，主指标排名仍Sequential18.5>Joint17.0>Drop12.5。不能删除Sequential的1.5s再宣布新的性能胜负。按首次cover事件分类的音频秒数只是原指标的描述性分区，不是一个新增转录量指标。

## 所有实际文字活动与生命周期

完整formal轨迹中，F正推进但text不变的row数为Sequential8、Drop18、Joint20；certified/processed F正推进但text不变为10、99、104。说明原累计非空gate和“当前轮产新字”确实不同，即使这些行没有成为Joint及时信用的首次cover触发。

Raw与仅删除Unicode空白的统计在本组相同；没有利用case、标点或NFKC归一掩盖差异。LCP版本身份会将内部替换后的整个suffix重赋身份，这是操作定义，不是最少编辑、token对齐或语义相同字的重新识别。

Drop的22个被撤回codepoint occurrence都在Canonical应用时关闭，其实际已观测寿命中位数0.559215s、范围0.226553–1.200672s。Joint的57个同样都在Canonical应用时关闭，中位数1.073509s、范围0.039256–5.518496s。最终仍可见的身份右删失于同source最后实际Consumer观测，不补到假想UI关闭时刻。全部身份的出现、关闭、literal文本及实际时间保存在`LCP_OCCURRENCE_SPANS.json`。

Joint引入241、擦除57、最终184；Drop为206−22=184。较多的早期显示伴随较多实际文本修订，不能将引入次数当成更多最终文字，也不能把57称为57个错字。这些观测不替代原CER或完整状态合法性检查。寿命/字符秒更不是越高越好的吞吐端点：更慢运行本身就可能延长曝光。

两witness单独保留，不混入formal表：Joint两格原信用9.0s，均在append row首次cover；引入121、擦除29、最终92。

## 对正文与后续prototype的用法

正文可以写“原音频前沿信用17.0s，全部在发生strict append的实际row首次cover”；不能写“17s新增文字”或“识别了额外4.5s正确文本”。Joint与Drop原信用差4.5s仍成立，但强Sequential的原信用更高，三个arm最终文本与原CER比较维持原结论。

新prototype可以逐字节复用`source_v1/analyze_content.py`的纯函数`analyze_cell(meta, rows, source_specs, origin)`，同时保留原音频端点、raw/去空白LCP变化和版本化occurrence寿命；为新scope另冻wrapper/config和原信用对齐门。不要根据新prototype表现改变归一、角色、分母或音频映射。

Gate：`B/results/revtrace/dsn_native_content_20261029/analysis_v1/GATE.json`，状态PASS_ALL14_ORIGINAL_CREDIT_AND_TEXT_ENDPOINTS，SHA256 `65e763b6b7871a8b92c66d825b3362db6b0ef3f4fa812034f8078895a677aa49`。本地`RESULTS_v1/DOWNLOAD_VERIFICATION.json`给出全部文件SHA。所有远端CPU/IO已释放；不需要新GPU或再扩审计。
