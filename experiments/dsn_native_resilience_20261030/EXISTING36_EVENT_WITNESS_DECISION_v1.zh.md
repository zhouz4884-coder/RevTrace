# 原36事件分母与跨进程退出view证据

这是对原8TB冻结结果的只读核查，不是新神经实验；没有发送任何signal。

3976个实际安装Canonical中，3622从Canonical输入发起，354是在飞条件调用在完整父输入确认后提升。按fullspec_policy的jobs/completed_full分离与job flags判据，completed-full-buffer安装总数为0，跨dead producer/fenced incarnation的完整buffer安装消费亦为0；不能从90次compatible-ahead view保存推断buffer复用。

4个worker-after-ASR格记录了另一个真实对象：原job/inc的ASR whole view已被实际Consumer消费；随后producer物理退出、CUDA释放并incarnation fence，Owner的retained_view_jobs仍含原UID。在完整Consumer日志中，下一次状态更新直接是同frontier的合法Canonical认证，没有中间清空记录。新Canonical修正了旧ASR预测，所以这是条件view持续驻留直到合法reconciliation，不是旧预测最终正确，不是post-death再次应用旧UID，更不是完整C/U buffer安装。

| cell | original consume perf | kill requested | exit confirmed | CUDA release | fence known by | next canonical perf | old/new text same |
|---|---:|---:|---:|---:|---:|---:|---|
|SC_FORMAL_SHORT28_v1_BAC009S0908W0369_worker_after_asr_conservative_r0|5111392.698140603|5111392.724595783|5111394.018257815|5111394.149829335|5111394.153706635|5111394.967831179|False|
|SC_FORMAL_SHORT28_v1_BAC009S0908W0369_worker_after_asr_fullcall_r0|5111502.856634989|5111502.873634764|5111504.141376308|5111504.285629508|5111504.289336347|5111505.03881072|False|
|SC_FORMAL_SHORT28_v1_BAC009S0908W0369_worker_after_asr_fullcall_r1|5112266.487853434|5112266.50251293|5112267.840567601|5112268.013835635|5112268.017485361|5112268.725924968|False|
|SC_FORMAL_SHORT28_v1_BAC009S0908W0369_worker_after_asr_conservative_r1|5112337.679865676|5112337.689740649|5112338.748214852|5112338.902735274|5112338.906350821|5112339.598450335|False|

4格原UID均为e0-j000000004/inc0，原visible frontier32000；实际Consumer原row8→后继row9，后继journal sequence5/certified frontier32000。完整state/text哈希、原注册input hash与raw输入SHA在EXISTING36_EVENT_WITNESS_CENSUS_v2.json逐格保存。连续驻留判断依赖已独立c4核验的完整Consumer日志与冻结Consumer实现，不是屏幕像素探针。

外部signal定点fixture在机制上可行：保持Owner/Consumer/ingress存活，SIGSTOP的是父模型worker而非Owner，待child完整回包被Owner登记为completed_full后，再kill该child并核old-inc/OS/CUDA退出，最后SIGCONT父worker；只有实际父C/U输出逐byte等于该child登记start，才有合法buffer安装。它只能补controlled witness，不能变成自然prevalence、性能成功或修复长流质量。现有view对象的跨death证据已足够支持窄正文句；完整buffer跨death仍按CPU/有限规格条件支持，当前不建议为此额外NN。

## 精确原行交叉索引

仅是既有c4已检查logs的交叉索引，非新GPU/正式实验。索引文件 `EXISTING36_VIEW_SURVIVAL_LINE_INDEX_v1.json` SHA `28cf945dba90b8d65f85523fb61943a230a4048b118067e9db78f3b2b38eecf8`；其每格列出原6文件绝对B路径、字节数与SHA、索引脚本字节SHA和c4实际总gateSHA。下表为1-based物理JSONL行号（不是0-based数组index）。

|cell|dispatch原job|worker ASR receipt|publication原view|Consumer原view→合法Canon|loss保留view|Owner death proof|fence后replacement start|Owner Canon install|
|---|---|---|---|---|---|---|---|---|
|SC_FORMAL_SHORT28_v1_BAC009S0908W0369_worker_after_asr_conservative_r0|4|8|9|9→10|8|12|13|15|
|SC_FORMAL_SHORT28_v1_BAC009S0908W0369_worker_after_asr_fullcall_r0|4|8|9|9→10|9|12|13|15|
|SC_FORMAL_SHORT28_v1_BAC009S0908W0369_worker_after_asr_fullcall_r1|4|8|9|9→10|9|12|13|15|
|SC_FORMAL_SHORT28_v1_BAC009S0908W0369_worker_after_asr_conservative_r1|4|8|9|9→10|8|12|13|15|
