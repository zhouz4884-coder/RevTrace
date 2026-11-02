"""Build the isolated LaTeX revision without latexmk/Perl dependency."""
from pathlib import Path
import hashlib,json,shutil,subprocess
E=Path(__file__).resolve().parents[1];R=E.parents[1]
paper=R/'Paper_DSN/revisions/20261102_dsn2027_release_v10'
qa=E/'paper_qa';qa.mkdir(exist_ok=True)
commands=[['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],['bibtex','main'],['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex']]
receipts=[]
for n,cmd in enumerate(commands):
    cmd[0]=shutil.which(cmd[0]);assert cmd[0]
    r=subprocess.run(cmd,cwd=paper,capture_output=True)
    (qa/f'build_pass_{n}.txt').write_bytes(r.stdout+r.stderr)
    receipts.append(dict(command=cmd,exit_code=r.returncode))
    if r.returncode:
        print((r.stdout+r.stderr).decode(errors='replace')[-4500:]);raise SystemExit(r.returncode)
pdf=paper/'main.pdf';log=(paper/'main.log').read_text(errors='replace')
record=dict(commands=receipts,pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),pdf_bytes=pdf.stat().st_size,
    log_issues=[s for s in log.splitlines() if any(x in s for x in ['Overfull','undefined','multiply defined','LaTeX Error'])],
    scope='LaTeX build only; experiment and visual checks separate')
(qa/'BUILD_RECEIPT.json').write_bytes((json.dumps(record,indent=2)+'\n').encode());print(json.dumps(record))
