"""Actual installed aria2 CLI canary against a bounded localhost synthetic asset."""
import argparse,hashlib,http.server,json,pathlib,subprocess,threading
from transport import aria_command,aria_input,need,put
def main():
    p=argparse.ArgumentParser();p.add_argument('--aria2',required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    data=bytes(range(256))*1024
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            need(self.path=='/official_upstream_name.tar.gz','unexpected_canary_path')
            raw_range=self.headers.get('Range');start=0;end=len(data)-1
            if raw_range:
                left,right=raw_range.removeprefix('bytes=').split('-');start=int(left);end=int(right) if right else end
                need(0<=start<=end<len(data),'invalid_canary_range')
            self.send_response(206 if raw_range else 200);self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes')
            if raw_range:self.send_header('Content-Range',f'bytes {start}-{end}/{len(data)}')
            self.end_headers();self.wfile.write(data[start:end+1])
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    name='expected_different_name.multi.part';input_path=a.out/'INPUT.txt';input_path.write_text(aria_input([f'http://127.0.0.1:{server.server_port}/official_upstream_name.tar.gz'],a.out,name))
    command=aria_command(a.aria2,input_path,a.out,name)
    try:
        result=subprocess.run(command,capture_output=True,text=True,timeout=30)
        (a.out/'aria2.log').write_text(result.stdout+result.stderr);need(result.returncode==0,'real_aria2_canary_exit_failed')
        target=a.out/name;need(target.is_file() and target.read_bytes()==data,'real_aria2_input_file_target_or_bytes_wrong')
        need(not(a.out/'official_upstream_name.tar.gz').exists(),'real_aria2_ignored_per_entry_output_name')
        summary=dict(status='PASS_REAL_ARIA2_LOCALHOST_INPUT_ENTRY_OUTPUT_PATH_AND_BYTES',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
            exit_code=result.returncode,expected_target_path=str(target),upstream_basename_absent=True,external_network_calls=0,model_calls=0,GPU_calls=0)
        put(a.out/'GATE.json',summary);print(json.dumps(summary))
    finally:server.shutdown();server.server_close();thread.join(timeout=5)
if __name__=='__main__':main()
