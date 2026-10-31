# 首个 parent 注入位置的原始证据核对

2026-10-31；只读原8TB日志，0新模型调用、0 signal、0远端写入。没有修改fixture源码、NN59或CURRENT。

结论：**两个选定位置在已知原正常格中均满足完整start合法性，而且ASR均实际派生了条件child；不增加新的timing选择机制。** 负控父虽然出生时是conditional，但前一Canonical在该父ASR发送之前已完整确认其start，未发生“首个parent先被refute”的交错。该结论仅用于已知注入点前提；不保证所有未来时序自然重现，正式运行未触发仍应失败保留。

原cell：`SC_FORMAL_SHORT28_v1_BAC009S0908W0369_none_fullcall_r0`，NN源 `4f4c3caba2b1068951d7a566e7d9e5aa6fc25f47`。

共同原始目录：

`/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/dsn_native_resilience_20261030/formal_short28_v1/cells/SC_FORMAL_SHORT28_v1_BAC009S0908W0369_none_fullcall_r0/`

## 正控 parent：16000→24000

- 所有相同start/end边界的dispatch只有1条：`owner_e0/dispatch.jsonl` **第3行**，原job `e0-j000000003`，slot `full0`，PID `2217338`；`started_on_canonical=true`。
- 原job完整start SHA为 `cce0b7c44ea17f37e3323ea4af8b9e1f781d7805d49d2a19f318dd32a71667f6`，与实际同frontier Canonical F16000的完整cut逐字节相等；其birth Canonical SHA也是同值。
- 该真实Canonical来自原job `e0-j000000002`，WAL sequence **3**，offset `[80925,151045)`，record SHA `b13593ea78d8a4cf154013834ef01593d8144367a8fc1632c3062cfb303b6dc2`；原Owner安装为 `owner_e0/owner_events.jsonl` **第6行**，perf `5109736.169733079`。
- parent ASR为 `owner_e0/worker_results.jsonl` **第6行**，原`sent_perf=5109736.823199123`。其完整projection end SHA为 `264652c8230cb0f5fe873170975b170f3a82de7f003dc3baac853a9f86ba3169`。
- 实际child为dispatch **第4行**，原job `e0-j000000004`、24000→32000、`started_on_canonical=false`，dispatched perf `5109736.889725027`；其完整start逐字节等于上述ASR projection，SHA相同。
- parent完成为worker_results **第7行**，实际end完整SHA同为 `264652c8230cb0f5fe873170975b170f3a82de7f003dc3baac853a9f86ba3169`，真实selected_correction存在。

## 负控 parent：24000→32000

- 所有相同start/end边界的dispatch只有1条：dispatch **第4行**，原job `e0-j000000004`，slot `full1`，PID `2217341`；它就是上面的实际条件child，`started_on_canonical=false`，birth Canonical仍为F16000。
- 其完整start SHA为 `264652c8230cb0f5fe873170975b170f3a82de7f003dc3baac853a9f86ba3169`，与随后真实同frontier Canonical F24000逐字节相等。
- 真实F24000来自原job `e0-j000000003`，WAL sequence **4**，offset `[151045,222678)`，record SHA `8e821d832966917f64a19b41395e416ee502de3864886387afc0e257737aaac5`；原Owner安装为owner_events **第8行**，perf `5109737.194581296`。
- parent ASR为worker_results **第8行**，sent perf `5109737.275362856`，**晚于上述真实父输入确认**。因此按该ASR进入hold时，该parent的完整start已经获Canonical确认。
- 该ASR完整projection end SHA为 `d25f4c1b78a3dbf8603e3184a5073ac5ef464f17e536d47ce8445ba33ad53e17`；实际提供的条件child为dispatch **第5行**，原job `e0-j000000005`、32000→40000、`started_on_canonical=false`，dispatched perf `5109737.404643965`，完整start与projection逐字节相等、SHA相同。
- parent完成为worker_results **第9行**，实际end完整SHA `951d27d89c334b8d15689a4ecb0f033a589feaee6a7a2352054cd6ef8b778827`，与其projection不相等，真实selected_correction存在。这是父输入在child的start frontier处被实际C/U修订的预定负控；不是该parent自身先被前一Canonical否定。

## 原始字节绑定与核对方法

行号均为1-based物理JSONL行。方法：流式解析原dispatch/results/Owner日志；独立解析原`RVN1`二进制WAL，逐frame校验长度、SHA256、canonical JSON编码、previous hash与连续sequence；对上述原job.start、实际同frontier next_state及真实child.start使用完整canonical JSON bytes比较，未只比较文本或frontier。

| 相对文件 | bytes | 完整SHA256 |
|---|---:|---|
| `owner_e0/dispatch.jsonl` | 1262585 | `b13c29e6c568b8bd75f32ca922bd2a6792cb1ea0a4ec4bfece70eb2312bf8551` |
| `owner_e0/worker_results.jsonl` | 1042486 | `d37ed1b1e16f48d5c612c4acfad8bb6a4d0aa0126c6e0a6c9e4c0406f98bf5e8` |
| `owner_e0/owner_events.jsonl` | 22675 | `6bf7e0436f906249e52fdd953e50db1abfbc8cc67d51d2d772798950db5bf6ad` |
| `facts.wal` | 1426206 | `8ef78d1533ab0ddd868845f3cd58a3d123fdcf63684b36857b8df135d83a755b` |

该核对未产生新的神经/故障格结果，也不重新标注旧run。若未来正式fixture因另一个实际first-parent interleaving不满足上述前提而未触发，应按冻结配置保留失败，不能以本页替代其自身实际输入/OS/CUDA/fence/消费证据。
