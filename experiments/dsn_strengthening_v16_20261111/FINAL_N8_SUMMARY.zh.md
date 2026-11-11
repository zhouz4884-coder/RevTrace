# 最终N8 Fullcall–Ready-only：同合同实测汇总

**类型：已闭合有界结果的可复现算术，不是新增模型、工作负载或服务实验。** 仅取PILOT24中的两臂8格、next2确认8格、last4确认16格，共32格。其他pilot臂与RESOURCE8不混入。原8-sourcebank的pilot2与后续确认6分列，不能称8名从未使用过的新声音。

实际NN均为`de0936b2e30179d63aeef6e235cd1af685578c58`；pilot controller为`f367c4e1068a9391a0e99d8537c94995a3388e13`，后两批为`4fb6d05f1cf4ad80e73bae9934afaed04c60edeb`。三批全部闭合，32个原任务GATE均PASS。每臂全offered分母137.864125 audio-s，包括partial EOS；每speaker两次timing重复一起计。

| 指标 | Fullcall | Ready-only |
|---|---:|---:|
| 及时音频信用(s) | 129.460000 | 58.500000 |
| 及时信用比例 | 93.904052% | 42.433084% |
| 原任务门 | 16/16 | 16/16 |
| 整场D2/C8通过 | 10/16 | 0/16 |
| 每run D99的中位数(s) | 1.630878 | 5.008969 |
| Worker occupation(s) | 223.214949712157 | 322.990538774990 |
| 两板origin→确认物理drain能量(J) | 91879.705750450 | 117822.717631776 |
| 两板J/全offered audio-s | 666.451158 | 854.629278 |
| 唯一派发job | 328 | 520 |
| 实际Owner admitted ready-result复用 | 0 | 3 |

总体duration-weighted差为 **51.470968245pp**；speaker等权配对均值为51.626475768pp。8/8来源、16/16重复对均Full>Ready。能量总差-25943.011881J（-22.018684%）；worker总差-99.775589062832s。这些是完整策略的实测交换，不能把全部能量或worker差归因给某个取消检查。

## 逐来源（两次重复合并）

| 来源 | 阶段 | 每臂offered(s) | Full/Ready信用(s) | 差(pp) | Full/Ready pass | Full/Ready worker(s) | Full/Ready能量(J) | Ready实际复用 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| BAC009S0769W0190 | pilot2 | 16.840125 | 16.840125/6.500000 | 61.401712 | 2/2 / 0/2 | 24.199871/38.753433 | 11272.080/14739.872 | 0 |
| BAC009S0901W0183 | pilot2 | 16.276125 | 15.500000/6.000000 | 58.367701 | 0/2 / 0/2 | 27.564766/43.392005 | 11104.840/15506.835 | 0 |
| BAC009S0902W0343 | confirmation6 | 17.131875 | 17.000000/7.000000 | 58.370727 | 0/2 / 0/2 | 30.489647/42.438051 | 11870.493/14484.090 | 1 |
| BAC009S0906W0197 | confirmation6 | 16.661875 | 16.661875/8.000000 | 51.986196 | 2/2 / 0/2 | 26.947036/40.294440 | 10851.607/14138.219 | 0 |
| BAC009S0907W0440 | confirmation6 | 17.151875 | 17.151875/10.000000 | 41.697336 | 2/2 / 0/2 | 25.433163/37.116962 | 10918.372/13935.551 | 2 |
| BAC009S0912W0434 | confirmation6 | 18.000000 | 18.000000/7.000000 | 61.111111 | 2/2 / 0/2 | 27.044594/42.149651 | 11469.696/15590.095 | 0 |
| BAC009S0914W0456 | confirmation6 | 17.806125 | 17.806125/8.000000 | 55.071640 | 2/2 / 0/2 | 27.779608/39.154742 | 11289.046/14624.997 | 0 |
| BAC009S0915W0286 | confirmation6 | 17.996125 | 10.500000/6.000000 | 25.005383 | 0/2 / 0/2 | 33.756266/39.691256 | 13103.571/14803.059 | 0 |

## 阶段、计时与证据范围

| 阶段 | 策略 | 来源/cells | offered(s) | 信用(s) | 信用比例 |
|---|---|---:|---:|---:|---:|
| pilot2 | fullcall | 2/4 | 33.116250 | 32.340125 | 97.656362% |
| pilot2 | ready_only | 2/4 | 33.116250 | 12.500000 | 37.745820% |
| confirmation6 | fullcall | 6/12 | 104.747875 | 97.119875 | 92.717752% |
| confirmation6 | ready_only | 6/12 | 104.747875 | 46.000000 | 43.914972% |

Worker区间使用已闭合唯一job：completed的reported worker_job_wall_seconds，abandoned的end−begin；没有把嵌套infer再加一次。Full为282installed+42preC+4完整丢弃=328，Ready为282+208+30=520。零missing worker timer，dispatch/terminal集合与controller accounting一致。完成调用已观察infer和分别为200.208906109445/213.222831466235s，但42/208个abort缺infer timer，因此**两臂total infer均NA**，不是上述完成调用和。它们也不是GPU-active时间。

两板能量直接使用已存在controller的common_external_energy.origin_to_confirmed_physical_model_drain积分，initial cold load/reference费用另列。保留原外部采样/物理drain观察边界；未将同显存当作同能量，也未新增功耗实验。Ready三次真实复用来自S0902一次、S0907两次；零命中的pilot仍保持原数。

可选有限诊断已保存在JSON：8source双侧标签翻转2/256；确认6为2/64。两次timing重复随speaker一起交换；这是固定配对输出的条件诊断，不是随机部署或总体检验。leave-one/two的范围只是有限子集敏感性，不是置信区间。正文可只报告逐source同向而不放p。

Worker finishing derivation实际源`a3ebaf9ccd5e579b7f28a17d308d0c93aac43729`，2个missing/duplicate控制通过；其CONFIG/ENVIRONMENT/RUN_RECORD/GATE、原输入hash前后不变及pilot8与OPV1精确交叉核对均保留在final_n8_worker_ops。没有新模型或场景。三批controller/每cellGATE和RUN_RECORD SHA在FINAL_N8_SUMMARY.json的input_hashes中，算术脚本SHA另列derivation_script_sha256。

## 写作与复现入口

- FINAL_N8_SUMMARY.json：完整32cell、8source、阶段、既有门、源身份、计时和能量口径、输入SHA、公式/schema。
- FINAL_N8_PER_SOURCE.csv：8行宽表，可直接生成source配对图；每行均合并同source两次timing重复。
- sourcearithmetic.py：只读有界controller结果与已冻结worker派生表的算术脚本。
- 已完成原8speaker旧NN4f Conservative比较为另一个证据银行；即使Full的129.46s恰好相同，也不替换本轮Ready-only结果。

五个LaTeX宏推荐值：NativeFullCreditPct=93.90，NativeReadyCreditPct=42.43，NativeCreditGainPP=51.47，NativeFullWorkerSeconds=223.215，NativeReadyWorkerSeconds=322.991。最终原始精度见JSON。
