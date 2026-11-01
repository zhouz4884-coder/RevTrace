"""One ZIP-only extraction and skill-only cold compilation of final v9."""
from pathlib import Path,PurePosixPath
import datetime,hashlib,importlib.util,json,os,re,stat,subprocess,traceback,zipfile

R=Path(__file__).resolve().parents[2]
E=Path(__file__).resolve().parent
REL=R/'Paper_DSN/revisions/20261101_dsn2027_release_v9'
ZIP=REL/'RevTrace_DSN2027_anonymous_source_v9.zip'
FINAL=R/'experiments/dsn_manuscript_update_20261028/FINAL_RELEASE_RECORD_20261101_v9.json'
CURRENT=R/'experiments/repository_identity_20261027/CURRENT.json'
COLD=E/'ANONYMOUS_COLD_BUILD'
LOGS=E/'COLD_BUILD_LOGS'
OUT=E/'COLD_BUILD_QA.json'
SKILL=Path(r'C:\Users\LENOVO\.agents\skills\latex-paper-en\SKILL.md')
COMPILE=SKILL.parent/'scripts/compile.py'
QA=R/'experiments/dsn_manuscript_update_20261028/qa_dsn_release.py'

def sha(data):return hashlib.sha256(data).hexdigest()
def rec(path):return dict(bytes=path.stat().st_size,sha256=sha(path.read_bytes()))
def dump(path,data):
    with path.open('x',encoding='utf8',newline='\n') as f:json.dump(data,f,indent=2);f.write('\n')
