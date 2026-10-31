"""Frozen two-client independent-EOS contract; no neural/runtime import."""
from __future__ import annotations
import math,threading
from common import need

CONTRACT='two_closed_loop_clients_two_distinct_EOS_offset2_v1'
A=('BAC009S0908W0369','BAC009S0913W0313')
B=('BAC009S0905W0246','BAC009S0916W0463')
ORDER=A+B
CLIENTS={'A':list(A),'B':list(B)}
OFFSET=2.0

def validate_contract(config):
    need(config['request_contract']==CONTRACT,'wrong two-client request contract')
    need(config['clients']==CLIENTS and config['client_first_offsets']=={'A':0.0,'B':OFFSET},'client partition/order/phase differs')
    need([s['source_id'] for s in config['settings']['sources']]==list(ORDER),'Owner sid order must be A0,A1,B0,B1')
    need(config['fault']=={'kind':'none'} and config['maximum_owner_restarts']==0,'opportunity experiment cannot recover/reload a model')
    need(config['settings']['corrector_dtype']=='float32' and config['settings']['max_ahead_frames']==32000,'original precision/ahead bound differs')
    need(config['maximum_service_seconds']==240,'fixed service bound differs')
    return {sid:(client,index) for client,order in CLIENTS.items() for index,sid in enumerate(order)}

def due_frontier(frames,request_origin,now):
    elapsed=max(0.,now-request_origin)
    return frames if elapsed>=frames/16000 else min(frames,int(elapsed/.5)*8000)

class TwoClients:
    """Supervisor-side releases; only actual canonical Consumer EOS advances a client."""
    def __init__(self,config,emit):
        self.partition=validate_contract(config);self.sources={s['source_id']:s for s in config['settings']['sources']};self.emit=emit
        self.lock=threading.RLock();self.origin=None;self.origins={};self.admitted={};self.completed={}
    def _admit(self,client,index,request_origin,observed):
        sid=CLIENTS[client][index];need(sid not in self.origins,'duplicate admission');previous=CLIENTS[client][index-1] if index else None
        need(previous is None or previous in self.completed,'client advanced before its own actual EOS')
        row=dict(kind='request_admitted',source_id=sid,client_id=client,client_request_index=index,request_origin_perf=request_origin,observed=observed,previous_source_id=previous,previous_complete_perf=self.completed[previous]['consumer_observed_perf'] if previous else None,planned_first_origin_perf=self.origin+(OFFSET if client=='B' else 0.) if index==0 else None)
        self.origins[sid]=request_origin;self.admitted[sid]=row;self.emit(row)
    def start(self,origin):
        with self.lock:
            need(self.origin is None and math.isfinite(origin),'duplicate/invalid origin');self.origin=origin;self._admit('A',0,origin,origin)
    def poll(self,now):
        with self.lock:
            if self.origin is not None and B[0] not in self.origins and now>=self.origin+OFFSET:self._admit('B',0,self.origin+OFFSET,now)
    def snapshot(self):
        with self.lock:return dict(self.origins)
    def complete(self,result,now):
        if not result.get('applied'):return
        row=result['row'];sid=row['source_id']
        with self.lock:
            if sid in self.completed or row['certified_frontier']!=self.sources[sid]['frames']:return
            need(row['kind']=='canonical' and sid in self.origins,'completion needs admitted actual canonical Consumer EOS')
            need(now>=row['observed']>=self.admitted[sid]['observed'],'completion clock precedes admission/Consumer')
            client,index=self.partition[sid]
            event=dict(kind='request_complete',source_id=sid,client_id=client,client_request_index=index,observed=row['observed'],request_origin_perf=self.origins[sid],EOS_frontier=self.sources[sid]['frames'],certified_frontier=row['certified_frontier'],consumer_observed_perf=row['observed'],completion_callback_perf=now)
            self.completed[sid]=event;self.emit(event)
            if index+1<len(CLIENTS[client]):self._admit(client,index+1,now,now)
