# DSN 干净发布包工具：已准备，尚未生成最终包

状态：`PREPARED_NOT_FINAL_RELEASE`，2026-10-29。根任务在 stage 最终决定后调用；本次没有生成真实 release 目录，没有新编译、上传或改变 `main.tex` / `CURRENT`。开发控制仅使用临时夹具；读取旧 PDF 仅检验 QA 帮助器对实际 IEEE 排版的适配，不替代最终编译或目视检查。

## 文件与行为

- [`prepare_dsn_release.py`](prepare_dsn_release.py)：默认只读规划。以指定 `core_draft.tex` 为入口，递归处理实际可达的 literal `input` / `include`、实际 `includegraphics`、实际 citation 和 bibliography。输出入口叫 `main.tex`，入口本身和所有章节/图片原始字节保持不变。未被入口引用的旧正文、图、表和附录不会被目录扫描带入。
- [`qa_dsn_release.py`](qa_dsn_release.py)：只使用已安装的 `pdfinfo`、`pdftotext`、`pdffonts`。检查技术页默认不超过11、参考文献另起净页、全部字体嵌入且没有 Type3、最终 log / blg / bbl 引用状态、被引用键实际进入 bbl、PDF 匿名元数据和打包文件 SHA。默认只输出 JSON；指定新 `--output` 目录才保存证据。
- [`test_dsn_release_tools.py`](test_dsn_release_tools.py)：16项有界控制，包括嵌套依赖/未引用文件排除、二进制图原字节、Bib 依赖/嵌套字段/安全移除、crossref/string 缺失与循环、动态/越界路径/隐藏宏、目标覆盖拒绝、复制期间源变化、字体/页边界/未定义引用/匿名元数据负例。没有模型或 TeX 编译。

所有工具只用 Python 标准库，没有安装额外库。编译动作只有 `--write --compile --skill-compile .../latex-paper-en/scripts/compile.py` 这一条显式路径，固定完整 `pdflatex-bibtex` recipe、关闭 shell escape；脚本不直接调用 TeX 引擎。该 recipe 在入口旁产生构建产物，因此 QA 默认读取 `main.pdf`、`main.log`、`main.blg`、`main.bbl`。不使用该 skill 在 explicit recipe 下未承诺的 outdir 行为。

## Bib 字节与依赖

保留实际引用键；如果某已选条目有明确 literal `crossref`，递归保留其必需父条目；只保留已选条目所需 `@string`。不推测缺失父项，不发明父项，不默默删掉 `crossref`。缺失、循环、非 literal crossref、xdata、active preamble、重复键/字段及未知字符串均停止并输出原因。当前 dry-run 无 crossref/string 额外依赖。

默认所选 Bib 条目字节保持不变。显式 `--strip-bib-metadata` 只移除已解析且边界明确的 `abstract` / `keywords` 字段；其他字段不重新序列化。`PACKAGING_PROVENANCE.json` 记录每个原输入文件和目标文件 SHA，以及每个已选条目的来源文件、原字节起止、原/新条目 SHA、所删字段和**原始条目完整字节的 base64**。因此精简后的包仍能恢复所选原条目，不必携带全部未引用文献。该来源记录不是实验执行 source commit，也不把旧 dirty checkout HEAD 当成执行身份。

## 根任务后续调用

工作目录为 `D:/VLA_QWEN/RevTrace`。先重新运行 dry-run，避免把下面的准备时快照当最终稿。

```powershell
python -B experiments/dsn_manuscript_update_20261028/prepare_dsn_release.py --source Paper_DSN/revisions/20261028_dsn2027_progress --entry core_draft.tex --strip-bib-metadata
```

stage 决定和正文合入完成后，根任务选择**尚不存在的新兄弟目录**；下面仅是以后调用的例子。本次没有执行该命令。父目录需已存在；已有目标一律拒绝，源目录的祖先/后代目标也拒绝。

```powershell
python -B experiments/dsn_manuscript_update_20261028/prepare_dsn_release.py --source Paper_DSN/revisions/20261028_dsn2027_progress --entry core_draft.tex --destination Paper_DSN/revisions/20261029_dsn2027_release_v1 --strip-bib-metadata --write --compile --skill-compile C:/Users/LENOVO/.agents/skills/latex-paper-en/scripts/compile.py
python -B experiments/dsn_manuscript_update_20261028/qa_dsn_release.py Paper_DSN/revisions/20261029_dsn2027_release_v1 --forbid-token LENOVO --forbid-token zhouz4884-coder --output Paper_DSN/revisions/20261029_dsn2027_release_v1/QA_AUTOMATED_v1
```

打包时重新核对输入快照，复制后核对全部目标 SHA；源在期间改变时保留带 `PACKAGING_FAILED.txt` 的可检查失败目录，不能当发布包，后续用新版本目录重试。编译 returncode / skill SHA / Python stdout-stderr 单独记录；编译非零或 QA 非 PASS 不构成完成发布。没有自动修改旧稿、入口指针或上传动作。

QA 成功返回 `PASS_AUTOMATED_PENDING_ALL_PAGE_VISUAL_QA`。根任务仍须打开最终 PDF 的**所有页**确认正文/图表可读、没有裁切覆盖、参考页只有参考文献，以及正文/链接/最终投稿系统元数据的匿名性。自动检查 PDF metadata 不是对全文匿名性的证明。

源包的上传白名单是 `PACKAGING_PROVENANCE.json` 的 `files[].target`，加该来源记录及最终 `main.pdf`。编译产生的 aux/log/synctex、`COMPILE_STDOUT.txt` 和内部 QA 证据用于本地核验，不属于匿名上传源包；它们可能记录本机 TeX 路径。最终打 zip 应按此白名单取文件，不按整个工作目录扫描。本工具当前准备阶段不创建最终 zip。

## 静态语法范围与停止条件

这是本项目当前 literal TeX 的闭包工具，不是通用 TeX 解释器。动态路径、用户自定义宏/条件分支、import 家族、graphicspath、更改 graphics extension、verbatim/code 环境、本地 cls/sty/bst、外部文献别名等需要显式扩展后重测；遇到已识别的不支持形式会停止，不通过运行任意宏来猜依赖。系统 IEEEtran 和已声明宏包记录为外部 TeX 依赖，沿用本机已有安装。

参考页判断按 PDF 实际文本结构处理 IEEE small caps 的 `R EFERENCES` 及 Windows CRLF，若分隔不明确返回 INDETERMINATE。参考文献之后的任意普通正文，单靠文本规则不能穷尽识别，最终仍由全页目视确认。字体行无法解析、日志/构建文献缺失、匿名 metadata 无法解析也不能自动通过。

## 本次准备验证

- 当前实际源的只读闭包：10个 TeX（入口+9个实际章节文件）、3张 PDF、3份 Bib，共16个文件；17个引用键。选择去除 metadata 时4个已选条目发生字段精简。该数量是准备时快照，后续正文变化应由脚本重新计算。
- 16项临时夹具控制通过；实际最终发布/skill 编译路径**尚未运行**。
- 旧已编译 `core_draft.pdf` 只读 smoke：SHA `a855cdebc230c7de7c278d739ecbf15f8190c90f69416bdbc0323977c1d0e6ae`，读取前后相同；10总页=9技术页+1参考页，23字体均嵌入、无Type3，现有 log/blg/bbl 和匿名 metadata 检查通过。该 PDF 早于根任务后来新增的模型/数据引用，不能证明当前17引用键均已编译，更不能替代未来最终包 QA。
