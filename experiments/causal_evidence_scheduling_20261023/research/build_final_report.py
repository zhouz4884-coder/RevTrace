"""Evidence-grounded report and contribution matrix, no manuscript changes."""
from pathlib import Path
import collections,csv,hashlib,json,statistics
W=Path(__file__).resolve().parent;E=W/'collected/evidence';R=W/'reports';R.mkdir(exist_ok=False)
def read(p):return json.loads(p.read_text())
def csvread(p):return list(csv.DictReader(p.open()))
go=read(E/'FORMAL_RESULTS_v1/GO_NO_GO.json');assert go['formal_cells']==180
assert read(W/'INDEPENDENT_ACTUAL_RECOMPUTE.json')['status'].startswith('PASS_')
release=read(W/'INDEX_AND_RELEASE_REMOTE.json');idx=W/'RAW_EVIDENCE_INDEX_REMOTE.json'
assert hashlib.sha256(idx.read_bytes()).hexdigest()==release['index_sha256']
paper=read(W/'PAPER_BEFORE.json');changed=[r['path'] for r in paper if hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()!=r['sha256']]
assert not changed,'Concurrent paper bytes changed; do not claim unchanged'
groups=csvread(E/'FORMAL_RESULTS_v1/GROUPS.csv');comparisons=read(E/'FORMAL_RESULTS_v1/PAIRED_MIXED_COMPARISONS.json')
service=csvread(E/'formal_v1_independent_audit_final/SERVICE_CELLS.csv')
def comp(arrival,baseline):return next(x['effect'] for x in comparisons if x['pool']=='validation' and x['arrival']==arrival and x['baseline']==baseline)
def point(arrival,baseline,k):return comp(arrival,baseline)['paired_median'][k]*100
def ci(arrival,baseline,k):return [x*100 for x in comp(arrival,baseline)['paired_95_interval'][k]]
def pct(v):return f'{v:+.2f}%'
def ci_text(vals):return '['+', '.join(pct(v) for v in vals)+']'
labels={'fine':'Always Fine','strict':'Always Strict+Fallback','standard':'Standard Safe Async','readiness':'Birth/readiness gate','ready_any':'Readiness-only','cost_gate':'Cost threshold','cost':'Joint Cost-only','causal_only':'Rowwise causal','ces':'Full CES'}
text=['# CES 有界研究结项：实现完成，独立算法增量 NO-GO','',
'## 核心判断','',
'CES已经是可运行、保持原状态准入约束的证据调度实现，不是离线方案。'
'但正式数据没有满足“独立Mixed上优于最佳固定方法，并显著优于Cost-only/简单门控”的门槛。'
'本轮结论为 **NO-GO：不把当前CES v4提升为DSN论文的新C2主贡献**。'
'这不是对原C1/C2/C3的否定，也不是证明任何后续CES设计都不可能有效。','',
'## 实际完成范围','',
'- 证据基线23ba88c；SDK2bc71af；最终执行源码e0aeae1。独立源码分支和目录，旧冻结结果未覆盖。',
'- 33个真实双3090先导单元，180个正式fresh-process单元；9方法、开发16/独立16来源、同步/错峰、Clean/Mixed/High。',
'- Mixed各3次重复；Clean/High各1次仅作描述。全部fine2s、rho1、GPU0 FP16、GPU1 FP32、相同预算/Row SDK/WAL/Consumer。',
'- 最终243项本地运行时回归、234项Linux回归；另外6项CPU模式交错及3项统计实现测试；7个CPU模型Linux SIGKILL/WAL边界。后者不称GPU恢复。',
'- 180单元证书/WAL/D1/收据/租约/Consumer与指标审计通过；7,002个实际物理Worker批次、53,005个行输入完成CPU重建及重复核对。不是额外神经推理或跨布局数值等价证明。',
'- 预冻结源码、硬件、软件、音频顺序、故障计划及实际执行时钟顺序全矩阵核对通过。普通95%与同时99.84375%区间分开保留。',
'- 本机原始纯Python实现独立复算16个实际独立Mixed比较；Fine/Cost比较10,000次、其余1,000次，全部官方10,000次结果再算一致，容差1e-12。','',
'## 独立来源Mixed：每列为三个run的中位数','',
'Goodput单位audio-s/wall-s；时延秒；能耗GPU J/audio-s。表中列中位数不冒充配对变化率。',
'| 到达 | 方法 | Goodput | Display P99 | Commit P99 | GPU能耗 | WER% |',
'|---|---|---:|---:|---:|---:|---:|']
for arrival in ['sync','staggered']:
 for method in ['fine','strict','standard','readiness','ready_any','cost_gate','cost','causal_only','ces']:
  g=next(x for x in groups if x['pool']=='validation' and x['traffic']=='mixed' and x['arrival']==arrival and x['method']==method)
  text.append('| '+('同步' if arrival=='sync' else '错峰')+' | '+labels[method]+' | '+' | '.join(f'{float(g[k]):.3f}' for k in ['Audio_Goodput_2_8','display_P99','commit_P99','GPU_J_audio_s'])+f" | {float(g['WER'])*100:.4f} |")
