import pathlib,json,datetime
T=pathlib.Path(__file__).resolve().parents[1]
record=dict(experiment_id='REVTRACE-DSN-RXK-JOINT-20261028-v1',pid=1638632,start_ticks=500244107,command_sha256='b733a67185619f6a57fb60e033af94b90eba9cf37fdb18b088d1de5da00bceb2',
 launched_unix=1793252431.3026743,source_commit='f0a8e7bc5fbcb010de28e94ac5c9dbd6e67363cf',plan_sha256='d5da167c84b185dc38c2f5db345b7ba9bd0b501b087fcb06216e8f449a7a7f8e',planned_cells=24,
 remote_result='/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/results/revtrace/physical_retirement_20261028/dsn_joint_controller_v1',
 evidence='Actual launcher stdout returned successful detached handle; root conditional allocation after all asset/env/fullSHA IO gates passed')
(T/'ready_cpu_evidence_v6/CORE_JOINT_LAUNCH_HANDLE.json').write_text(json.dumps(record,indent=2))
p=T/'CURRENT_STATUS.json';s=json.loads(p.read_text());s.update(status='READY_NATIVE_WAITING_F0_JOINT24',heavy_io_active=False,all_own_remote_preparation_processes_finished=True,
 current_phase='f0R×K24 actually launched under root authorization; native14 waits next serialized GPU allocation',updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 independent_full_asset_sha_receipt='acquisition_monitor_v1/FINAL_FULL_SHA_ASSET_RECEIPT.json',independent_full_asset_sha_receipt_sha256='6637a4e2674368838597cdf021717b531caf874f382b0e4da39535bee0edd673',
 independent_io_finished_receipt='acquisition_monitor_v1/FINAL_IO_FINISHED_RECEIPT.json',independent_io_finished_receipt_sha256='06aa802af1a281c2719a3e97c3b87f0f96f561e1947c3ec828c66398e8e425c1',f0_joint24_handle=record)
p.write_text(json.dumps(s,indent=2))
