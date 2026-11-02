"""Draw already measured complete-cohort partitions; no measurement or reader."""
from pathlib import Path
import argparse,hashlib,json,platform,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 j=json.loads(Path(a.input).read_bytes());rows=j['rows']
 assert len(rows)==4 and [(r['bank'],r['speakers'],r['policy']) for r in rows]==[(b,n,s) for b,n in [('Independent',8),('Resident',4)] for s in ['conservative','fullcall']]
 for r in rows:
  assert r['offered']>0 and all(r[k]>=-1e-10 for k in ['matching','mismatching','unknown','untimely'])
  assert abs(sum(r[k] for k in ['matching','mismatching','unknown','untimely'])-r['offered'])<1e-8
 for i in (0,2):assert abs(rows[i]['offered']-rows[i+1]['offered'])<1e-8
 out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8.0,'axes.labelsize':8.0,'xtick.labelsize':8.0,'ytick.labelsize':8.0,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.65,'hatch.linewidth':.6,'savefig.facecolor':'white'})
 fig,ax=plt.subplots(figsize=(3.48,2.75));fig.subplots_adjust(left=.285,right=.985,bottom=.33,top=.96)
 has_unknown=any(r['unknown']>1e-9 for r in rows)
 parts=[('matching','#2B5F91',None,'Timely; matches selected text'),('mismatching','#DCCFF0','///','Timely; different selected text')]
 if has_unknown:parts.append(('unknown','#E9D6A8','..','Timely; agreement unknown'))
 parts.append(('untimely','#EFF1F4',None,'Misses a delivery deadline'))
 ys=[3.16,2.45,1.10,.39];labels=[];small=[]
 for idx,(r,y) in enumerate(zip(rows,ys)):
  left=0.
  for key,color,hatch,label in parts:
   value=100*r[key]/r['offered'];ax.barh(y,value,left=left,height=.38,color=color,edgecolor='#737D89',linewidth=.35,hatch=hatch,zorder=2)
   if value>=8:
    ax.text(left+value/2,y,f'{value:.1f}',ha='center',va='center',color='white' if key=='matching' else '#273449',fontsize=8)
   elif value>0 and key=='untimely':
    ax.annotate(f'{value:.1f}%',xy=(left+value/2,y),xytext=(99,y-.37),ha='right',va='center',fontsize=8,color='#576A7D',arrowprops=dict(arrowstyle='-',lw=.5,color='#7E8893',connectionstyle='angle,angleA=0,angleB=90,rad=0'))
    small.append(dict(row=idx,category=key,percent=value,label='external'))
   elif value>0:small.append(dict(row=idx,category=key,percent=value,label='retained visible slice; exact value in input'))
   left+=value
  assert abs(left-100)<1e-7
  labels.append('Conservative' if r['policy']=='conservative' else 'RevTrace')
 ax.set(yticks=ys,yticklabels=labels,xlim=(0,100),ylim=(-.18,3.86),xticks=[0,50,100],xlabel='Offered audio (%)')
 ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0,pad=4);ax.tick_params(axis='x',width=.65,length=3)
 ax.text(0,3.66,'Independent (8 speakers)',fontsize=8.2,fontweight='bold',color='#273449')
 ax.text(0,1.62,'Resident (4 speakers)',fontsize=8.2,fontweight='bold',color='#273449')
 handles=[Patch(facecolor=color,edgecolor='#737D89',hatch=hatch,linewidth=.4,label=label) for _,color,hatch,label in parts]
 fig.legend(handles=handles,loc='lower left',bbox_to_anchor=(.025,.008),ncol=1,fontsize=8,labelspacing=.18,handlelength=1.25,handletextpad=.5,borderaxespad=0)
 files=[]
 for ext in ['pdf','svg','png']:
  target=out/('native_content.'+ext);fig.savefig(target,dpi=300);files.append(dict(path=target.name,bytes=target.stat().st_size,sha256=sha(target)))
 record=dict(gate='PASS_INPUT_BOUND_COMPLETE_PARTITION_VECTOR_EXPORT',input_sha256=sha(a.input),renderer_sha256=sha(__file__),python=sys.version,executable=sys.executable,platform=platform.platform(),matplotlib=matplotlib.__version__,width_inches=3.48,height_inches=2.75,minimum_font_pt=8.,grayscale_encoding='purple hatch plus neutral deadline-miss fill; unknown dotted if present',separate_cohort_denominators=True,unknown_visible_if_nonzero=has_unknown,small_slices=small,new_model_calls=0,actual_reader_calls=0,rows=rows,files=files,visual_QA='PENDING_ACTUAL_SIZE_INSPECTION')
 (out/'SUMMARY.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');(out/'GATE.json').write_text(json.dumps({k:v for k,v in record.items() if k not in ('rows','files')},indent=2)+'\n',encoding='utf-8');plt.close(fig)
 print(json.dumps({k:v for k,v in record.items() if k not in ('rows','files','small_slices')}))
if __name__=='__main__':main()
