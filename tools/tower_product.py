"""Photo-constrained grow-tower reconstruction; dimensions distinguish catalog from fit.

Five hollow flares are joined to each open hub. Net baskets are separate solids.
Collision shells are partitioned around their openings, never a filled tier hull.
No claim of manufacturer CAD or exact internal irrigation geometry is made.
"""
import numpy as np
import cadquery as cq
from scipy.spatial.transform import Rotation


def pose(t, k, row=0):
    yaw=360*k/t['pockets_per_row']+(t['tier_rotation_offset_deg'] if row%2==0 else 0)
    rz=Rotation.from_euler('z',yaw,degrees=True)
    return rz.apply([0,-t['pocket_base_offset_m'],0]), rz*Rotation.from_euler('x',t['pocket_tilt_from_vertical_deg'],degrees=True)


def transform(shape,offset,rot):
    rv=rot.as_rotvec();a=np.linalg.norm(rv)
    if a>1e-10:shape=shape.rotate((0,0,0),tuple(rv/a),np.rad2deg(a))
    return shape.translate(tuple(np.array(offset)*1000))


def cad(t):
    P=t['row_pitch_m']*1000;R=t['core_radius_m']*1000;w=t['wall_thickness_m']*1000
    L=t['pocket_length_m']*1000;r0=t['pocket_base_radius_m']*1000;r1=t['pocket_top_radius_m']*1000;mouth=t['mouth_radius_m']*1000
    hub=cq.Workplane('XY').circle(R).extrude(P)
    # Flared shells join the hub instead of hovering as individual drinking cups.
    outer=cq.Workplane('XY').circle(r0).workplane(offset=L).circle(r1).loft()
    void=cq.Workplane('XY').workplane(offset=w).circle(r0-w).workplane(offset=L-6-w).circle(r1-w).loft()
    void=void.union(cq.Workplane('XY').workplane(offset=L-7).circle(mouth).extrude(16))
    shell=hub
    for k in range(t['pockets_per_row']):
        off,rot=pose(t,k,row=1);shell=shell.union(transform(outer,off,rot))
    for k in range(t['pockets_per_row']):
        off,rot=pose(t,k,row=1);shell=shell.cut(transform(void,off,rot))
    shell=shell.cut(cq.Workplane('XY').workplane(offset=-1).circle(R-w).extrude(P+2))
    # Slip collar at the hub; tolerance and lock/latch details await measurements.
    # Kept wholly within the tier envelope to preserve the constrained stack-up.
    shell=shell.union(cq.Workplane('XY').workplane(offset=P-4).circle(R+1.5).circle(R-w).extrude(4))
    basket=cq.Workplane('XY').circle(mouth+3).circle(mouth-1).extrude(3)
    basket=basket.union(cq.Workplane('XY').workplane(offset=-51).circle(18).circle(15.5).extrude(3))
    for k in range(12):
        a=2*np.pi*k/12
        p=np.array([17*np.cos(a),17*np.sin(a),-49.5]);q=np.array([(mouth-1.6)*np.cos(a),(mouth-1.6)*np.sin(a),1])
        v=q-p;rod=cq.Solid.makeCylinder(1.1,float(np.linalg.norm(v)),cq.Vector(*p),cq.Vector(*v))
        basket=basket.union(cq.Workplane(obj=rod))
    for angle in [0,60,120]:
        spoke=cq.Workplane('XY').box(33,1.7,2).translate((0,0,-50)).rotate((0,0,0),(0,0,1),angle)
        basket=basket.union(spoke)
    W=t['reservoir_width_m']*1000;D=t['reservoir_depth_m']*1000;H=t['reservoir_body_height_m']*1000
    # Rounded square frustum, hollow with an independent removable lid.
    def rounded(w,d,r,z):
        return cq.Workplane('XY').workplane(offset=z).sketch().rect(w,d).vertices().fillet(r).finalize()
    bottom=rounded(W-40,D-40,18,0).extrude(1).faces('<Z').wires().val();top=rounded(W-8,D-8,23,H).extrude(1).faces('<Z').wires().val()
    outertank=cq.Solid.makeLoft([bottom,top])
    ib=rounded(W-46,D-46,16,3).extrude(1).faces('<Z').wires().val();it=rounded(W-14,D-14,20,H+1).extrude(1).faces('<Z').wires().val()
    tank=cq.Workplane(obj=outertank.cut(cq.Solid.makeLoft([ib,it])))
    lid=rounded(W,D,22,0).extrude(t['lid_thickness_m']*1000)
    lid=lid.cut(cq.Workplane('XY').circle(R-w).extrude(20))
    # Pump cable/service cap represented visibly, with no invented pump dynamics.
    service=cq.Workplane('XY').circle(17).extrude(3)
    wheel=cq.Workplane('XY').circle(18).circle(3).extrude(13).edges('%Circle').fillet(1)
    bracket=cq.Workplane('XY').box(24,20,12).edges('|Z').fillet(3)
    collar=cq.Workplane('XY').circle(R).circle(R-w).extrude(t['top_collar_height_m']*1000)
    return {'tier_module':shell,'net_basket':basket,'tank':tank,'tank_lid':lid,'caster_wheel':wheel,'caster_bracket':bracket,'service_cap':service,'top_collar':collar}


