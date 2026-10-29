# 最终 GitHub 发布清单与只读核验规格 v1

2026-10-29。仅本地读取 `publish_progress.py`、`prepare_dsn_release.py`、`qa_dsn_release.py` 和当前可达稿件，准备最终白名单。不改 publisher、正文、Git、远端或模型执行。最终 release 目录在本轮读取时尚不存在；下列最终门尚不能标为通过。

## 1. 当前状态与发布缺口

当前 `publish_progress.py` 只收集指定的 `experiments/...` 家族及 `experiments/LATEST_RESEARCH.json`，**不会发布 `Paper_DSN`**。最终需要显式追加 clean release、入口指针和一个固定 ZIP；不要把 `Paper_DSN` 或 release 目录直接递归加入现有 families。

`Paper_DSN/CURRENT.md` 仍指向 20261008 旧稿，包含旧的 Windows 绝对路径和旧私有快照身份。root 应在最终 QA 完成后将其换成当前 release 的仓内相对链接、最终 PDF/ZIP SHA 和实际页数。CURRENT 是公开仓库导航，不进入匿名源 ZIP。

`prepare_dsn_release.py` 的来源记录只绑定实际源文件字节和闭包，不替代实验执行源码 commit。不要因为发布包或 GitHub archive HEAD 改变，给已有实验改写 source commit。

## 2. 精确白名单

固定根：

```text
R = repository root
D = R/Paper_DSN/revisions/20261029_dsn2027_release_v1
M = D/PACKAGING_PROVENANCE.json
Z = D/RevTrace_DSN2027_anonymous_source_v1.zip   # 建议固定该唯一名字
```

### 匿名源 ZIP 的完整集合 A

```text
A = {D / row.target for row in M.files}
    union {D/PACKAGING_PROVENANCE.json, D/main.pdf}
```

ZIP 内路径必须是相对于 D 的 POSIX 路径，使解压后直接得到 `main.tex`、`main.pdf`、`sections/...`、`figures/...`、Bib 和来源记录。不得加绝对路径，不应保留本机的 `Paper_DSN/revisions/...` 父层；ZIP 自己不进入自身。

`M.files[].target` 是唯一依赖白名单，不用扩展名 glob 推断实际文件。当前工作稿只读闭包快照为 **18 个文件**：

```text
main.tex
sections/01_progress_introduction.tex
sections/02_contract.tex
sections/03_continuation.tex
sections/03_native_extension.tex
sections/04_protocol.tex
sections/05_evaluation_core.tex
sections/05_execution_only.tex
sections/05_native_retention.tex
sections/06_progress_related.tex
sections/07_progress_discussion.tex
sections/08_progress_conclusion.tex
figures/coordination_protocol.pdf
figures/service_region.pdf
figures/timely_full_interval_case.pdf
refs.bib
formal_refs.bib
coordination_refs.bib
```

这是当前实际可达状态，不是应硬编码的最终数量。root 后续改图/引用后，最终集合只以新生成且通过字节核验的 M 为准。既有 16 文件的准备说明已过时，不能拿它拦截合法新增章节或代替重算。

### GitHub 最终额外集合 H

```text
H = A union {Z, R/Paper_DSN/CURRENT.md}
```

若为了 byte-preserved Git 传输新增 `.gitattributes`，只允许显式的 `D/.gitattributes`（内容 `* -text`）作为 H 的另一个固定条目；它不进入 A。`CURRENT.md` 也应经过当前 publisher 的逐 blob 字节核验，不能仅依赖 autocrlf 设置。现有 Git index SHA 检查必须保留。

当前阶段的 QA/模型/配置等 bounded 研究证据仍由现有 experiment 家族发布。它们与 H 是两个集合；不能用“实验目录本来可上传”推导“匿名源 ZIP 可以装入实验目录”。

## 3. 明确排除项

即使它们实际存在于 D，也不得进入 A：

