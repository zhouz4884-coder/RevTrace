# MAGICDATA test header源已冻结；短CPU门通过

实际短实验：`REVTRACE_MAGICDATA_TEST_HEADER_CONTROLS_20261111_V1`。12/12 controls通过，0 skip；新程序独立重核官方metadata的24,279 WAV与43个test speaker join。**真实test归档没有开始下载，逐WAV时长与候选N仍未知，没有选择speaker。**

冻结身份：

* 新完整source commit：`3e5bedcc08ea1872707a7d01c965252e639abde4`；6文件，local与remote clean、逐byte/SHA匹配。
* Source manifest SHA：`a9b2c80a4a8c408add456680073a709dd1e80adb787d998ed4f1c9ec5e91ca77`。
* Bundle SHA：`51e25f85c8f1dce1cd6a28ebdd4c4ff6e27b7a865f37e529f5dcccb704901241`；root可解析ref：`refs/research/magicdata-test-header-v1`。
* Config SHA：`c3c8c925ac4e196a1860ba963778394c44498a0e61441d09201fc20275e4e1d2`；frozen environment SHA：`a87944db26db5d44d07ed243133a0fc11ddcda89f3bac701f2d3d0cd1a39741d`。
* SUMMARY SHA：`ce79bc79fdd8eb5e4f20875827d5eac86503660fe00fadd6377e114693a7a37c`；GATE SHA：`09de847718a69b57f629627d10fe8271b2dd69a3793cf4235a7a2bac4d139270`。

启动前已记录ID/config/env/代码与完整manifest、8TB raw/summary/gate。Root默认无参preflight和显式header source+run-record预检均PASS；本次前后默认CURRENT仍为NN4f，任务没有改写它。后续root合法激活GPUdriver时，header source仍用独立显式身份；launcher只记录当时默认pointer，不要求它保持4f，也不恢复旧pointer。

12项覆盖：非44字节header、odd JUNK与扩展fmt；extensible PCM及精确时长层边界；stereo/其它sample rate不默默转码；截断/越界RIFF；多data拒绝；path traversal与train/dev；完整小archive管线及TRANS从不extractfile；missing/speaker mismatch；symlink拒绝；强制gzip EOF校验坏CRC；HTTP206/range/size/ETag/URL续传绑定；原member byte hash而不decode。

原短run PID2775230/start614273353已退出。Primary raw在8TB：

`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_strengthening_v16_20261111/magicdata_header_v1/controls`

10项bounded原输出逐SHA取回`MAGICDATA_HEADER_CONTROLS_v1/`，含原日志、config/env、run record、events、summary/gate及launch身份；`COLLECTION_MANIFEST.json`保存remote路径/bytes/hash。短gate是CPU源与元数据join门，不是完整音频header census或GPU性能门。

## root协调后的长任务入口

源码、完整config/env、remote source已经就位。root确定与GPUdriver激活/constructor profiling不冲突的时段后，可执行：

```powershell
python -B experiments/dsn_strengthening_v16_20261111/header_ops/remote_header_v1.py launch --mode acquire_census
```

该命令重新记录默认无参preflight、显式新source+运行输入gate，另建 `REVTRACE_MAGICDATA_TEST_HEADER_CENSUS_20261111_V1` 的异步PID/startticks/command hash与prelaunch记录；不会覆盖短run。新raw根为上述父目录的 `acquire_census/`。官方2,201,936,013字节test归档保留该8TB根；完整SHA/MD5与gzipCRC/EOF、tar安全、全WAV RIFF/metadata join一起通过才给header census PASS。已冻结官方checksum缺失状态，不假造official SHA；source/history census仍明确pending。

```powershell
python -B experiments/dsn_strengthening_v16_20261111/header_ops/remote_header_v1.py status --mode acquire_census
python -B experiments/dsn_strengthening_v16_20261111/header_ops/remote_header_v1.py collect --mode acquire_census
```

status只认同一个PID/startticks/command，超时不重启；下载有3次同归档受限续传、45秒socket timeout和7200秒wall上限。完成后collector只取bounded结果，原archive与逐WAV技术行留8TB；后者会超过bounded单文件上限，不带回工作区。下载/重哈希/扫描的UTC/perf/CPU/IO/cache快照保留，不能把该活动期间的GPU constructor变化直接归因于loader或策略。

当前长任务尚未启动是root明确的技术协调顺序，不是等待人类许可。事前完整合同在 `plans/MAGICDATA_TEST_HEADER_CONTRACT_v1.zh.md`；实际冻结config和source在 `header_packages_v1/`、`magicdata_header_source/`。
