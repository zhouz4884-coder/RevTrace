# 本轮 release 工具衔接

本次只修改发布工具和合成控制，没有编译、打包、视觉批准实际新稿，也没有写 CURRENT 或推送 GitHub。

## 已改动

- `package_dsn_release.py` 新增可选 `--final-record`，保留历史默认 v1。记录路径和 ZIP 路径都在任何新输出前检查，不覆盖旧记录；最终记录以独占创建方式写入。
- `publish_progress.py` 新增同名参数。必须同时匹配所传 release 相对路径、PDF SHA、archive 相对路径、ZIP SHA 和字节数；旧稿的最终记录不能批准同 PDF 的另一份新 release 或另一 ZIP。
- `release_delivery_checks.py` 提供上述无副作用共享检查。
- 新通用 `record_final_visual_review.py` 只能在 root 实际查看全部最终 PNG 后使用。它要求显式页列表、实际完成审阅的声明和非空发现记录，绑定最终 PDF、自动 QA 字节 SHA、全部 PNG 的 SHA/尺寸。脚本自己不具备视觉判断能力。
- 历史 `record_final_visual_review_v1.py` 及旧 v1 QA/final record 保留。

## 验证

实际运行 `uv run --no-project --offline python -B -m unittest test_dsn_release_tools -v`：**25/25 PASS，0 skip**。原16项加9项版本衔接控制，覆盖旧目标不可覆盖、路径逃逸、同 PDF/不同 release、改名或改字节的 ZIP、变更 PDF、未做实际审阅声明、漏页/重页/错序、缺失/重复/坏 PNG，以及11页技术正文加新页参考文献。控制使用临时合成字节/PNG header，不能作为真实论文 PDF 或视觉 QA 结果。

三个新 CLI 的 `--help` 已正常解析。`prepare_dsn_release.py` 已能按字节闭包保存字面 `\input{...}` 的新表格和显式 `\includegraphics{...pdf}`；`qa_dsn_release.py` 默认允许11技术页，参考文献必须另起纯参考文献页。本轮无需放宽这两项工具。论文用 PDF 图，SVG/PNG 的实验交付另放 bounded evidence；不要把 SVG 作为 pdflatex 主稿依赖。

## root 后续命令

以下以新稿 `20261030_dsn2027_release_v1` 举例；实际路径和页数以最终自动 QA 为准。所有目标必须是新名字。

1. 仍通过原 `prepare_dsn_release.py --source ... --entry main.tex --destination ... --write --compile --skill-compile C:/Users/LENOVO/.agents/skills/latex-paper-en/scripts/compile.py` 制作干净稿，只调用该 skill 的编译入口。
2. 自动 QA：`qa_dsn_release.py Paper_DSN/revisions/20261030_dsn2027_release_v1 --output Paper_DSN/revisions/20261030_dsn2027_release_v1/QA_AUTOMATED_v1`。
3. `pdftoppm -scale-to 1800 -png <release>/main.pdf <release>/QA_RENDERED_v1/page` 后，root 用 view_image 实际查看全部页，完成图表、可读性、遮挡、参考文献页和正文匿名性检查。
4. 完成上一步之后才执行：

```text
uv run --no-project --offline python -B experiments/dsn_manuscript_update_20261028/record_final_visual_review.py --release Paper_DSN/revisions/20261030_dsn2027_release_v1 --automated-qa Paper_DSN/revisions/20261030_dsn2027_release_v1/QA_AUTOMATED_v1/QA.json --rendered-directory Paper_DSN/revisions/20261030_dsn2027_release_v1/QA_RENDERED_v1 --output experiments/dsn_manuscript_update_20261028/FINAL_ALL_PAGE_VISUAL_QA_20261030_v1.json --reviewed-pages 1,2,3,4,5,6,7,8,9,10,11,12 --root-reviewed-all-pages --notes "填写实际逐页发现；按实际最终页数调整显式列表"
```

5. 同一 source/PDF 打包并产生新记录：

```text
uv run --no-project --offline python -B experiments/dsn_manuscript_update_20261028/package_dsn_release.py --release Paper_DSN/revisions/20261030_dsn2027_release_v1 --automated-qa Paper_DSN/revisions/20261030_dsn2027_release_v1/QA_AUTOMATED_v1/QA.json --visual-review experiments/dsn_manuscript_update_20261028/FINAL_ALL_PAGE_VISUAL_QA_20261030_v1.json --archive Paper_DSN/RevTrace_DSN2027_20261030_v1.zip --final-record experiments/dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261030_v1.json
```

6. 更新 CURRENT / LATEST_RESEARCH 等本轮状态后，root 运行原 publisher，额外传入 `--final-record experiments/dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261030_v1.json`，其余 `--release/--archive` 必须与第5步一致。

root后续整合：publisher现在也将自身脚本作为普通bounded源文件逐字节归档，避免文档引用的最终CLI缺席交付包。它不在执行中改写自身；PROCESS/PUBLICATION记录仍分开处理，避免循环清单。实际提交前的Git blob核验同时覆盖发布脚本、共享helper、测试和本说明；这不是追加实验或改变神经结果。