text+=['', '## 配对效应与贡献门槛','',
f"- 同步CES/Fine：Goodput {pct(point('sync','fine','goodput'))}，普通95% {ci_text(ci('sync','fine','goodput'))}。这是局部正结果，不应删除。",
f"- 同步CES/联合Cost-only：{pct(point('sync','cost','goodput'))}，95% {ci_text(ci('sync','cost','goodput'))}；相对readiness-only及逐行因果也未建立稳定净优势。",
f"- 同步CES/Standard：{pct(point('sync','standard','goodput'))}，95% {ci_text(ci('sync','standard','goodput'))}。不能只选择Fine这一列称为成功。",
f"- 错峰CES/联合Cost-only：Goodput {pct(point('staggered','cost','goodput'))}，95% {ci_text(ci('staggered','cost','goodput'))}；能耗 {pct(point('staggered','cost','energy'))}，95% {ci_text(ci('staggered','cost','energy'))}。",
f"- 错峰CES/Fine：Goodput {pct(point('staggered','fine','goodput'))}，95% {ci_text(ci('staggered','fine','goodput'))}；能耗 {pct(point('staggered','fine','energy'))}。",
'- 独立Mixed中各比较的终态WER/CER配对差为0；这不是以降低识别质量换来的性能，也不代表逐Token/逐历史相同。',
'- 独立Mixed全部方法均0/3整run双P99通过；不能把部分前沿Goodput提升写成2s/8s容量达标。',
'- 实际认证Consumer时钟替代Owner安装时钟后，180个run的Goodput均未变化；两种时钟仍分别交付，不混称网络/客户端时延。','',
'## 从真实调用定位问题','',
'1. 错峰r0，CES验证37行/回退7行；联合Cost-only验证19行/回退2行。两者物理Worker批次均24，实际模型调用30对26；占用23.165s对20.761s。额外验证和Fallback没有变成免费工作。',
'2. 错峰r1/r2，CES模型调用30/24次、占用23.176/23.716s；联合Cost-only为24/26次、21.981/20.717s。CES显式等待为0；CPU规划加特征仅约0.030–0.070s/run，不能主要怪等待或CPU慢。',
'3. 错峰r0，CES obsolete Private为11，Fine为34，但CES服务指标更差：降低Private失效计数不自动提高合法Goodput。重叠行时间及关联物理调用包络不当作独占节省。',
'4. 同步独立Mixed中CES实际可验证行中位仅5行/135个目标，主要路径仍是独立Generation。可复用候选机会稀少，约束了额外调度空间。',
'5. 上述是成本/机会事实；“风险项高估Private保存价值”“单批次目标未捕获Parent解锁的后续关键路径”“成本/拒绝预测域偏移”是待检验解释，不冒充已证根因。全部选择与真实Batch误差表见formal_diagnosis_v1。','',
'## 本轮能支持什么，不能支持什么','',
'- 支持：在固定fine/rho下，可信证据可由完整验证+真实Fallback或独立FP32生成取得；选择与准入判据分离；实现通过原准入、WAL、实际输入及消费检查。',
'- 支持：存在负载依赖的局部收益以及明确退化反例；状态因果信息本身不等于正确的系统收益预测。',
'- 不支持：CES的因果特征或联合规划已获独立净收益；不支持独占Row-complete收益、普遍胜过强基线或已经增强DSN新算法竞争力。',
'- 原C1/C2/C3、V0/V1 NO-GO、Batch-dependent Input Realization及此前负结果不改。本轮未修改正文、标题、摘要或投稿材料。','',
'## 下一步的有界研究判断','',
'当前版本冻结，不再凭同一验证集改权重。若继续本主题，先只验证一个具体假设：'
'将“避免潜在Private失效”替换为“推进尚未合法消费前沿的边际关键路径”，同时对真实Fallback占用与后继Parent串行依赖计价，'
'并给联合Cost-only完全相同的成本/期限能力。先从现有日志量出真实空间，再决定是否新建下一轮GPU协议。'
'这不是已实现修复，不预设收益；如果仍等同简单门控，应停止新增算法主张而保留原架构贡献。','',
'## 封存与复核','',
f"8TB闭合索引{release['files']}个文件、{release['bytes']:,} bytes；SHA256 {release['index_sha256']}。",
f"426个已记录Worker身份均不再存活，5个GPU控制器原命令均结束；GPU空闲为封存时的实际观察。{len(paper)}个原稿文件重新哈希未改变。",
'完整原始日志/模型/音频留在指定8TB；本地有界证据1,629文件，含真实Canonical见证、WAL、指标、质量、输入重建和源码历史。']
(R/'RESEARCH_REPORT.zh.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
matrix=[
 {'claim_id':'C2-EXEC','claim':'Executable protected evidence routing at fixed rho1','evidence':'runtime e0aeae1;33 pilots;180 formal;CPU tests','decision':'SUPPORTED_IMPLEMENTATION','boundary':'Not independently validated algorithm superiority'},
 {'claim_id':'SAFE-REFINE','claim':'Evidence choice preserves original admission/WAL conditions','evidence':'11 byte-identical modules;180 replay audits;7 CPU process kills','decision':'SUPPORTED_CONDITIONAL','boundary':'Trusted worker/storage assumptions;not universal FP32/layout equality or new GPU recovery'},
 {'claim_id':'C2-CAUSAL','claim':'Causal information adds repeatable benefit over joint cost','evidence':'Independent Mixed vsCost:sync CI crosses0;staggered negative','decision':'NO_GO','boundary':'Do not package correlated metadata or shared executor benefit as novelty'},
 {'claim_id':'C2-JOINT','claim':'Joint planning adds repeatable benefit over full rowwise causal/simple gates','evidence':'Independent Mixed paired comparisons,GATES.csv','decision':'NO_GO','boundary':'Some point improvements,not established net independent increment'},
 {'claim_id':'C2-PERF','claim':'Broad same-quality system improvement over best fixed legal strategy','evidence':'Independent Mixed sync and stagger;equal terminal error counts','decision':'NO_GO_BROAD_CLAIM','boundary':'Sync Fine comparison positive95%;does not survive all stronger comparisons'},
 {'claim_id':'ORIGINAL-C1-C3','claim':'Original state-write boundary and durable recovery retained','evidence':'SOURCE_SCOPE_AUDIT;original evidence left unchanged','decision':'PRESERVED_NOT_NEW_CLAIM','boundary':'This study does not reject original C1/C2/C3 or guarantee DSN acceptance'}]
with (R/'CONTRIBUTION_EVIDENCE_MATRIX.csv').open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(matrix[0]));w.writeheader();w.writerows(matrix)
(R/'CONTRIBUTION_EVIDENCE_MATRIX.json').write_text(json.dumps(matrix,indent=2)+'\n')
decision=dict(go,final_independent_recompute='PASS',matrix_identity='PASS',all_processed_inputs_repeated='PASS',
 paper_unchanged_files=len(paper),resources_released='PASS',interpretation='Current CES v4 NO-GO for independent C2 algorithm increment,not proof all CES or original architecture fails')
(R/'FINAL_GO_NO_GO.json').write_text(json.dumps(decision,indent=2)+'\n')
(W/'PAPER_AFTER_AUDIT.json').write_text(json.dumps({'status':'PASS_PAPER_BYTES_UNCHANGED','files':len(paper),'changed':changed},indent=2)+'\n')
print(json.dumps({'report':str(R/'RESEARCH_REPORT.zh.md'),'formal_cells':180,'decision':decision['independent_new_C2_algorithm'],'paper_files_unchanged':len(paper)}))