* 构建中间件：`*.aux`、`*.log`、`*.blg`、`*.bbl`、`*.out`、`*.toc`、`*.fls`、`*.fdb_latexmk`、`*.synctex*`。
* `COMPILE_RECORD.json`、`COMPILE_STDOUT.txt`、`PACKAGING_FAILED.txt`、`QA_*`、逐页 PNG、`pdfinfo/pdffonts/pages` 文本、XMP 导出与其他内部检查文件。
* `CURRENT.md`、旧 `main.pdf`、旧工作稿、未被实际引用的章节/图表、旧 supplement、任何实验目录、source bundle、仓库 `.git` 或 worktree 管理文件。
* 模型与数据：权重、LoRA、tokenizer assets、HF/ModelScope cache、环境、音频、原始 ASR packet、原始 tensor、原始大日志或 powersample bank。
* 凭据：`.env*`、SSH key、known_hosts/credential helper、登录 cache、cookies、PAT/HF token、密码、私有服务端点。发布不需要这些材料。

QA 和编译日志必须保留在本地作为 final gate 依据；不打匿名 ZIP不等于删掉验证记录。若需把最终 QA 结论同步 GitHub，可在实验家族中放只含 gate、文件 SHA、页数、字体结论和逐页检查状态的精简 JSON；不要把本机路径或完整编译 stdout 塞进匿名包。

## 4. publisher 的最小新增逻辑规格（给 root 实现，不在本任务修改）

在现有 `files` 收集完成、开始复制之前追加 H。只使用一次解析的最终 M，按下面次序 fail closed：

1. D、M、`main.pdf`、Z 与最终 CURRENT 必须真实存在；若有 `PACKAGING_FAILED.txt`，拒绝发布。
2. M schema 必须为 `revtrace-dsn-release-v1`，`entry_target == main.tex`，`files` 非空且 `target` 唯一。
3. 每个 target 是非空、规范化的相对 POSIX 名字：拒绝反斜线、绝对路径、盘符、空路径段、`.`、`..`、NUL；`(D/target).resolve()` 必须仍在 D 内。拒绝符号链接及任何解析后越界的 junction。
4. 对每个 `files` 行重新核 `target_sha256` 和 `bytes`。当前 M 的 gate 写的是打包时未编译状态，这是历史来源状态；最终可交付由独立编译/QA gate 证明，不应把 M 的历史 gate 偷改成实验或完整 QA PASS。
5. `main.pdf`、M、Z 不在原 `files` 哈希中，应在本次 process manifest 另记实际 bytes/SHA；读取后、复制前以及复制后各核字节。PDF 必须和最终 QA 记录的 SHA 完全一致。
6. Z 必须通过第 5 节的逐 entry 等集合核验。ZIP 与解压 payload 的存在本身不证明它使用了新 PDF。
7. 对 H 的全部文件保留当前 publisher 的 `<20,000,000 bytes` 单文件上限和 SHA/blob 校验。超限先定位实际大项，不为图方便把整个源树放宽。
8. H 只追加清楚列明的文件，不递归扫 D。禁止 `git add .`、`git add -A` 或临时 reset/pull legacy checkout。沿用现有 clean delivery worktree、普通 push、remote main 对齐与逐文件 blob 校验。

现有 publisher 在收集时会为 experiment 家族创建 `.gitattributes`；对 D 不要因套用 family 扫描而自动带入其他构建文件。需要 transport 属性时只显式增加前述固定属性文件。

## 5. ZIP 的只读等集合核验

ZIP 创建后，不必解压到另一个目录，直接用 `zipfile` 读取并验证：

```python
expected = {row['target'] for row in M['files']} | {
    'PACKAGING_PROVENANCE.json', 'main.pdf'
}
with ZipFile(Z) as archive:
    infos = archive.infolist()
    assert len(infos) == len(expected)             # 排除重复 entry
    assert {i.filename for i in infos} == expected # 没有多装/漏装
    for info in infos:
        assert not info.is_dir()
        assert not info.flag_bits & 1             # 不使用加密包隐藏检查对象
        assert not is_unsafe_or_symlink(info)     # 相对路径、无越界、无链接
        disk = D / info.filename
        assert info.file_size == disk.stat().st_size
        assert sha256(archive.read(info)).hexdigest() == sha256(disk.read_bytes()).hexdigest()
    assert archive.testzip() is None
```

其中 `is_unsafe_or_symlink` 检查与第 4 节 target 规则一致，再拒绝 UNIX symlink mode `((external_attr >> 16) & 0o170000) == 0o120000`。ZIP comment/extra 不应携带用户名、绝对路径或凭据。创建 ZIP 时使用显式 arcname，不按整个文件夹打包。

