"""Trusted CPU export of native tokenizer code and exact parser dependencies.

No model weights are loaded and no neural generation is performed. The exported
program is not a text/output cache. A separate fresh-process conformance test is
required before this program may be used for serving recovery.
"""
from pathlib import Path
import argparse,hashlib,importlib.metadata,inspect,json,os,platform,subprocess,sys,time,traceback
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from revtrace.startup_overlap import load_native_qwen_context,verify_prefrozen_renderer,package_root
from revtrace.light_render import file_sha,canonical_sha,parser_slice,FrozenTokenizer,FIXED_OPERATIONS


def put(p,x):
    with p.open('x',encoding='utf8') as f:json.dump(x,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',type=Path,required=True);p.add_argument('--native-descriptor',type=Path,required=True)
    p.add_argument('--native-descriptor-sha256',required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--result',type=Path,required=True)
    p.add_argument('--source-root',type=Path,required=True);p.add_argument('--source-manifest',type=Path,required=True);a=p.parse_args()
    assert not a.result.exists() and not a.bundle.exists();source=json.loads(a.source_manifest.read_text())
    assert subprocess.check_output(['git','-C',str(a.source_root),'rev-parse','HEAD'],text=True).strip()==source['code_commit']
    assert not subprocess.check_output(['git','-C',str(a.source_root),'status','--porcelain'],text=True).strip()
    for r in source['files']:assert file_sha(a.source_root/r['path'])==r['sha256']
    a.result.mkdir(parents=True);a.bundle.mkdir(parents=True)
    env=dict(python=sys.version,platform=platform.platform(),packages={n:importlib.metadata.version(n) for n in ['torch','transformers','qwen-asr','tokenizers']})
    put(a.result/'ENVIRONMENT.json',env)
    put(a.result/'FREEZE.json',dict(experiment_id='REVTRACE-NATIVE-RENDER-PROGRAM-PREPARATION-20261028',source_commit=source['code_commit'],source_manifest_sha256=file_sha(a.source_manifest),native_descriptor_sha256=a.native_descriptor_sha256,environment_sha256=file_sha(a.result/'ENVIRONMENT.json'),model=str(a.model),argv=sys.argv[1:],bundle=str(a.bundle),raw_result_location=str(a.result),aggregate_summary_location=str(a.result/'RESULT.json'),gate_decision_location=str(a.result/'GATE.json'),GPU_inference_calls=0))
    started=time.perf_counter()
    try:
        native_contract=verify_prefrozen_renderer(a.model,a.native_descriptor,expected_descriptor_sha256=a.native_descriptor_sha256)
        context=load_native_qwen_context(a.model);assert context.contract==native_contract
        tok=context.processor.tokenizer
        assert getattr(tok,'clean_up_tokenization_spaces',None) is False
        assert getattr(tok,'split_special_tokens',False) is False
        default_empty=tok.encode('');backend=tok.backend_tokenizer;program=backend.to_str();structure=json.loads(program)
        assert structure.get('padding') is None and structure.get('truncation') is None
        assert structure['model']['type']=='BPE' and structure['model'].get('dropout') is None
        flag=backend.encode_special_tokens;assert type(flag) is bool
        program_path=a.bundle/'native_tokenizer_program.json';program_path.write_text(program,encoding='utf8')
        # Native encoding has established its actual default state. Do not
        # substitute a hand-rebuilt vocab or reconfigure the reference tokenizer.
        from tokenizers import Tokenizer
        clone=Tokenizer.from_str(program);FrozenTokenizer(clone,encode_special_tokens=flag)
        assert canonical_sha(json.loads(clone.to_str()))==canonical_sha(structure)
        root=package_root();native=json.loads(a.native_descriptor.read_text())
        parse,ast_sha=parser_slice(root/'inference/utils.py',native['package_files']['inference/utils.py'])
        assert hashlib.sha256(inspect.getsource(parse).encode()).hexdigest()==native_contract['parse_source_sha256']
        from transformers import PreTrainedTokenizerFast,PreTrainedTokenizerBase
        import tokenizers,unicodedata
        dependencies={Path(inspect.getfile(type(tok))),Path(inspect.getfile(PreTrainedTokenizerFast)),Path(inspect.getfile(PreTrainedTokenizerBase))}
        tokenroot=Path(tokenizers.__file__).resolve().parent
        dependencies.update(tokenroot.rglob('*.so'));dependencies.add(Path(tokenizers.__file__))
        d=dict(schema='qwen-equivalent-render-program-v1',native_reference_contract=native_contract,
            native_descriptor_sha256=a.native_descriptor_sha256,source_preparation_commit=source['code_commit'],
            python_version=platform.python_version(),unicode_version=unicodedata.unidata_version,
            packages=env['packages'],model_assets=native_contract['assets'],qwen_package_python=native['package_files'],
            dependency_files=[dict(path=str(f.resolve()),sha256=file_sha(f)) for f in sorted(dependencies)],
            program_file=program_path.name,program_sha256=file_sha(program_path),native_default_backend_sha256=canonical_sha(structure),
            encode_special_tokens=flag,default_empty_encoded_ids=default_empty,
            fixed_operations=FIXED_OPERATIONS,
            native_all_special_ids=tok.all_special_ids,vocab_size=tok.vocab_size,
            parser_ast_sha256=ast_sha,parser_functions=['normalize_language_name','detect_and_fix_repetitions','parse_asr_output'],
            light_module_sha256=file_sha(a.source_root/'runtime/src/revtrace/light_render.py'),
            scope='native tokenizer PROGRAM export, not a transcript cache; fresh conformance and explicit serving contract still required')
        put(a.bundle/'descriptor.json',d)
        result=dict(status='PREPARED_FROM_ACTUAL_NATIVE_PROCESSOR',descriptor_sha256=file_sha(a.bundle/'descriptor.json'),bundle=str(a.bundle),program_bytes=program_path.stat().st_size,default_empty_ids=default_empty,preparation_seconds=time.perf_counter()-started,model_weight_loads=0,GPU_inference_calls=0,serving_use_permitted=False)
        put(a.result/'RESULT.json',result);put(a.result/'GATE.json',dict(gate='PROGRAM_PREPARED_NOT_SERVING_EQUIVALENCE',**result));print(json.dumps(result),flush=True)
    except BaseException:
        put(a.result/'STOP.json',dict(error=traceback.format_exc(),model_weight_loads=0,GPU_inference_calls=0));raise


if __name__=='__main__':main()
