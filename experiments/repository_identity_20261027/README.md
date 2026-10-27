# 开工前源码身份修复：REPO-IDENTITY-20261027

## 结论与入口

本次是本地 Git 家务与 CPU 前置核验，不是新增 GPU 实验，也未修改论文。

| 用途 | 本地路径（相对于项目根） | 身份 |
| --- | --- | --- |
| 原有未提交现场，保留不用作新实验入口 | `.` | `codex/tc-adaptation`，`7372133ecf9ff2b7930fb799b56e1fbdd1d80f3f` |
| 最新正式 GitHub 证据归档 | `.execution/archive_main` | `main`，`84c41fca5b2576d121e67b9273b2b72ea2b53b7c` |
| 最新 LP1 冻结源码的干净开发起点 | `.execution/lp1_runtime` | `codex/lp1-next`，`7c176556592c2a4fad436056b8b96be52cac9ea4` |

这三个身份不能互相替代。原目录仍显示 `7372133` 是有意保护脏工作树，
不是 fetch 失败。现在本地 `main` 与 `origin/main` 均已快进至 `84c41fc`，
`62b1003c2db6766118244c78fa95e2c3fac42c16` 已可在同一 Git 对象库中解析。
没有对原目录执行 pull、merge、reset、stash 或提交用户已有修改。

可直接核查：

```powershell
git -C D:\VLA_QWEN\RevTrace\.execution\archive_main rev-parse HEAD
git -C D:\VLA_QWEN\RevTrace cat-file -t 62b1003c2db6766118244c78fa95e2c3fac42c16
python -B D:\VLA_QWEN\RevTrace\experiments\repository_identity_20261027\preflight.py
```

## 实验源码不是归档 HEAD

已逐个核验 LP1 的 19 份 bundle SHA256 与 bundle 声明的完整 commit，
导入对象并固定 `refs/archive/revtrace/lp1/*`；另导入 CK5 v6 基线。
完整映射见 `SETUP.json`，不是只记录短 hash。

| 历史执行范围 | 实际源码 commit |
| --- | --- |
| CK5 v6 基线 | `b8aa802c687256d3801612dc8bee585ee849ddea` |
| X operator GPU | `f33acdb4475be6c43e3b72dba88e21bb1ad4e940` |
| X service GPU | `4d23d23569cb39db231ed5748f2604c26e663eec` |
| M 主矩阵 GPU | `e83983004b22f0e7b6081157260f9954f4cf2ff7` |
| M content-only GPU | `ea9fc8999076aaf773e7618e170953fa1ccd1280` |
| 最终 CPU 回归源码 | `7c176556592c2a4fad436056b8b96be52cac9ea4` |

最终源码的 176 个跟踪文件逐字节匹配正式归档内的
`final_source_v2_SOURCE.json`，其 SHA256 为
`e4f72dae0920594911d7ef8199c71f91601263f05c1a0e90d78abfbb4b3a4f77`。
两个新工作树均干净，使用各自 `core.autocrlf=false`，不更改原目录的换行设置。
最终源码是开发起点，不自动等于所有历史 GPU 实验所用版本。

## 核验结果与 AGENTS 第 2 条

- 原 46 个已修改跟踪文件的内容 SHA256 保持不变，暂存区内容不变。
  唯一有意新增的跟踪文件修改是根目录 AGENTS 的源码身份前置门槛。
- 从新源码工作树执行五个指定测试模块：32/32 CPU 回归通过。
- 新身份门槛的 CPU 测试：6/6 通过，覆盖错误 HEAD、字节变化、脏目录、
  缺失实验元数据、冻结输入哈希错误及错误原始结果磁盘。
- Git 非浅仓库；connectivity 检查通过。历史 dangling 对象保留，未执行 GC/删除。
- 没有启动 GPU、改变实验数值、改稿或推送远端。

第 2 条没有被豁免：本次解除的是“本地无法解析证据与执行源码”的阻塞，
不等于已追溯审计整个项目每一个旧实验的全部元数据。
新实验依然必须先冻结实际修改后的源码、config、环境与原始结果位置。

`preflight.py --run-record <record.json>` 可额外检查启动记录的必需字段和
config/environment 文件哈希。未提供记录时只报告 `SOURCE_IDENTITY_PASS`，
不会宣称实验可启动或已完成。远端实际部署副本/环境/资源核验仍需单独进行。
summary/gate 的目标路径在启动前登记，完成后才允许填充真实结论；不得预填 PASS。

执行轨迹：`BEFORE.json` → `SETUP.json` → `SOURCE_PREFLIGHT.json` →
`RUNTIME_CPU.xml` / `GATE_TESTS_v2.xml` → `AFTER.json` → `VERIFICATION.json`。
`FSCK.txt` 保留原始 connectivity 输出。上述结果不支持任何新的性能主张。
