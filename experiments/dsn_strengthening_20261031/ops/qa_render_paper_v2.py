"""Read the compiled new release; automate checks and render every page."""
import json,pathlib,subprocess,sys
E=pathlib.Path(__file__).resolve().parents[1];R=E.parents[1]
P=R/'Paper_DSN/revisions/20261031_dsn2027_release_v2'
T=R/'experiments/dsn_manuscript_update_20261028'
output=P/'QA_AUTOMATED_v1';render=P/'QA_RENDERED_v1'
assert not output.exists() and not render.exists()
r=subprocess.run([sys.executable,'-B',str(T/'qa_dsn_release.py'),str(P),'--output',str(output)],capture_output=True)
(E/'PAPER_AUTOMATED_QA_v2.log').write_bytes(r.stdout+r.stderr)
assert r.returncode==0,(r.stdout+r.stderr).decode('utf8',errors='replace')[-3000:]
qa=json.loads((output/'QA.json').read_bytes());assert qa['gate']=='PASS_AUTOMATED_PENDING_ALL_PAGE_VISUAL_QA'
render.mkdir();subprocess.run(['pdftoppm','-scale-to','1800','-png',str(P/'main.pdf'),str(render/'page')],check=True)
print(json.dumps(dict(gate=qa['gate'],total_pages=qa['total_pages'],pagination=qa['checks']['pagination'],fonts=qa['checks']['fonts']['font_count'],pdf_sha256=qa['pdf_sha256'],source_files=qa['checks']['source_snapshot']['registered_files']),indent=2))
