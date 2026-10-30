# 正式short28与sustained8计划构造器：已准备，未冻结/执行

默认是纯dryrun；`--self-test`只检计划排列不读模型；只有root显式`--freeze`才读取最终干净runtime及已通过参考，输出exclusive配置和计划。工具不改CURRENT、不访问远端、不运行模型。计划版本可与runtime版本不同：remote source目录/manifest由实际传入的runtime路径basename决定，不因计划叫v1就强绑9492或source_v1。

## 已准备的原任务参考

独立CPU exporter源 `293528d84a103054860051db90aeb36766b6b141` 的13项正式控件与固定真实输入导出已由execution_continuation在root source/noarg窗口执行通过。`SHORT_REFERENCE_EXPORT_RESULTS_v1/DETAILS.json` SHA为 `db1d90dc445ed9e63e9fe201e462e25bc8e2ae464bac002fc33ff25d5baa5785`；gate SHA为 `9fc54b1d146f6c3da50e757e68f3aae2d7f9781bf2c17e4ca3dc449c6c1cd2cf`。85步为旧bdfa保守S0764/r0真实17步加原新4离线68步，完整state/C/IDs与三记录、dispatch/install、依赖链和EOS均交核。没有将99运行重标bdfa，也没有重放服务性能。

## Short28

```powershell
python -B experiments/dsn_native_resilience_20261030/ops/freeze_formal_short.py --self-test
python -B experiments/dsn_native_resilience_20261030/ops/freeze_formal_short.py --freeze --version v1 --runtime-manifest experiments/dsn_native_resilience_20261030/packages/SOURCE_FINAL.json --runtime-source experiments/dsn_native_resilience_20261030/source_FINAL
```

上面FINAL是待root决定最终runtime版本的参数示意，不是已经存在/已执行的文件。

主24格：固定S0908，none、duplicate_late、worker_after_asr、worker_partial_frame、owner_before_durable、owner_after_durable，六条件×两臂×两fresh。source不独立于开发，定位controlled failure/timing coverage。另S0764/S0905各两臂一次正常回归4格。seed2026103031；normal与回归共8格先行，各pair block打乱，fault20格block独立打乱；第二fresh颠倒第一fresh的arm顺序、主GPU0/1换位。fault target固定32000，maxservice240，原2/8、全部offered/EOS、质量/能耗/恢复时钟保留。预计476个Canonical转移。

默认参考remote路径为项目P下 `SHORT85_REFERENCE_DETAILS_v1.json` 和 `SHORT85_REFERENCE_GATE_v1.json`；execution_continuation须stage本地同SHA原字节。CLI可在freeze前显式覆写remote路径。各cfg `reference_kind=short_bdfa_static_source_mapping`、require_reference=true；只静态映射stage_execution.source_commit，别的字段不忽略。

## Sustained8

```powershell
python -B experiments/dsn_native_resilience_20261030/ops/freeze_formal_long.py --self-test
python -B experiments/dsn_native_resilience_20261030/ops/freeze_formal_long.py --freeze --version v1 --runtime-manifest experiments/dsn_native_resilience_20261030/packages/SOURCE_FINAL.json --runtime-source experiments/dsn_native_resilience_20261030/source_FINAL --reference-gate PATH_TO_ACTUAL_LONG_GATE
```

仍须绑定真正完成的long gate，且它的source_commit严格等于最终runtime；不能在875原步＋875恢复边验证完成前制造PASS计划。若root之后修改NN源，旧long reference不能当同源全字段参考。长DETAILS很大时无需本地复制；按实际gate的details SHA绑定8TB raw路径，--reference-details本地文件参数可选。

两条合成流S0770/S0903，228.51025/208.1003125秒；两臂×两fresh共8格，seed2026103041，pair blocks随机，r1反序及GPU换位。只有合成最终EOS，不加接缝reset、静音或重采样；不称自然连续录音。maxservice固定1200，原2/8/alloffered与每臂两重复的1750 offered边界保留，预计3500个Canonical转移。两个speaker不是八个独立声学样本。`continuous_original`严格全字段，不进行SourceTag投影。

## 给通用campaign operator的共同schema

两计划沿用pilot的source/environment/reference SHA、cells[].config/config_sha256/out/log/arm/fault_kind、expected_cells与原始/summary/gate路径，另外直接提供 `campaign_kind=formal_short28/formal_sustained8`、`reference_gate`、`reference_gate_sha256`。冻结配置require_reference=true。

不能复用硬EXPECTED6的开发operator。正式generic operator由execution_continuation另行独立源码冻结，逐trial调用最终NN源、核完整task/ref与真实退出/GPU释放后再下一格；遇失败保留停止，不覆盖旧输出。开发6、正式主24、回归4、长8的证据tier分开，冷故障SLO失败不自动否定正确恢复，也不能因此隐藏期限损失。
