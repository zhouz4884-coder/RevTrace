# Buffer fixture 独立审查修复记录

2026-10-31；development，未运行新NN、CUDA或正式故障格。

审查原件已逐字节移到本目录 `BUFFER_FIXTURE_INDEPENDENT_REVIEW_v1.zh.md`，SHA256 `4dfff1c6ea9a81276fa0999594348906602de6ae9ad9f7e84d31df47b275e004`；其原 `buffer_fixture_source_dev` 内副本已删除，审查文字不计入执行源码依赖。

## F1：释放证据必须绑定同一个原 child

`validate_release` 现在强制接收来自原始日志/marker的 expected child job、expected started row、expected child marker。它逐字节比较 release 自报对象和这些 expected 对象，再验证原 fence；并比较 child-marker SHA。controller、独立audit和等待中的父worker三条路径均显式传入这些 expected 值。父worker额外从原 dispatch、worker_results、owner_events 读取 expected 身份，不能用release对象自己证明自己。

新增反例保留完整合法 fence，但将其与外来 `e0-j999999999` 或外来 incarnation拼接；现在拒绝。原job完整start/birth/inc、原payload和原Owner接收路径不变。

## F2：冻结路径与实际输出目录同时约束

新 `fixture_paths.py` 在plan阶段按目标POSIX语义拒绝 `..`、`.`、重复分隔符、反斜杠、相似字符串前缀等路径别名。配置冻结具体raw_root和每cell raw_result_location。正式运行时要求 `--out` 与冻结的 `<raw_root>/cells/<cell_id>` 完全相同，验证实际B盘及results目录，逐级拒绝symlink/junction，并对解析后的目录做严格is_relative_to检查。watchdog目录也固定到同一raw_root下的预定cell目录。

新增真实CLI入口函数的反例证明：普通入口和内部child入口均在任何源校验/神经工作之前拒绝任意 `--out`。本机Windows若不能创建symlink，测试明确验证拒绝分支；正式Linux CPU运行可直接创建真实symlink再验证。

## F3：外部进程硬墙钟

普通CLI和公开 `run()` 均先启动独立watchdog，再以独立session创建实际fixture子进程。子进程在任何Owner启动之前验证watchdog父PID/start_ticks、自己的PID代次、cell/nonce与配置SHA。冻结的外墙钟为900秒，另有40秒清理和5秒CUDA-CLI查询超时；原D2/C8未改，service bound严格保留原template的240秒，不采用早期开发builder的360秒值。

watchdog调用共享新harness的 `run_paired_campaign.stop_owned_processes`，不再维护第二套清理策略；它以本次登记的PID/start_ticks与已知成员证明为依据，只停止本run的Supervisor/Owner/后继session，使用有界CUDA查询。query失败仍是资源释放未知，不能写PASS或按已释放继续NN。

复核还发现并修正了一个额外边界：零退出码若在硬deadline之后才被观察到，也按TIMEOUT处理。合成clock `[0,901]`、900秒限制、`poll()==0` 的反例现在确实调用清理。

## 当前验证

`BUFFER_FIXTURE_DEVELOPMENT_CPU_v11.json`：25/25通过，0 failure、0 error、0 skip；0神经调用、0 NN worker signal。测试创建并终止了1个明确归属自己的CPU睡眠子进程，验证外墙钟不依赖被阻塞的子进程事件循环；不能将其表述为真实NN/CUDA故障见证。旧development v1–v10记录保留，其中v1/v2为本机sandbox临时目录/硬链接权限失败，后续修复后重测。v11额外断言builder保持原template service上限。

执行源仍在独立development Git checkout，尚未由本代理提交或冻结。最终配置须等待共享harness v2真实commit/manifest固定后构建，不能继续使用78b... v1身份。NN4f59文件、C/U、输入资格、来源及既有实际run均未改。
