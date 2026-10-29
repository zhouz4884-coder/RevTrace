from __future__ import annotations
import argparse,hashlib,json,platform,subprocess,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch,PathPatch
from matplotlib.path import Path as MPath
import fitz

W,H=7.15,4.45
BLUE='#0F4D92';GREEN='#28795D';INK='#272727';GRAY='#767676'
TEXT=[];BOUNDS=[]

def sha(b):return hashlib.sha256(b).hexdigest()
def put(p,v):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,required=True);parser.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args();config_bytes=args.config.read_bytes();config=json.loads(config_bytes)
    source=Path(__file__).resolve().parent;manifest_bytes=args.manifest.read_bytes();manifest=json.loads(manifest_bytes)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    assert commit==manifest['code_commit']
    assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=source,text=True).strip()
    for row in manifest['files']:
        b=(source/row['path']).read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256']
    for name,proof in config['input_files'].items():
        b=Path(name).read_bytes();assert dict(bytes=len(b),sha256=sha(b))==proof,name
    out=Path(config['output']);out.mkdir(parents=True,exist_ok=False)
    plt.rcParams.update({'font.family':['Arial','Helvetica','DejaVu Sans'],'font.size':8.5,
        'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','text.usetex':False,
        'savefig.facecolor':'white','figure.facecolor':'white'})
    fig=plt.figure(figsize=(W,H));ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,W),ylim=(0,H));ax.axis('off')
    def text(x,y,value,size=8.5,color=INK,weight='normal',ha='center',box=None):
        obj=ax.text(x,y,value,fontsize=size,color=color,fontweight=weight,ha=ha,va='center',linespacing=1.2)
        TEXT.append(obj)
        if box is not None:BOUNDS.append((obj,box))
        return obj
    def card(x,y,w,h,title,body,*,color=INK,face='#F7F7F7',title_size=9.4,body_size=8.4):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.0,rounding_size=0.045',
            linewidth=1.0,edgecolor=color,facecolor=face))
        bounds=(x+.035,y+.025,w-.07,h-.05)
        text(x+w/2,y+h-.15,title,title_size,color,'bold',box=bounds)
        lines=body.count('\n')+1
        cy=y+(h-.22)/2
        text(x+w/2,cy,body,body_size,box=bounds)
    def arrow(points,color=INK,width=1.0,style='-'):
        if len(points)>2:
            ax.add_patch(PathPatch(MPath(points[:-1],[MPath.MOVETO]+[MPath.LINETO]*(len(points)-2)),
                fill=False,color=color,linewidth=width,linestyle=style,capstyle='round',joinstyle='round'))
        a,b=points[-2:]
        ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=8.,color=color,
            linewidth=width,linestyle=style,shrinkA=0,shrinkB=0))

    text(.14,4.32,'a  Certified selection and legitimate provisional progress',10.1,weight='bold',ha='left')
    card(.15,3.57,1.70,.60,'Authority','actual selected (F, Z, P)',color=BLUE,face='#EDF3F9')
    card(2.65,3.57,1.90,.60,'WAL → Canonical','protected write → install',color=BLUE,face='#EDF3F9')
    arrow([(1.85,3.87),(2.65,3.87)],BLUE)
    text(2.25,4.02,'selection',8.0,BLUE)

    card(.15,2.35,1.70,.80,'Private chain','complete results +\nfrozen in-flight input',color=GREEN,face='#EDF6F1')
    card(2.65,2.35,1.90,.80,'R: retain computation','same F and full P\nactual completed ancestry\nfrozen in-flight input',color=GREEN,face='#EDF6F1',body_size=8.2)
    arrow([(1.85,2.75),(2.65,2.75)],GREEN)
    text(2.25,2.92,'evidence',8.0,GREEN)
    arrow([(3.60,3.57),(3.60,3.15)],BLUE)
    text(3.77,3.36,'installed (F, P)',8.0,BLUE,ha='left')

    x,y,w,h=5.15,2.35,1.85,1.82
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.0,rounding_size=0.045',linewidth=1.05,edgecolor=INK,facecolor='white'))
    text(6.075,4.02,'Actual Consumer',9.5,weight='bold',box=(x+.035,y+.03,w-.07,h-.06))
    for yy,face,color in [(3.45,'#EDF3F9',BLUE),(2.72,'#EDF6F1',GREEN)]:
        ax.add_patch(FancyBboxPatch((5.28,yy),1.59,.47,boxstyle='round,pad=0.0,rounding_size=0.035',linewidth=.85,edgecolor=color,facecolor=face))
    text(6.075,3.685,'Certified lane\nselected root advances',8.5,BLUE,box=(5.29,3.46,1.57,.45))
    text(6.075,2.955,'S: whole provisional view\nretain if compatible',8.3,GREEN,box=(5.29,2.73,1.57,.45))
    text(6.075,3.31,'independent lanes',8.1,GRAY)
    text(6.075,2.51,'No suffix joining',8.3,weight='bold')
    arrow([(4.55,3.87),(4.88,3.87),(4.88,3.685),(5.28,3.685)],BLUE)
    arrow([(1.00,2.35),(1.00,2.07),(4.94,2.07),(4.94,2.955),(5.28,2.955)],GREEN)
    text(3.00,2.21,'whole hypothesis remains provisional',8.2,GREEN)

    text(.14,1.75,'b  Coverage exit and actual physical release',10.1,weight='bold',ha='left')
    xs=[.17,1.47,2.46,3.50,4.86,6.08]
    ws=[1.16,.85,.90,1.22,1.08,.90]
    bodies=['Canonical F\ncovers target\n(no use remains)','Cancel\nrequest','Decode\nsafe point','RowComplete\nor\nRowCancelled','All rows terminal\n+ device sync\nBatchDrained','Lease\nreleased']
    for i,(xx,ww,body) in enumerate(zip(xs,ws,bodies)):
        color=BLUE if i==0 else INK
        face='#EDF3F9' if i==0 else '#F5F5F5' if i!=5 else '#E9F3ED'
        ax.add_patch(FancyBboxPatch((xx,.62),ww,.83,boxstyle='round,pad=0.0,rounding_size=0.04',linewidth=.95,edgecolor=color,facecolor=face))
        text(xx+ww/2,1.035,body,8.1,color,weight='bold' if i in (0,5) else 'normal',box=(xx+.025,.645,ww-.05,.78))
        if i:
            arrow([(xs[i-1]+ws[i-1],1.035),(xx,1.035)],GRAY,.9)
    text(.17,1.54,'K',9.,BLUE,'bold',ha='left')
    text(3.575,.35,'RowComplete may be delivered early; only synchronized batch drain releases the lease.',8.3)

    fig.canvas.draw();renderer=fig.canvas.get_renderer();figure_box=fig.bbox
    failures=[]
    for obj in TEXT:
        b=obj.get_window_extent(renderer=renderer)
        if obj.get_fontsize()<8 or b.x0<figure_box.x0-0.1 or b.y0<figure_box.y0-0.1 or b.x1>figure_box.x1+.1 or b.y1>figure_box.y1+.1:
            failures.append(dict(text=obj.get_text(),reason='font_or_canvas_bounds'))
    for obj,(bx,by,bw,bh) in BOUNDS:
        box=ax.transData.transform([(bx,by),(bx+bw,by+bh)]);b=obj.get_window_extent(renderer=renderer)
        if b.x0<box[0][0]-.1 or b.y0<box[0][1]-.1 or b.x1>box[1][0]+.1 or b.y1>box[1][1]+.1:
            failures.append(dict(text=obj.get_text(),reason='containing_card_bounds'))
    assert not failures,failures
    stem=out/'coordination_protocol'
    for suffix in ['pdf','svg','png']:
        fig.savefig(stem.with_suffix('.'+suffix),dpi=350,bbox_inches=None)
    plt.close(fig)
    doc=fitz.open(stem.with_suffix('.pdf'));page=doc[0]
    fonts=page.get_fonts(full=True);assert all('Type3' not in str(row) for row in fonts)
    assert abs(page.rect.width/72-W)<.001 and abs(page.rect.height/72-H)<.001
    page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False).save(out/'coordination_protocol_PDF_PAGE.png')
    env=dict(python=sys.version,platform=platform.platform(),matplotlib=matplotlib.__version__,pymupdf=fitz.VersionBind)
    put(out/'QA.json',dict(status='PASS_PROGRAMMATIC_FULL_PAGE_QA',width_inches=W,height_inches=H,
        minimum_font_pt=min(obj.get_fontsize() for obj in TEXT),svg_text_editable=True,pdf_fonts=fonts,Type3=0,
        canvas_and_card_text_bounds='PASS',visual_QA='PENDING_SEPARATE_FULL_PAGE_INSPECTION'))
    put(out/'PLOT_RECORD.json',dict(experiment_id=config['experiment_id'],evidence_type='method illustration; no new measured performance',
        plot_source_commit=commit,plot_source_manifest_sha256=sha(manifest_bytes),frozen_config_sha256=sha(config_bytes),
        environment=env,input_files=config['input_files'],execution_source_commit=config['execution_source_commit'],new_GPU_calls=0,
        outputs={p.name:dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in out.iterdir() if p.is_file()}))
    print(json.dumps(dict(output=str(out),status='PASS_PROGRAMMATIC_FULL_PAGE_QA',minimum_font=8.,Type3=0)))

if __name__=='__main__':main()
