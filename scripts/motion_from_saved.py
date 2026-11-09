"""Render action-labelled trajectories from archived frozen CSML predictions."""
from pathlib import Path
import hashlib, html, json, os, statistics, base64, gzip, io
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import numpy as np
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--replay-outputs',type=Path,required=True)
parser.add_argument('--csml-assets',type=Path,required=True)
parser.add_argument('--output',type=Path,default=Path('reproduced/motions'))
args=parser.parse_args()
out=args.replay_outputs
data=Path(__file__).resolve().parents[1]/'data'
provenance=read(data/'source_provenance.json')
LOCATOR=provenance['frozen_locator_sha256']
PINS={r['variant'][-1]:r['terminal_checkpoint_sha256'] for r in provenance['source_reports'] if r['variant'].startswith('101')}
FAMILIES=read(data/'dynamic_trajectory_receipt.json')['source_action_mapping']
finished=read(out/'report.json')
assert finished['status']=='ALL_SHARED97_LOCALIZATION_COMPLETE' and finished['optimizer_updates']==finished['VJP']==0
names={'M':'measured_full5__measured',**{a:'seed101_'+a+'__all_reconstructed' for a in 'ABC'}}
leaves={a:out/k for a,k in names.items()}
reports={a:read(p/'report.json') for a,p in leaves.items()}
assert all(v['status']=='COMPLETE' and v['locator_checkpoint_SHA256']==LOCATOR and v['optimizer_updates']==v['VJP']==0 for v in reports.values())
assert all(reports[a]['checkpoint_SHA256']==PINS[a] for a in 'ABC')
rows={a:{r['trial']:r for r in v['records']} for a,v in reports.items()}
assert len(rows['M'])==97 and all(set(rows['M'])==set(z) for z in rows.values())
assets=args.csml_assets
assert set(FAMILIES)=={'grid','lines','circle','xyz'}
pools={}; chosen=[]
for family,trials in FAMILIES.items():
    pool=[]
    for trial in trials:
        m=rows['M'][trial]
        b=rows['B'][trial]
        if m['targets']<100 or min(m['coverage'],b['coverage'])<.9:
            continue
        with np.load(leaves['M']/(trial+'.npz'),allow_pickle=False) as z:
            mask=z['position_mask'].astype(bool)
            coords=z['reference_xyz_mm']
        ref=coords[mask]
        assert len(ref)==m['targets']
        if max(np.ptp(ref[:,0]),np.ptp(ref[:,1]))<2 or np.max(ref[:,2])<.6:
            continue
        ids=np.flatnonzero(mask)
        spans=[np.ptp(coords[g],axis=0) for g in np.split(ids,np.flatnonzero(np.diff(ids)!=1)+1) if len(g)>1]
        if family!='grid' and not any(max(v[:2])>=2 for v in spans):
            continue
        if family=='xyz' and not any(max(v[:2])>=2 and v[2]>=.3 for v in spans):
            continue
        pool.append((m['raw']['mean_mm'],trial))
    assert pool,family
    mid=statistics.median(x[0] for x in pool)
    _,trial=min(pool,key=lambda x:(abs(x[0]-mid),x[1]))
    pools[family]={'candidate_count':len(trials),'eligible_count':len(pool),'eligible_trials':[x[1] for x in pool]}
    chosen.append((family,(rows['B'][trial]['raw']['p95_mm']-rows['M'][trial]['raw']['p95_mm'],trial)))
