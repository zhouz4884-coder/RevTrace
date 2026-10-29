# c7 原方法身份误拒绝：实际 CPU 定位与窄修复

失败的 `equivalence_v1` 原样保留。它在首个 0.5 s early input 完成后、第一次 C-entry projection 时因原 infer 的 code identity guard 失败；不能把这次失败解释成 C/U 语义不等、模型选择不同或已完成 69 输入。

同一原 native 环境中的 import-only CPU 检查显示：实际加载的原 infer、SpeechLM C 和 LM C，与固定原作者 **完整 module** 正常 compile 得出的 code 在全部比较字段、常量、flags（另含 exception table）上均一致；它们仅与 helper 裁剪 class 后编译的参考 co_code 不同。clean 方法两种编译完全相同。没有模型实例、GPU 初始化或推理。

具体环境是 Python 3.12.13。完整 module 编译可见 `time`/`torch`/`np` 的 module import 绑定，调用编码例如 `LOAD_GLOBAL(NULL + time)` 接 `LOAD_ATTR(time)`；裁剪 class 失去模块级绑定信息，编码变成 `LOAD_GLOBAL(time)` 接 `LOAD_ATTR(NULL|self + time)`。infer offset 66/76 与 C 中 np.array、torch.no_grad 等位置能直接检查。co_flags 没有差异，因此 `future annotations` 的最初猜想被实际对照排除。DETAILS 内 dis 的一个嵌套 lambda repr 包含进程地址，那只是展示字符串地址差，不能算额外语义或 code 差。

窄修复只在新的 `source_v2/native_tail.py` 和 `test_native_tail.py`：方法 oracle 改为 compile 固定原 raw **完整 module** 后取 class/method code，不执行 module；保留原 exact co_code/co_flags/source/class 与 Authority/identity 分离检查。suffix 仍是同一固定原 AST，C/U 未替换。测试 fixture 也不再裁剪 class，因此不能与 helper 一起犯相同错误。新增独立完整编译 oracle、同输入重复 C/IDs/feedback、原 native loaded class 的无 model 构造合法性检查。

Windows 开发 33 控件中 32 PASS、1 项完整 native package 检查明确 skip；该单项必须在实际 Linux native 包上执行而不能 skip。最终新的完整 frozen source CPU/神经门由 SC 统一执行，不能用这些开发控制替代。

证据：

- 原 CPU 定位 source `e27e57a`，plain snapshot/manifest/bundle 均位于本 family；带指令明细的 source `c9c0e02` 独立冻结。
- 运行 `identity_diagnostic_v1`、`identity_diagnostic_v3` 均 PASS_CPU_IMPORT_ONLY_IDENTITY_DIAGNOSIS_RECORDED；gate SHA 相同为 `fca7f11886908715632c93d250c7ccb4e4fcb68fb568ee4b594b86338823ac41`，因为摘要比较内容相同，v3 的完整指令详情另存在 DETAILS。
- `identity_diagnostic_v2` 的 wrapper 曾错误指向尚不存在的远端 source_v2，在 git 路径检查阶段失败；没有 import 或模型执行。该 orchestration 错误及 gate 完整保留，v3 指回 c7/source_v1 后成功，未覆盖 v2。
- `identity_diagnostic_results_v1/COLLECTION_MANIFEST.json`：17 个 bounded 文件，共 47,207 B，逐文件与远端 SHA-256 相同。这里没有重读大型模型或旧 raw inference logs。

故障类别是方法身份 oracle 的编译单元不一致，不是已证语义假设失败，也不是有限精度导致的选择差异。新 69 输入神经门仍须独立完成；旧神经失败没有重命名为 PASS。