def add_tower(root,world,assets,cfg,piece,add,vec,quat):
    t=cfg['tower'];tower=add(world,'body',name='growing_tower',pos=vec(t['center_m']))
    P=t['row_pitch_m'];R=t['core_radius_m'];w=t['wall_thickness_m'];L=t['pocket_length_m'];r0=t['pocket_base_radius_m'];r1=t['pocket_top_radius_m'];mouth=t['mouth_radius_m']
    tank=piece(tower,'reservoir','tank',[0,0,t['caster_height_m']],color='dark')
    # Reservoir outer-envelope contacts; access inside the tank isn't in task scope.
    add(tank,'geom',name='reservoir_collision',type='box',size=vec([t['reservoir_width_m']/2,t['reservoir_depth_m']/2,t['reservoir_body_height_m']/2]),pos=vec([0,0,t['reservoir_body_height_m']/2]),rgba='0 0 0 0',contype='4',conaffinity='3')
    piece(tower,'reservoir_lid','tank_lid',[0,0,t['caster_height_m']+t['reservoir_body_height_m']],color='white')
    piece(tower,'reservoir_service_cap','service_cap',[.13,0,t['first_row_base_m']],color='white')
    for i,(x,y) in enumerate([(-.155,-.155),(-.155,.155),(.155,-.155),(.155,.155)]):
        piece(tower,f'caster_bracket_{i}','caster_bracket',[x,y,.035],color='dark')
        piece(tower,f'caster_wheel_{i}','caster_wheel',[x,y+.0065,.018],Rotation.from_euler('x',90,degrees=True),color='dark')
    # Convex narrow sectors retain hollow central and planting openings.
    def sectors(body,name,levels,n=24):
        for j in range(n):
            verts=[]
            for z,ro,ri in levels:
                for radius in [ro,ri]:
                    for a in np.array([j,j+1])*2*np.pi/n:verts.append([radius*np.cos(a),radius*np.sin(a),z])
            mesh=name+'_'+str(j)
            if mesh not in mesh_names:
                add(assets,'mesh',name=mesh,vertex=vec(verts));mesh_names.add(mesh)
            add(body,'geom',type='mesh',mesh=mesh,rgba='0 0 0 0',contype='4',conaffinity='3')
    mesh_names=set();active=None
    for row in range(t['rows']):
        yaw=t['tier_rotation_offset_deg'] if row%2==0 else 0
        base=np.array([0,0,t['first_row_base_m']+row*P])
        tier=piece(tower,f'tier_{row}','tier_module',base,Rotation.from_euler('z',yaw,degrees=True),color='white')
        sectors(tier,'hub_shell',[(0,R,R-w),(P,R,R-w)])
        for k in range(t['pockets_per_row']):
            # Tier body already supplies the alternating yaw.
            off,rot=pose(t,k,row=1)
            p=add(tier,'body',name=f'pocket_{row}_{k}',pos=vec(off),quat=quat(rot))
            sectors(p,'flare_shell',[(0,r0,r0-w),(L-.006,r1,r1-w)])
            sectors(p,'shoulder_shell',[(L-.006,r1,mouth),(L,r1,mouth)])
            basket=piece(p,f'basket_{row}_{k}','net_basket',[0,0,L+.001],color='metal')
            sectors(basket,'basket_rim',[(0,mouth+.003,mouth-.001),(.003,mouth+.003,mouth-.001)])
            # Discrete ribs, not a closed cone that would seal the actual net.
            for j in range(12):
                a=2*np.pi*j/12
                a0=[.017*np.cos(a),.017*np.sin(a),-.0495]
                a1=[(mouth-.0016)*np.cos(a),(mouth-.0016)*np.sin(a),.001]
                add(basket,'geom',type='capsule',fromto=vec([a0,a1]),size='.0011',rgba='0 0 0 0',contype='4',conaffinity='3')
            if row==t['active_row'] and k==t['active_pocket']:active=basket
    piece(tower,'tower_top_collar','top_collar',[0,0,t['first_row_base_m']+t['rows']*P],color='white')
    assert active is not None
    return active