readouts={}
xy_abs=[]; depths=[]
for kind,(delta,trial) in chosen:
    series={}
    with np.load(assets/'data/predictions/shared'/(trial+'.npz'),allow_pickle=False) as original:
        original_mask=original['position_mask'].astype(bool)
        original_ref=original['reference_xyz_mm']
        original_clock=original['t_group_ns']
        nominal_lift=original['nominal_lifted'].astype(bool)
    assert not (original_mask & nominal_lift).any()
    for a,p in leaves.items():
        f=p/(trial+'.npz')
        with np.load(f,allow_pickle=False) as z:
            coords={k:z[k].copy() for k in ['xyz_mm','reference_xyz_mm','position_mask','position_valid','t_group_ns','input_valid','contact_probability','support_probability','expected_error_mm','output_state']}
        mask=coords['position_mask'].astype(bool)
        assert np.array_equal(mask,original_mask) and np.array_equal(coords['t_group_ns'],original_clock)
        assert np.array_equal(coords['reference_xyz_mm'],original_ref,equal_nan=True)
        cp,sup,err=coords['contact_probability'],coords['support_probability'],coords['expected_error_mm']
        finite=np.isfinite(coords['xyz_mm']).all(1)&np.isfinite(cp)&np.isfinite(sup)&np.isfinite(err)&coords['input_valid'].astype(bool)
        gate=finite&(cp>=.5)&(sup>=.5)&(err<=.5)
        assert np.array_equal(gate,coords['position_valid'])
        accepted=mask&gate
        coords['counts']={'frames':len(mask),'eligible_targets':int(mask.sum()),'shown':int(accepted.sum()),
                          'eligible_rejected':int((mask&~gate).sum()),'gate_pass_outside_reference':int((~mask&gate).sum())}
        assert int((nominal_lift&(coords['output_state']>=1)).sum())==rows[a][trial]['contact_diagnostic']['false_contact']
        r=rows[a][trial]
        err=coords['xyz_mm'][mask].astype(float)-coords['reference_xyz_mm'][mask].astype(float)
        mag=np.linalg.norm(err,axis=1)
        al=np.linalg.norm(err-err.mean(0),axis=1)
        assert mask.sum()==r['targets'] and abs(accepted.sum()/mask.sum()-r['coverage'])<1e-12
        for field,vector in [('raw',mag),('translation_removed',al)]:
            assert np.allclose([vector.mean(),np.percentile(vector,95),np.sqrt(np.mean(vector*vector))],
                 [r[field][k] for k in ('mean_mm','p95_mm','rmse_mm')],rtol=1e-12,atol=1e-12)
        coords['source_SHA256']=sha(f)
        if a!='M':
            for k in ['reference_xyz_mm','position_mask','t_group_ns']:
                assert np.array_equal(coords[k],series['M'][k],equal_nan=True)
        xy_abs.extend([abs(coords['reference_xyz_mm'][mask,:2]).max(),abs(coords['xyz_mm'][accepted,:2]).max()])
        depths.extend(coords['reference_xyz_mm'][mask,2].tolist()+coords['xyz_mm'][accepted,2].tolist())
        series[a]=coords
    readouts[kind]=(trial,delta,series)
upper=max(8,int(np.ceil(max(xy_abs))))
limit_depth=max(3.2,float(np.ceil(max(abs(min(depths)),abs(max(depths))))))
if max(abs(min(depths)),abs(max(depths)))<=3.2:limit_depth=3.2
lo=-limit_depth
hi=limit_depth
if hi<=lo: hi=lo+1

def words(x,y,s,**opts):
    extra=' '.join(k.replace('_','-')+'="'+str(v)+'"' for k,v in opts.items())
    return '<text x="%.2f" y="%.2f" %s>%s</text>'%(x,y,extra,html.escape(str(s)))

def line(x1,y1,x2,y2,color='#d6dce0',dash=''):
    return '<line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" stroke="%s" %s/>'%(x1,y1,x2,y2,color,dash)

def paths(x,y,valid,color,dash=''):
    ids=np.flatnonzero(valid & np.isfinite(x) & np.isfinite(y))
    groups=np.split(ids,np.flatnonzero(np.diff(ids)!=1)+1)
    out=[]
    for g in groups:
        if len(g)==1:
            out.append('<circle cx="%.2f" cy="%.2f" r="1.2" fill="%s"/>'%(x[g[0]],y[g[0]],color))
        elif len(g)>1:
            out.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="1.3" %s/>'%(' '.join('%.2f,%.2f'%(x[i],y[i]) for i in g),color,dash))
    return ''.join(out)