## 6. 匿名内容检查：要包括 PDF、链接和来源记录内的编码原条目

`qa_dsn_release.py --forbid-token` **只扫描 PDF metadata**。它不证明正文、注释、PDF 链接或 `.bib` 匿名，最终需要下面的补充只读检查。

扫描对象：

1. A 中所有 TeX/Bib 和 M 的可读字符串。
2. `M.bibliography_entries[].original_entry_bytes_base64` 解码后的原始 Bib 字节。packager 去除了 rendered Bib 的 abstract/keywords，但为了可恢复性保留编码原条目，所以只扫精简后的 Bib 不够。
3. `main.pdf` 与可达图 PDF 的 metadata/XMP、实际文字、annotation URI/链接；不要只看 PDF Author 字段。
4. Z 每个解压 entry 的同一套检查，而不是仅检查磁盘版本。

需无命中的内容包括本机用户名/账号、自有公开仓库定位、Windows/Unix 绝对本机路径、SSH/私有端点和 credential material。第三方原论文/官方源码的正常引用链接应保留；**不要为了匿名把所有 GitHub 或 https 文献链接删掉**。

本轮使用的重点 token 是 `LENOVO`、`zhouz4884-coder`、自仓 RevTrace URL、本项目两个已知私有/远程端点，以及私钥/HF/GitHub credential 的格式；只记录命中类别和文件名，不打印疑似秘密正文。Windows 盘符正则要防止将 `https://` 末尾的 `s:/` 误报为盘符，例如使用 `(?<![A-Za-z0-9])[A-Za-z]:[\\/]`。

匿名包无需自有 GitHub URL、机器用户名或绝对工作区路径。CURRENT 可以给仓内相对链接；论文中保留系统名 RevTrace 与正常的第三方文献，不自行创建新的匿名 mirror 或执行投稿。

## 7. 本轮只读检查的实际结果

对当时工作稿重新运行 packager 的 `Closure(...).plan()`，未写 release：

* **18 个可达文件，19 个被引 key，19 个 provenance 原 Bib 条目**。
* 对可达 TeX、精简 Bib、编码原条目、三张图 PDF 的 metadata/文字/URI，以及当时已编译 `core_draft.pdf` 的 metadata/文字/URI，未发现上述用户名、账号、自仓链接、本机绝对路径、私有端点或 credential-format 命中。
* 当时 `core_draft.pdf` 是 **11 总页**，Author/Subject 均为空。此处只确认检查对象的状态，不将它等同于尚未创建的最终 `main.pdf`，也不替代最终页数/字体/目视 QA。
* 最终 release 尚未生成；M/最终 main.pdf/ZIP/更新后的 CURRENT/最终 GitHub commit **均未在本任务验证或创建**。

这次检查使用已安装 PyMuPDF 与标准库，无下载、无 TeX 编译、无模型运行。辅助代码只在内存运行，没有生成检查器文件或修改 publisher。

## 8. 最终执行顺序与完成证据

1. 正文和全部新来源结果合入完毕，停止改源；packager 重新解析闭包，写入全新的 D。
2. 通过 latex-paper-en skill 的固定编译入口编译 D/main.tex；执行 `qa_dsn_release.py` 并逐页目视所有页。自动 gate 仅为 `PASS_AUTOMATED_PENDING_ALL_PAGE_VISUAL_QA`，目视完成前不得写最终完成。
3. 按 A 做匿名内容检查；按 A 创建固定 Z，并通过 ZIP 等集合/逐文件 SHA 检查。
4. 更新 CURRENT，使用仓内相对路径和实际最终 hash；按 H 加入 publisher，不递归加入 D。
5. 复核全部 source/figure/Bib/PDF/ZIP 字节，普通 push。记录 archive commit、tree、remote main 确认、最终 PDF SHA、ZIP SHA、M SHA 和 bounded snapshot manifest。
6. 再从 delivery worktree 及远端所指 commit 核对同一 payload；receipt 中区分 GitHub evidence archive 身份与各实验实际 execution source 身份。

最终用户报告可以给 PDF、匿名源 ZIP、GitHub commit 与主要实测结果。不要把“提交到了 GitHub”替代“实验完成/源包可编译/最终 PDF 已逐页检查”，也不要称已执行 DSN 投稿。
