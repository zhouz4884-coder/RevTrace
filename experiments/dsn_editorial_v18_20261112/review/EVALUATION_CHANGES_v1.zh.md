# v18第05节改写交接

唯一论文改动：隔离v18树`sections/05_evaluation_v16.tex`。v17种子约2856词，交接稿约2120词，减少约736词。没有改main、其他章节、bib、宏、图、表或既有release，没有编译/新实验。

已完成：

- **B** 放回三cohort信用交互18.530/6.205/17.555s。先定义`I=Y11−Y10−Y01+Y00`，再以各source原信用fraction为Y，给mean5.90pp、描述性95% bootstrap[1.13,10.28]pp；与N8配对差、U_norm分开。
- **A** 加入另一开发银行c16r2的反排名：compute-only201.960s vsjoint194.735s，但原D2读点缺失4.000audio-s vs0；首信用与持续可用性成为不同的实测目标。
- **C** 旧四source bank的92次真实model-active promotion、20个tentative ASR successor不同于原C/U结果，连接“输入资格”和“输出选择”。没有给旧银行贴当前NN身份。
- 当前N8正面结果全部保留：最终宏、8来源/16重复同向、各源2×2严格信用优势、三源资源轴方向、3次真实Ready复用、SLO10/16vs0/16、源聚类留一及条件标签翻转。P99的1.67/4.98明确定义为source内两次per-run P99的median再跨source取median。
- 290变为sampled job/install predicate comparisons；278current-input matches/12refuted profiles和实际policy retention分开。Full/VDag实际56、Ready56重派/49+9、UIR两次拒绝与S0901 1.5s保留。
- 纠正fixed-lag为generic control，citation改`papi2023alignatt`。
- 负paired_jitter明确`R11−R10=−4.245s`、`I=−2.245s`，仍保留5次兼容超前机会；primary-sync `−.790s`、`I=+2.565s`，仍保留3次。机会计数作为实际执行诊断。
- 删除“双峰确定服务水平”、two independent native banks、跨runtime相同事件结构、旧40.62对当前42.43的因果比较、text-equality未测性能臂与soundness→completeness等表述。

保留`eq:credit`、`fig:main_evidence`、`fig:native_confirmation_v16`，以及完整表输入`tables/native_confirmation_v16`对应的`tab:native_confirmation_v16`。五个Native宏仅引用，没有改定义。E原引擎参考和D协议cost留给Root单独整合。

静态核对仅限所写源：花括号数量一致，现有figure/table/input路径与宏名保留，七小节组成连贯的问题链。编译和全稿统一检查由Root进行。交接时源SHA：`340116eb003455628ac1edf50b93d3d87db6c8c43200b5854fd47f3e6f56fe15`；Root后续压缩B段/加入cost后应使用其新版本身份。