figs={}; summaries=[]
for kind,(trial,delta,series) in readouts.items():
    meta={'selection':kind,'trial':trial,'shape':rows['M'][trial]['shape'],'targets':rows['M'][trial]['targets'],
          'B_minus_M_P95_mm':delta,
          'arms':{a:{k:rows[a][trial][k] for k in ('raw','translation_removed','coverage','contact_diagnostic')} for a in names},
          'source_npz_SHA256':{a:z['source_SHA256'] for a,z in series.items()},'display_counts':{a:z['counts'] for a,z in series.items()}}
    summaries.append(meta)
    for lang in ('EN','ZH'):
        zh=lang=='ZH'
        title=({'grid':'点阵触压','lines':'多向直线','circle':'圆形扫描','xyz':'XYZ 联合运动'} if zh else {'grid':'Grid indentation','lines':'Multi-direction straight sweeps','circle':'Circular scanning','xyz':'Combined XYZ motion'})[kind]
        p=['<svg xmlns="http://www.w3.org/2000/svg" width="1160" height="625" viewBox="0 0 1160 625"><rect width="100%" height="100%" fill="white"/><g font-family="Microsoft YaHei, sans-serif" font-size="13" fill="#202b36">']
        p.append(words(27,34,title+'  |  '+trial+'  |  '+({'rounded':'圆弧','hemispherical':'半球','small_flat':'小平头'}[meta['shape']] if zh else meta['shape'].replace('_',' ')),font_size=22,font_weight='bold'))
        p.append(words(27,58,('种子 101，固定 1500 轮，原始坐标。黑虚线／空心点：名义参考。橙线：通过接受规则的输出。' if zh else 'Seed 101, fixed 1500 epochs, raw coordinates. Black dashes or open circles: nominal reference. Orange: accepted output.'),font_size=13))
        labels=({'M':'M 五点实测','A':'A 五点输入／五点监督','B':'B 三点输入／五点监督','C':'C 三点输入／三点监督'} if zh else {'M':'M Measured five','A':'A Five in / five supervised','B':'B Three in / five supervised','C':'C Three in / three supervised'})
        for j,(a,z) in enumerate(series.items()):
            x0=26+282*j; cx=x0+140; xx=x0+55; yy=120; w=170
            r=meta['arms'][a]; mask=z['position_mask'].astype(bool); acc=mask&z['position_valid'].astype(bool)
            p.append(words(cx,88,labels[a],text_anchor='middle',font_size=15,font_weight='bold'))
            p.append(words(cx,108,'%.3f / %.3f mm  |  %.1f%%'%(r['raw']['mean_mm'],r['translation_removed']['mean_mm'],100*r['coverage']),text_anchor='middle',font_size=11))
            axis=lambda v: (v+upper)/(2*upper)*w
            for t in [-upper,0,upper]:
                gx=xx+axis(t); gy=yy+w-axis(t)
                p += [line(gx,yy,gx,yy+w),line(xx,gy,xx+w,gy),words(gx,yy+w+14,t,text_anchor='middle',font_size=10),words(xx-9,gy+4,t,text_anchor='end',font_size=10)]
            p += [words(cx,yy+w+30,'X (mm)',text_anchor='middle'),words(xx-25,yy-5,'Y (mm)',font_size=11)]
            for k,v,col,dash in [('xyz_mm',acc,'#cb6424',''),('reference_xyz_mm',mask,'#182329','stroke-dasharray="4 2"')]:
                xyz=z[k];p.append(paths(xx+axis(xyz[:,0]),yy+w-axis(xyz[:,1]),v,col,dash))
            valid=np.flatnonzero(mask)
            for g in np.split(valid,np.flatnonzero(np.diff(valid)!=1)+1):
                if len(g)>1:
                    xy=z['reference_xyz_mm'][g,:2]
                    if np.max(np.ptp(xy,axis=0))<.04:
                        q=xy[len(g)//2]
                        p.append('<circle cx="%.2f" cy="%.2f" r="2.2" fill="white" stroke="#182329" stroke-width="1"/>'%(xx+axis(q[0]),yy+w-axis(q[1])))
            tx=x0+40; ty=365; tw=205; th=171
            sec=(z['t_group_ns']-z['t_group_ns'][0])/1e9
            limit=max(1,float(sec[-1]))
            for t in [lo,(lo+hi)/2,hi]:
                gy=ty+th-(t-lo)/(hi-lo)*th
                p += [line(tx,gy,tx+tw,gy),words(tx-7,gy+4,'%.1f'%t,text_anchor='end',font_size=10)]
            for t in [0,limit/2,limit]:
                gx=tx+t/limit*tw
                p += [line(gx,ty,gx,ty+th),words(gx,ty+th+15,'%.1f'%t,text_anchor='middle',font_size=10)]
            for k,v,col,dash in [('xyz_mm',acc,'#cb6424',''),('reference_xyz_mm',mask,'#182329','stroke-dasharray="4 2"')]:
                y=ty+th-(z[k][:,2]-lo)/(hi-lo)*th
                p.append(paths(tx+sec/limit*tw,y,v,col,dash))
            p += [words(cx,568,'时间 (s)' if zh else 'Time (s)',text_anchor='middle'),
                  words(tx,ty-8,'压深 (mm)' if zh else 'Indentation (mm)',font_size=11)]
        p.append(words(27,600,('标题数值：原始／整序列常量消偏均误，及接受覆盖率。画线仅限合格定位目标，拒绝处断线。' if zh else 'Headings: raw / constant-offset diagnostic mean error and accepted coverage. Curves use eligible targets and break at rejected frames.'),font_size=12))
        p.append('</g></svg>')
        figs[kind+'_'+lang]=base64.b64encode(gzip.compress(''.join(p).encode())).decode()

trial,_,series=readouts['xyz']
az=np.deg2rad(35); el=np.deg2rad(24)
matrix=np.array([[-np.sin(az),np.cos(az),0],
                 [np.sin(el)*np.cos(az),np.sin(el)*np.sin(az),-np.cos(el)]])
corners=np.array([(x,y,z) for x in (-upper,upper) for y in (-upper,upper) for z in (lo,hi)])
bounds=corners@matrix.T
factor=min(225/np.ptp(bounds[:,0]),200/np.ptp(bounds[:,1]))
for lang in ('EN','ZH'):
    zh=lang=='ZH'
    p=['<svg xmlns="http://www.w3.org/2000/svg" width="1160" height="365" viewBox="0 0 1160 365"><rect width="100%" height="100%" fill="white"/><g font-family="Microsoft YaHei, sans-serif" font-size="13" fill="#202b36">']
    p.append(words(27,31,('XYZ 联合运动的三维对照' if zh else 'Three-dimensional view of combined XYZ motion')+'  |  '+trial,font_size=21,font_weight='bold'))
    p.append(words(27,55,'种子 101，固定 1500 轮。黑虚线：名义参考。橙线：接受的原始输出。' if zh else 'Seed 101, fixed 1500 epochs. Dashed black: nominal reference. Orange: accepted raw output.'))
    labels=({'M':'M 五点实测','A':'A 五点输入／五点监督','B':'B 三点输入／五点监督','C':'C 三点输入／三点监督'} if zh else {'M':'M Measured five','A':'A Five in / five supervised','B':'B Three in / five supervised','C':'C Three in / three supervised'})
    for j,(a,z) in enumerate(series.items()):
        cx=164+282*j
        cy=211
        def project(q):
            return np.asarray(q)@matrix.T*factor+np.array([cx,cy])
        p.append(words(cx,86,labels[a],text_anchor='middle',font_size=15,font_weight='bold'))
        for axis in range(3):
            for q in corners:
                other=q.copy()
                other[axis]*=-1
                if q[axis]<other[axis]:
                    u,v=project(q),project(other)
                    p.append(line(*u,*v,color='#dce1e5'))
        origin=project([-upper,-upper,lo])
        for q,label,dx,dy in [([upper,-upper,lo],'X',3,11),([-upper,upper,lo],'Y',7,7),([-upper,-upper,hi],'Z',-10,-5)]:
            xy=project(q)
            p.append(line(*origin,*xy,color='#8b98a2'))
            p.append(words(xy[0]+dx,xy[1]+dy,label,font_size=11))
        mask=z['position_mask'].astype(bool)
        for key,valid,col,dash in [('xyz_mm',mask&z['position_valid'].astype(bool),'#cb6424',''),
                                    ('reference_xyz_mm',mask,'#182329','stroke-dasharray="4 2"')]:
            xy=project(z[key])
            p.append(paths(xy[:,0],xy[:,1],valid,col,dash))
        p.append(words(cx,330,'X/Y ±%g mm · Z ±%g mm'%(upper,hi),text_anchor='middle',font_size=11))
    p.append(words(27,351,'同一正交视角和三轴物理比例，拒绝帧断开。' if zh else 'Common orthographic view and physical scale on all axes. Rejected frames break the curves.',font_size=12))
    p.append('</g></svg>')
    figs['xyz_3d_'+lang]=base64.b64encode(gzip.compress(''.join(p).encode())).decode()

args.output.mkdir(parents=True,exist_ok=True)
for k,v in figs.items():
    (args.output/('Motion_'+k+'.svg')).write_bytes(gzip.decompress(base64.b64decode(v)))
print('Regenerated matched action figures from saved prediction arrays.')
