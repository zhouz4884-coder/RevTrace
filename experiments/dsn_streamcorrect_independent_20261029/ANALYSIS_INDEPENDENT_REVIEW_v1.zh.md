# 本地独立复核：新四 speaker 分析模板

对象为冻结分析源 `7d4cded8f587b6f538091c751ede15c22f100caf`，不是 bdfa 方法改动，也未读取新16格中间结果。本地完整22项 CPU controls 实际通过。此复核不启动模型、不做远端读取、不产生真实新16格重计。

发现一个必须在真实重计前修复的确定性代码错误：`analyze_confirmation.py::main` 先用 `frozen` 字典保存 source receipt/metadata/appraisal/method provenance，随后 cell 循环又用同名变量保存 `Path(frozen_config_dir)/config_name`，下一行访问 `frozen['source_receipt']` 必然 TypeError，后面的 acoustic summary 也会受此覆盖影响。已通知 SC 冻结新 source，仅将配置路径变量改名并增加真正执行微型主 driver cell-loop 的控件；7d4源保留。现有22项函数控件没有执行这一路径，故通过并不能排除此错误。服务方法、计划和计时实验不受影响。

其余关键语义绑定符合本轮合同：

- `normalize` 虽名称沿用旧稿，实际保留完整 state，并精确核验 bdfa stage_execution，不删除字段。fidelity 串联 install 的 job ID、真实 job start/end、WAL/history、完整原参考 state、C选择与返回IDs；原参考须从 genesis 开始并连续。
- 两臂输入和设置一致、同 repeat 的 GPU 角色一致、按冻结相邻 block配对；期限仍 D2/C8，保留 missing、partial EOS 和全部 offered 分母。主差以整数 samples计算后换秒。
- directional judgement 先合并每 source 两次 timing pair，再统计 4个声学来源中正向者；总差为正且至少3/4来源合计正向。未将8次计时重复或272个 frontier 当独立声学样本。
- 同source四格最终质量要求完全相同；CER独立按完整最终文本重算，声学级 summary另保留一次计数，避免质量样本数膨胀。
- 内容侧按首次覆盖行的实际可见 frontier G 查同G完整Canon全文；没有把更长文本截断成 F，也没有拿更晚或更高G替代。同G未知保持未知，raw/空白归一化独立，原服务信用和后验支持信用分别列出。
- 物理 model-active promotion 使用 `model_start < parentCanonInstall < model_end`，与 worker-owned区间及跨卡真实model overlap 分别计数。已知失效退出核实际同start Canon反例，不将未知未来input称必然失效。

正式执行仍应等全部16格 terminal PASS、相同controller完整退出、GPU释放及有界复制逐文件SHA完成；冻结新分析源后运行，不能把本review或控件当新源服务证据。
