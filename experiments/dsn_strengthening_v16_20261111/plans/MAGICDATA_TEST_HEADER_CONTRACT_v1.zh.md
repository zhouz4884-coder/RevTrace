# MAGICDATA test：获取与全成员header census事前合同

仅CPU技术就绪，不产生ASR/算法/未见speaker结论；不选择16人。短controls先运行，长下载须与root的新GPUdriver激活/constructor测量协调。CURRENT只记录，不由此任务改写。

官方来源为[OpenSLR68](https://www.openslr.org/68/)的test split，获取URL固定为`https://openslr.magicdatatech.com/resources/68/test_set.tar.gz`；仅允许页面列出的同名官方镜像，当前计划仅使用CN URL。冻结HEAD长度2,201,936,013bytes、ETag`"833ee08d-58e45ba913852"`。官方页面未列checksum；md5sum.txt/md5sum/sha256sum.txt三个有界官方相邻探针均404，记录于`review/MAGICDATA_CHECKSUM_LOOKUP_v1.json`。故expected official SHA256/MD5明确为null；下载完成后计算实际SHA256与MD5并冻结，不称已与官方公开digest匹配。

metadata原件SHA为`1f71e2dfea4706e76177158a6d45f2be838042af5ecc442f447f8369d40764c9`，test.scp SHA为`c1dc8d289fb8a245359428d0ad30624cc3eff620c3ada4b7b1359f532e6be600`，SPKINFO SHA为`b74de5e561d4e5b9e57248445413bb1ffe7415aca9ee72d7528799dc8d8f4d7f`。它们固定24,279个唯一test WAV、43个test speaker IDs；每条basename与relative path是一个成员的两个别名。新程序直接重核metadata join。

获取须以完整Content-Length和HTTPS/ETag绑定为前提；仅相同原归档允许限次网络续传，续传强制206与完整Content-Range一致。部分文件/错误保留独立raw目录，禁止把不完整归档当成功。raw不落Windows工作区，原tar.gz保留8TB；不抽取全体WAV。

扫描必须消费完整gzip至EOF以校验CRC/ISIZE及尾部；tar header校验、有限展开尺寸、path/type防护覆盖全部成员。禁止absolute/..路径、反斜线、drive path、symlink/hardlink/sparse/device/FIFO及train/dev成员。WAV basename必须与test.scp恰好一一对应，speaker目录必须等于官方metadata，缺失/额外/重复失败。TRANS和其它非WAVregular成员只跳过，永不extractfile/解析正文。

每个WAV按RIFF声明长度与所有chunk边界/padding读取，不准假设44byte。支持fmt16/扩展fmt、PCM extensible GUID、JUNK/LIST和odd padding；重复fmt、多data、尺寸越界/截断分列技术拒绝。原monoPCM16/16kHz、blockalign/byterate一致才进入候选；unsupported codec的时长保持unknown，不虚拟转码。duration由实际data frame数/sample rate计算，分层[6,12)与[12,20]。跳过payload时可算原WAV字节SHA，但不解码、听取、ASR、裁剪、拼接、重采样或写回原数据。

输出全部43个speaker的WAV总数、兼容/不兼容/结构拒绝/层外和两个层的数量，显式包括0；逐WAV技术行留8TB。available N只是技术候选人数；**完整新source-history census仍为REQUIRED_NOT_COMPLETED，禁止实际speaker/utterance选择或unused/pretraining-unseen声明。**

controls与acquire_census分别有ID/原运行目录，使用同一新完整源码commit/manifest/bundle和冻结config/env，显式源预检与root当前默认无参预检分别记录。短controls包含12个语义可区分的合成RIFF/路径/传输/整包CRC与TRANS不读控制，以及实际官方metadata join；无真实test下载。之后root可在明确命令下运行长acquire_census，无需人类新增许可。

UTC/perf起止、每5秒下载进度、每500 WAV扫描进度，以及本进程IO/CPU/page faults和globalCached/MemAvailable/Dirty/Writeback/vmstat均保存。下载、checksum和gzip/header扫描会消耗IO并使cache变热；这些区间必须与后续constructor profiling分开标记，不能把相邻加载称未测量的cold-cache试验。CPU程序不导入Torch/Transformers、不调用GPU、不清cache、不发无关进程signal。
