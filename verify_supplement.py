"""核对公开数据的补充表、逐样本误差与文件清单，不执行拟合或圈时求解。"""
import csv
import hashlib
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent

def read(name):
    with (ROOT/name).open(encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f))

def main():
    manifest=read('manifest_sha256.csv')
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and p.name!='manifest_sha256.csv'}
    assert actual=={r['file'] for r in manifest}
    for r in manifest:
        p=ROOT/r['file']
        assert p.stat().st_size==int(r['bytes'])
        assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],r['file']
    index={r['trajectory_id']:r for r in read('trajectories/index.csv')}
    mesh=read('results/zhejiang_mesh.csv')
    restarts=read('results/zhejiang_restarts.csv')
    assert len(mesh)==8 and len(restarts)==4
    for r in mesh+restarts:
        q=index[r['trajectory_id']]
        assert q['circuit']==r['circuit']=='zhejiang'
        assert q['mesh_nodes']==r['mesh_nodes']
        assert abs(float(q['lap_time_s'])-float(r['lap_time_s']))<1e-8
        assert r['original_accepted']=='true' and r['full_supplemental_pass']=='false'
    for step,n,expected in [('1','3205',.433243),('1.5','2137',.344657),('3','1069',.342257),('6','535',.203711)]:
        pair={r['strategy']:float(r['lap_time_s']) for r in mesh if r['nominal_spacing_m']==step}
        assert len(pair)==2 and all(r['mesh_nodes']==n for r in mesh if r['nominal_spacing_m']==step)
        assert abs(pair['constant']-pair['fitted_dry']-expected)<.5e-6
    gaps=[]
    for route,expected in [('restart_from_1m',.433464),('reconstruct_from_3m',.408933)]:
        pair={r['strategy']:float(r['lap_time_s']) for r in restarts if r['initialisation']==route}
        assert len(pair)==2
        gap=pair['constant']-pair['fitted_dry']; gaps.append(gap)
        assert abs(gap-expected)<.5e-6
    assert round(abs(gaps[0]-gaps[1])*1000,1)==24.5
    for r in restarts:
        assert float(r['initial_barrier_parameter'])==1e-5
        assert float(r['acceptable_optimality_tolerance'])==.0003
        assert float(r['acceptable_constraint_tolerance'])==1e-7
    teacher=read('calibration/teacher_dry.csv')
    predictions=read('calibration/fairness_predictions.csv')
    assert len(teacher)==len(predictions)==4500
    assert len({(r['circuit'],r['s_m']) for r in teacher})==4500
    for n,(t,p) in enumerate(zip(teacher,predictions)):
        assert t['circuit']==p['circuit'] and float(t['s_m'])==float(p['s_m'])
        assert int(p['sample_id'])==n+1
    y=np.array([float(r['rear_delta_wheel_torque_nm']) for r in teacher])
    total=np.array([float(r['rear_total_wheel_torque_nm']) for r in teacher])
    groups=np.array([r['circuit'] for r in teacher])
    summary=read('results/calibration_fairness.csv')
    assert len(summary)==36
    variants={r['variant'] for r in summary}
    assert len(variants)==6
    seen=set()
    for r in summary:
        key=r['variant'],r['evaluation']; assert key not in seen; seen.add(key)
        mask=np.ones(4500,dtype=bool) if r['evaluation'] in ('full','leave_one_out') else groups==r['evaluation']
        suffix='full' if r['evaluation']=='full' else 'leave_one_out'
        pred=np.array([float(p[f"{r['variant']}__{suffix}_nm"]) for p in predictions])[mask]
        error=pred-y[mask]
        significant=np.abs(y[mask])>=50
        expected=dict(mae_nm=np.mean(abs(error)),rmse_nm=np.sqrt(np.mean(error**2)),
            p95_abs_error_nm=np.quantile(abs(error),.95),max_abs_error_nm=np.max(abs(error)),
            ratio_mae=np.mean(abs(error/total[mask])),
            sign_agreement=np.mean(np.sign(pred[significant])==np.sign(y[mask][significant])))
        for k,value in expected.items():
            assert np.isclose(value,float(r[k]),rtol=1e-11,atol=1e-10),(key,k,value,r[k])
        if r['evaluation']=='full': assert float(r['training_samples'])==4500
        elif r['evaluation']!='leave_one_out': assert float(r['training_samples'])==4500-mask.sum()
        else: assert r['training_samples']==''
    coeff=defaultdict(list)
    for r in read('calibration/fairness_coefficients.csv'):
        coeff[r['variant'],r['held_out_circuit']].append(r)
        assert np.isfinite(float(r['coefficient'])) and float(r['coefficient'])>=0
    assert len(coeff)==30
    for (variant,fold),rows in coeff.items():
        assert variant in variants and fold in {'full',*groups}
        if variant.startswith('scalar'):
            assert len(rows)==1 and rows[0]['i']==rows[0]['j']==''
        else:
            assert len(rows)==16 and {(int(r['i']),int(r['j'])) for r in rows}=={(i,j) for i in range(4) for j in range(4)}
    assert abs(float(coeff['scalar_preserve_none','full'][0]['coefficient'])-7.640540785038599)<1e-5
    cv={r['variant']:float(r['mae_nm']) for r in summary if r['evaluation']=='leave_one_out'}
    reduction=100*(1-cv['surface_preserve_none']/cv['scalar_preserve_none'])
    assert round(reduction,2)==35.86
    projection=read('diagnostics/frozen_projection.csv')
    assert len(projection)==2
    for r in projection:
        assert float(r['derated_sample_fraction'])==0 and float(r['derating_threshold_nm'])==.01
        expected=.001574631806415667 if r['strategy']=='constant' else .002657672735020815
        assert abs(float(r['projection_difference_mae_nm'])-expected)<1e-12
    print(f'补充检查通过：S20 8条，S21 4条；S22 36行误差、30套系数、4500个逐样本预测。共同无正则留一MAE降低 {reduction:.2f}%。')
    print(f'文件清单核验通过：{len(manifest)}个文件，另加清单本身。')

if __name__=='__main__':
    main()
