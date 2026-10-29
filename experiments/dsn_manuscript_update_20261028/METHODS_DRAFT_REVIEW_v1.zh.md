# 新技术草稿独立核对：一个实质措辞问题，其余边界基本成立

核对对象：新修订中 `02_contract.tex`、`03_continuation.tex`、`04_protocol.tex`。依据为实际冻结 f0a8e7bc 的 `continuity_proof.py`、`certified_display.py`、`kernel_runtime.py`、`composed_kernel.py`、`row_lifecycle.py`、Worker 同步/排空路径、`durable_journal.py`，以及已完成的 C1 CPU 见证和 native v8 adapter。没有修改这些草稿或源码，没有远端操作。

**总体判断：两条命题的强度适当。** 执行完整性作为明示前提，Private 不获得 Canonical 写权，不要求另一浮点调用逐位相同；R 的保守完整边界节点/唯一在途槽与 S 的直接冻结输入见证已区分；原子完整视图、实际 kernel 预演后授权/应用、row terminal 与 device drain、1154 状态模型的有限范围均与源码相符。

## 必须改的一处

`% LOGIC (03_continuation.tex:66) [Major] [P1]: guard失败后称“the incompatible continuation”把缺少该充分见证等同真实不兼容。`

`eligible_chain` 会在缺少 Private 同边界完成节点时拒绝，但一个已发布子调用仍可能凭自己的冻结输入直接从新 Canonical 根证明合法；本轮 CPU 见证已明确展示 R 拒绝而 Consumer 可接受。因此建议只改为 **“the continuation lacking this witness”** 或 **“the unproven continuation”**，不要修改算法或扩大 claim。

这不是说该实现错误；恰好是正文已声明的保守充分性。前文对必要性/最小性已有正确限制，应在动作句保持同样语义。

## 建议澄清的三处

1. `% SCOPE (02_contract.tex:16,28; 03_continuation.tex:56) [Minor] [P2]: 将core F/提示token表述与native full-cut映射区分。` f0 的反馈是完整 prompt token；native 的反馈还包括缓冲、context、cursor 等，不能统称 feedback tokens。更重要的是 native 的初始 buffer-only 更新可推进 `FeedbackCut.frontier`，但 `processed`/实际服务 certified frontier 仍不前进。建议保留一般 P=完整声明状态，把“tokens”限定为 Qwen 实现；在应用节明确 native 的状态边界和服务进展计账区别。
2. `% SCOPE (03_continuation.tex:89; 04_protocol.tex) [Minor] [P2]: 明确这些kernel/row/durability保证属于core runtime。` f0 的 `KernelView` 的确先 preview，再 kernel `apply-request`，最后实际状态替换与 `view-applied`；kernel逐项核 durable root、注册的完整 Private 结果、text/frontier与唯一祖先。native 受控适配则使用自己的 `FeedbackCut/Reconciler/Consumer` 和 journals，不复用 f0 event kernel 或 fixed-batch row retirement。应用节可以清楚给出此映射，而非将完整 core 恢复/排空保证直接转贴过去。
3. `% PRECISION (04_protocol.tex:52,61) [Minor] [P2]: uncertain application与early recovered-view能力加范围。` `durable_journal._append_records` 在写入不确定或同步后 `_apply_record` 失败时 poison，确实拒绝继续提交；这里的 application 是**持久 transition 的内存状态应用**，不是任意显示操作。建议写成“uncertain append or state-application outcome”。“recovered view before cold workers”是受控恢复配置能力，最好写“in the recovery configuration”，避免被理解为所有默认 startup 和 native 实验都已提供该行为。

## 已核实可保留的关键句

- R 的 `eligible_chain` 依次核同 F 完整 P、generation、每条冻结 input/chunk、实际 tip、唯一在途任务和 target 尚未覆盖；输入真实性和合同/epoch由外层绑定，正文已明示相应前提。
- S 的 `_compatible` 可以从直接冻结输入证明，也可以沿完整已发布祖先回溯；cycle/多候选在保守路径被拒绝。它与 R 不必接受同一组见证。
- kernel实际检查 durable根及完整text/frontier绑定。caller布尔值不是其授权依据；这不等于GPU算术证明，草稿已经正确区分。
- 完整行可先于共享batch排空发布。`RowInbox` 要求完整与取消终态互斥且具备精确manifest，Worker在 generation return 与CUDA同步之后发 drain；不能由完整 publication 或 CancelRequest 释放 lease。
- `commit_transitions` 只收集已验证、不同session的transition，不新增计时收集窗口，不提供多session全或无；同步后依次应用，每条ACK以相应持久事实为依据。短恢复前缀不被描述成未执行的组原子性。
- 1,154状态产品不覆盖完整多节点重根/在途 guard，草稿最后一段没有误称完整机器证明。两条命题是合同内条件性归纳及动作性质，表达强度合理。

**结论：改 P1 的一词关系，并在 core/native 映射处补清楚范围后，可以继续整合。** 不需要为这些表述追加 GPU 或把已有充分条件改成更复杂算法。拟新增 `05_execution_application.tex` 将明确 native 的范围与 empty-buffer 服务计账，且仅使用已完成 K24/96/native14 结果。

## 新增执行/应用片段交付

已新增 `sections/05_execution_application.tex`，约937英文词（含表与caption）、1个紧凑表。目标是让读者判断“实际排空是否换来有内容支持的服务”，再看到完整原生反馈合同及其容量/能耗边界。

段落顺序：K24固定设计 → 严格同输入/同批后继 → 96行内容及新增期限分解 → mixed/能耗边界 → native完整cut与core范围区别 → 强双完整副本及质量/容量表。

| 片段主张 | 证据 | 状态 |
|---|---|---|
| 六同步批96行真实推进、同F完整原文支持 | 已完成K24、冻结c25诊断、same-F全24/96 CPU补强 | supported |
| 原期限制约下K收益混合 | 原24全部run与逐前沿gained/lost；原first-credit不变 | supported |
| 原生保留存在真实兼容/必要撤回，质量保持 | v8原14、a065离线审计、完整历史和16/182 CER | supported |
| native joint降低drop能耗3.60%，但比双副本高84.94% | 已取回14件实际两板energy JSON，按正式四格/臂求和并核集合manifest SHA | supported |
| stage profiling或handoff收益 | 没有写入片段 | not claimed |

独立小wrapper用IEEEtran编译成功，精确命令为 `uv run --no-project --offline python -B C:/Users/LENOVO/.agents/skills/latex-paper-en/scripts/compile.py section_check.tex --recipe pdflatex-bibtex --outdir build`，exit 0。完整看了两页PDF渲染，表格无裁切，最终无未定义引用/引文、无overfull、无Type3字体。检查产物位于 `methods_draft_review_v1_compile/`；它不是整篇稿件已完成的编译声明。

Self-review：没有改其它sections/main/旧PDF；现有方法anchor不动；新引用仅使用已核 `vu2026streamcorrect`；实际Owner不兼容分支数与可见回撤数分开表述；native使用自身reconciler而不转贴core kernel/row/recovery保证；empty-buffer更新不挣实际处理信用；不使用profile或未实现结果。