def run(argv,name,cwd=None):
    p=subprocess.run(argv,cwd=cwd,capture_output=True,timeout=600,
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    assert len(p.stdout)+len(p.stderr)<=1024*1024, 'Bounded log exceeds 1MiB'
    (LOGS/(name+'.stdout')).write_bytes(p.stdout)
    (LOGS/(name+'.stderr')).write_bytes(p.stderr)
    assert p.returncode==0, name+' exited '+str(p.returncode)
    return p

def main():
    report=dict(gate='IN_PROGRESS',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        new_model_calls=0,SSH_calls=0,CURRENT_modified=False,original_manuscript_modified=False,
        archive=str(ZIP),release=str(REL),final_record=str(FINAL),cold_directory=str(COLD),
        extraction_count=0,compilation_count=0,shell_escape=False)
    before={}
    try:
        assert not COLD.exists() and not LOGS.exists() and not OUT.exists(), 'Exclusive output already exists'
        final=json.loads(FINAL.read_bytes())
        assert final['gate']=='PASS_COMPLETE_ALL_PAGE_VISUAL_AND_AUTOMATED_QA'
        rows=final['source_package_files'];expected={row['path']:row for row in rows}
        assert len(expected)==len(rows)==28
        assert rec(ZIP)==dict(bytes=final['archive_bytes'],sha256=final['archive_sha256'])
        assert final['pdf_sha256']=='cf3cd3556cf7637f970d3d18870beb71447c51d34eb6417c4e5ab30f41d12114'
        assert final['archive_sha256']=='5643e96542ed2a0d8b52ac410149e90e147c62b57841234d86188c8e68535f8b'
        protected=[ZIP,FINAL,CURRENT]+[REL/name for name in sorted(expected)]
        before={str(p):rec(p) for p in protected}
        for name,row in expected.items():
            assert (REL/name).resolve().is_relative_to(REL.resolve()) and not (REL/name).is_symlink()
            assert rec(REL/name)==dict(bytes=row['bytes'],sha256=row['sha256'])
        with zipfile.ZipFile(ZIP) as z:
            infos=z.infolist();names=[i.filename for i in infos]
            assert len(names)==len(expected) and set(names)==set(expected)
            assert len(set(x.casefold() for x in names))==len(names) and z.testzip() is None
            assert sum(i.file_size for i in infos)<20*1024*1024
            for i in infos:
                p=PurePosixPath(i.filename)
                assert not p.is_absolute() and '..' not in p.parts and '\\' not in i.filename and ':' not in i.filename
                assert not i.is_dir() and not stat.S_ISLNK(i.external_attr>>16) and not(i.flag_bits&1)
                raw=z.read(i);row=expected[i.filename]
                assert len(raw)==row['bytes'] and sha(raw)==row['sha256']
            provenance=json.loads(z.read('PACKAGING_PROVENANCE.json'))
            assert {x['target'] for x in provenance['files']}|{'main.pdf','PACKAGING_PROVENANCE.json'}==set(names)
            for row in provenance['files']:
                raw=z.read(row['target']);assert len(raw)==row['bytes'] and sha(raw)==row['target_sha256']
            COLD.mkdir();LOGS.mkdir()
            for i in infos:
                p=COLD/PurePosixPath(i.filename);p.parent.mkdir(parents=True,exist_ok=True)
                with p.open('xb') as f:f.write(z.read(i))
        report['extraction_count']=1
        report['source_whitelist']=dict(files=len(expected),exact_record_bytes_and_SHA=True,
            exact_provenance_target_SHA=True,extra_files=[],unsafe_entries=[])
        dump(LOGS/'PROTECTED_HASHES_BEFORE.json',before)
        command=['uv','run','--no-project','--offline','python','-B',str(COMPILE),'main.tex','--recipe','pdflatex-bibtex']
        report['compile']=dict(command=command,cwd=str(COLD),skill_sha256=sha(SKILL.read_bytes()),
            compile_script_sha256=sha(COMPILE.read_bytes()))
        report['compilation_count']=1
        p=run(command,'SKILL_COMPILE',COLD);report['compile']['returncode']=p.returncode
        spec=importlib.util.spec_from_file_location('cold_v9_pure_qa',QA)
        qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
        layout={};flow={};pagination={};fonts={};font_raw={};pages={}
        for label,pdf in [('release',REL/'main.pdf'),('cold',COLD/'main.pdf')]:
            info=run(['pdfinfo',str(pdf)],label+'_info').stdout.decode('utf8','replace')
            match=re.search(r'(?m)^Pages:\s*(\d+)',info);assert match
            pages[label]=int(match[1]);assert pages[label]==final['total_pages']==12
            layout[label]=run(['pdftotext','-layout','-enc','UTF-8',str(pdf),'-'],label+'_layout').stdout
            flow[label]=run(['pdftotext','-enc','UTF-8',str(pdf),'-'],label+'_flow').stdout
            pagination[label]=qa.reference_pages(flow[label].decode('utf8'),12,11)
            assert pagination[label]['status']=='PASS',pagination[label]
            assert pagination[label]['technical_pages']==11 and pagination[label]['references_start_page']==12
            assert pagination[label]['reference_numbers_seen']==list(range(1,32))
            font_raw[label]=run(['pdffonts',str(pdf)],label+'_fonts').stdout
            fonts[label]=qa.font_check(font_raw[label].decode('utf8'))
            assert fonts[label]['status']=='PASS' and fonts[label]['font_count']==30,fonts[label]
        assert layout['release']==layout['cold'] and flow['release']==flow['cold']
        def split(raw):
            p=raw.decode('utf8').split('\f')
            if p and not p[-1].strip():p.pop()
            assert len(p)==12
            return p
        per_page=[dict(page=i+1,byte_identical=a==b,release_sha256=sha(a.encode()),cold_sha256=sha(b.encode()))
            for i,(a,b) in enumerate(zip(split(layout['release']),split(layout['cold'])))]
        assert all(x['byte_identical'] for x in per_page)
        log=(COLD/'main.log').read_text(encoding='utf8',errors='replace')
        patterns=dict(undefined_citations=r'Citation\s+.*?undefined',undefined_references=r'Reference\s+.*?undefined',
            undefined_control_sequences=r'Undefined control sequence',unresolved_summary=r'There were undefined (?:references|citations)',
            overfull=r'Overfull\s*\\[hv]box',rerun=r'Label\(s\) may have changed|Rerun to get')
        warnings={k:re.findall(pattern,log,re.I) for k,pattern in patterns.items()}
        assert not any(warnings.values()),warnings
        assert all(rec(COLD/name)==dict(bytes=x['bytes'],sha256=x['sha256'])
            for name,x in expected.items() if name!='main.pdf')
        after={str(p):rec(p) for p in protected};assert before==after
        dump(LOGS/'PROTECTED_HASHES_AFTER.json',after)
        report.update(gate='PASS_ZIP_ONLY_COLD_SKILL_BUILD_LAYOUT_AND_SOURCE_PARITY',
            layout_text_bytes_identical=True,flow_text_bytes_identical=True,per_page_layout=per_page,
            pagination=pagination,embedded_fonts=fonts,font_lists_byte_identical=font_raw['release']==font_raw['cold'],
            final_log_checks=warnings,all_original_inputs_SHA_before_after_unchanged=True,
            cold_packaged_source_bytes_unchanged=True,original_zip=rec(ZIP),original_pdf=rec(REL/'main.pdf'),
            rebuilt_pdf=rec(COLD/'main.pdf'),PDF_metadata_bytes_may_differ=True,final_record_sha256=sha(FINAL.read_bytes()),
            qa_reader_sha256=sha(QA.read_bytes()),driver_sha256=sha(Path(__file__).read_bytes()),
            bounded_log_bytes=sum(p.stat().st_size for p in LOGS.iterdir() if p.is_file()),
            completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    except BaseException as exc:
        report.update(gate='FAIL_PRESERVED_COLD_BUILD_CHECK',error_type=type(exc).__name__,reason=str(exc),traceback=traceback.format_exc())
        if before:
            report['protected_inputs_unchanged_after_failure']=before=={p:rec(Path(p)) for p in before}
        dump(OUT,report);raise
    dump(OUT,report)
    print(json.dumps(dict(gate=report['gate'],files=len(expected),extractions=report['extraction_count'],
        compilations=report['compilation_count'],compile_exit=report['compile']['returncode'],
        layout_identical_pages=12,technical_pages=11,references_only_pages=1,references=31,
        embedded_font_entries=30,original_hashes_unchanged=True,report_sha256=sha(OUT.read_bytes()))))

if __name__=='__main__':main()
