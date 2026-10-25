from pathlib import Path
from collections import defaultdict
import csv,json,statistics
W=Path(__file__).resolve().parent/'precollection'
def rows(n):
 with (W/n).open(newline='',encoding='utf8') as f:return list(csv.DictReader(f))
g=defaultdict(list)
for r in rows('PROPOSAL_TAIL_CELLS.csv'):
 # Tail audit's method is the configured runtime method, not the side-arm label.
 label=r['cell'].split('-',3)[3].rsplit('-r',1)[0]
 g[r['arrival'],label].append(r)
for (arrival,method),rr in sorted(g.items()):
 if method not in ['fine','cost','service_cost','reserved_progress','inherit','causal','causal_joint','cost_joint']:continue
 assert len(rr)==3
 print(json.dumps({'type':'proposal','arrival':arrival,'label':method,'runs':len(rr),'caps':sum(int(x['proposal_caps']) for x in rr),
 'rows':sum(int(x['proposal_rows']) for x in rr),'median_rows':statistics.median(int(x['proposal_rows']) for x in rr),
 'median_batches':statistics.median(int(x['proposal_batches']) for x in rr),
 'median_lease_s':statistics.median(float(x['total_lease_s']) for x in rr),
 'median_cap_associated_lease_s':statistics.median(float(x['cap_associated_batch_lease_s']) for x in rr),
 'max_batch_s':max(float(x['max_batch_lease_s']) for x in rr)}))
g=defaultdict(list)
for r in rows('OPERATION_CALIBRATION.csv'):g[r['arrival'],r['label'],r['operation']].append(r)
for (arrival,method,op),rr in sorted(g.items()):
 if method not in ['fine','cost','causal','causal_joint','inherit','service_cost']:continue
 n=sum(int(x['actual_selected_batches']) for x in rr)
 pred=sum(float(x['predicted_first_lease_mean_s'])*int(x['actual_selected_batches']) for x in rr)/n
 act=sum(float(x['actual_full_lease_mean_s'])*int(x['actual_selected_batches']) for x in rr)/n
 print(json.dumps({'type':'selected_batch_calibration','arrival':arrival,'method':method,'op':op,'batches':n,
 'pred_mean':pred,'actual_mean':act,'relative_actual_minus_prediction':act/pred-1,
 'actual_fallback_rows':sum(float(x['actual_fallback_rows']) for x in rr),'predicted_fallback_rows':sum(float(x['predicted_fallback_rows']) for x in rr)}))
g=defaultdict(list)
for r in rows('SERVICE_PROMISES.csv'):g[r['cell'].split('-')[1],r['label']].append(r)
for (arrival,method),rr in sorted(g.items()):
 print(json.dumps({'type':'service_obligations','arrival':arrival,'method':method,'targets':len(rr),
 'deferrals_at_retirement_after_dispatch_reset':max(int(x['deferrals_at_retirement']) for x in rr),'promised':sum(bool(x['promised_finish']) for x in rr),
 'late':sum(x['actual_promise_late']=='True' for x in rr)}))
