"""Independent beam-law verification, NOT a whole-plant contact simulation.

Linear Euler-Bernoulli FEM; state is elastic displacement relative to an
assumed persistent rest curve. No tool, cut, fracture or biological fit.
"""
from pathlib import Path
import json, math, shutil
import numpy as np

HERE=Path(__file__).resolve().parent
OUT=HERE.parents[2]/'runs/hemp-development-v1'
# Illustrative coupon dimensions and material priors. Deliberately separate
# from the branching plant: a horizontal clamp is a different boundary condition.
L=.16; R=.0026; E=80e6; RHO=850.; FORCE=.003
EI=E*math.pi*R**4/4


def matrices(n):
    h=L/n;K=np.zeros((2*(n+1),)*2);M=K.copy()
    ke=EI/h**3*np.array([[12,6*h,-12,6*h],[6*h,4*h*h,-6*h,2*h*h],[-12,-6*h,12,-6*h],[6*h,2*h*h,-6*h,4*h*h]])
    me=RHO*math.pi*R*R*h/420*np.array([[156,22*h,54,-13*h],[22*h,4*h*h,13*h,-3*h*h],[54,13*h,156,-22*h],[-13*h,-3*h*h,-22*h,4*h*h]])
    for i in range(n):
        ix=np.arange(2*i,2*i+4);K[np.ix_(ix,ix)]+=ke;M[np.ix_(ix,ix)]+=me
    return K[2:,2:],M[2:,2:]


def command(t):
    if t<.4:return 0.
    if t<.8:return FORCE*(.5-.5*math.cos(math.pi*(t-.4)/.4))
    if t<1.2:return FORCE
    if t<1.6:return FORCE*(.5+.5*math.cos(math.pi*(t-1.2)/.4))
    return 0.


def run(n,dt):
    K,M=matrices(n);D=.8*M+.0009*K
    # Fixed-root conditions eliminate the first displacement and rotation.
    b=np.zeros(2*n);b[-2]=1
    analytic=FORCE*L**3/(3*EI);static=np.linalg.solve(K,b*FORCE)
    assert abs(static[-2]-analytic)/analytic<1e-7
    beta=.25;gamma=.5
    a0=1/(beta*dt*dt);a1=gamma/(beta*dt);a2=1/(beta*dt);a3=1/(2*beta)-1;a4=gamma/beta-1;a5=dt*(gamma/(2*beta)-1)
    inv=np.linalg.inv(K+a0*M+a1*D)
    q=np.zeros(2*n);vel=q.copy();acc=q.copy();trace=[];energy=[];diss=0.;work=0.;prevF=0.;prevq=q.copy()
    for i in range(round(4/dt)+1):
        t=i*dt;force=command(t)
        if i:
            rhs=b*force+M@(a0*q+a2*vel+a3*acc)+D@(a1*q+a4*vel+a5*acc)
            qn=inv@rhs;an=a0*(qn-q)-a2*vel-a3*acc;vn=vel+dt*((1-gamma)*acc+gamma*an)
            midpoint=(vel+vn)*.5;diss+=float(midpoint@D@midpoint)*dt
            work+=(prevF+force)*.5*float((qn-q)[-2])
            q,vel,acc=qn,vn,an
        en=float(.5*(vel@M@vel+q@K@q));energy.append(en)
        if i%max(1,round(.02/dt))==0:
            trace.append({'t':round(t,5),'force_N':force,'elastic_m':np.r_[0,q[::2]].tolist(),'energy_J':en})
        prevF=force;prevq=q.copy()
    return {'segments':n,'dt_s':dt,'trace':trace,'checks':{
        'static_tip_error_relative':float(abs(static[-2]-analytic)/analytic),
        'energy_balance_relative':float(abs(work-diss-energy[-1])/max(abs(work),1e-12)),
        'dissipated_energy_J':diss,'final_elastic_tip_m':float(q[-2]),
        'max_elastic_tip_m':float(max(abs(x['elastic_m'][-1]) for x in trace)),
        'analytical_static_tip_m':analytic,'final_energy_J':energy[-1]}}


def main():
    base=run(12,.002);fine=run(24,.001)
    t=np.array([x['t'] for x in base['trace']]);a=np.array([x['elastic_m'][-1] for x in base['trace']]);b=np.array([x['elastic_m'][-1] for x in fine['trace']]);diff=float(np.max(abs(a-b)))
    assert diff<.00002, 'Mesh/time refinement exceeds predeclared 20 micrometre tolerance'
    assert base['checks']['energy_balance_relative']<.01
    assert base['checks']['dissipated_energy_J']>=0
    result={'status':'analytical and numerical verification only; uncalibrated plant material',
            'coupon':{'length_m':L,'radius_m':R,'E_Pa':E,'density_kg_m3':RHO,'EI_Nm2':EI,
                      'boundary':'root clamped, incremental tip force, no gravity or tool contact',
                      'rest_curve':'15 mm x/L squared; assumed shallow persistent shape, not fitted growth'},
            'base':base,'fine_checks':fine['checks'],'max_refinement_tip_difference_m':diff,
            'persistent_rest_curve_preserved_by_construction':True,
            'biologically_validated':False,'whole_plant_test':False}
    (OUT/'mechanics.json').write_text(json.dumps(result,separators=(',',':')))
    report={k:v for k,v in result.items() if k!='base'};report['base_checks']=base['checks']
    (HERE/'evidence/mechanics-audit.json').write_text(json.dumps(report,indent=2))
    shutil.copy2(HERE/'mechanics.html',OUT/'mechanics.html')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
