import json, math, random, heapq
from shapely.geometry import shape, Point, box, LineString
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely import STRtree

C=json.load(open('ne_50m_admin_0_countries.geojson'))['features']
LAKES=[shape(f['geometry']) for f in json.load(open('ne_50m_lakes.geojson'))['features']]
RIV=json.load(open('ne_50m_rivers_lake_centerlines.geojson'))['features']
PP=json.load(open('ne_50m_populated_places_simple.geojson'))['features']
REG=json.load(open('ne_10m_geography_regions_polys.geojson'))['features']
A1=json.load(open('ne_10m_admin_1_states_provinces.geojson'))['features']
RIV10=json.load(open('ne_10m_rivers_lake_centerlines.geojson'))['features']
LAKES10=[shape(f['geometry']).buffer(0) for f in json.load(open('ne_10m_lakes.geojson'))['features']]
ROADS=[f for f in json.load(open('ne_10m_roads.geojson'))['features'] if f['properties'].get('type') in ('Major Highway','Beltway') and f['properties'].get('scalerank',99)<=6]
PP10=json.load(open('ne_10m_populated_places_simple.geojson'))['features']
import numpy as np
_T=np.load('topo.npz');TOPO=_T['t'].astype(float)
def elev(lon,lat):
    y=(lat+90)*6; x=(lon+180)*6; i=int(y); j=int(x); fy=y-i; fx=x-j
    i=min(max(i,0),1079); j=min(max(j,0),2159)
    t=TOPO
    return t[i,j]*(1-fx)*(1-fy)+t[i,j+1]*fx*(1-fy)+t[i+1,j]*(1-fx)*fy+t[i+1,j+1]*fx*fy
URB=[shape(f['geometry']).buffer(0) for f in json.load(open('ne_10m_urban_areas.geojson'))['features']]
GLAC=[shape(f['geometry']) for f in json.load(open('ne_10m_glaciated_areas.geojson'))['features']]
MTN=[shape(f['geometry']).buffer(0) for f in REG if f['properties']['FEATURECLA'] in('Range/mtn',)]
DES=[shape(f['geometry']).buffer(0) for f in REG if f['properties']['FEATURECLA'] in('Desert',)]
def tree(gs):
    gs=[g for g in gs if not g.is_empty]; return STRtree(gs),gs
TL,LK=tree(LAKES); TU,UR=tree(URB); TL10,LK10=tree(LAKES10); TM,MT=tree(MTN); TD,DS=tree(DES); TG,GL=tree(GLAC)
def inside(t,gs,pt):
    for i in t.query(pt):
        if gs[i].contains(pt): return True
    return False

def country(a3):
    for f in C:
        if f['properties']['ADM0_A3']==a3: return shape(f['geometry']).buffer(0)
    raise Exception(a3)

# terrain classes: 0 coast/border 1 forest 2 farmland 3 water 4 city 5 mountain 6 desert
def build(L):
    rng=random.Random(L['seed'])
    if L['kind']=='boss':
        clip=box(*L['bbox'])
        parts=[]
        for f in C:
            p=f['properties']
            if p['CONTINENT'] in L['continents'] or p['ADM0_A3'] in L.get('extra',[]):
                if p['ADM0_A3'] in L.get('exclude',[]): continue
                g=shape(f['geometry']).buffer(0).intersection(clip)
                if not g.is_empty and g.area>0.3: parts.append((p['ADM0_A3'],g))
    else:
        base=country(L['a3'])
        if 'bbox' in L: base=base.intersection(box(*L['bbox']))
        parts=[(L['a3'],base)]

    geoms=[g for _,g in parts]; allg=unary_union(geoms)
    minx,miny,maxx,maxy=allg.bounds
    if 'bbox' in L and L['kind']!='boss': minx,miny,maxx,maxy=L['bbox']
    k=math.cos(math.radians((miny+maxy)/2))
    preps=[(a,prep(g)) for a,g in parts]; ptree=STRtree([g for _,g in parts])
    def raster(GW):
        cell=(maxx-minx)*k/GW; GH=max(1,round((maxy-miny)/cell))
        own=[-1]*(GW*GH)
        for j in range(GH):
            for i in range(GW):
                pt=Point(minx+(i+.5)*cell/k, maxy-(j+.5)*cell)
                for ci in ptree.query(pt):
                    if preps[ci][1].contains(pt): own[j*GW+i]=int(ci); break
        return GW,GH,cell,own
    GW=40
    for _ in range(3):
        GW,GH,cell,own=raster(GW)
        n=sum(1 for v in own if v>=0)
        GW=max(12,round(GW*math.sqrt(L['target']/max(n,1))))
        GH2=GW*(maxy-miny)/((maxx-minx)*k)
        if max(GW,GH2)>L.get('maxdim',92): GW=round(GW*L.get('maxdim',92)/max(GW,GH2))
    GW,GH,cell,own=raster(GW)
    ll=lambda i,j:(minx+(i+.5)*cell/k, maxy-(j+.5)*cell)
    # noise
    def mknoise(scale):
        nx=int(GW/scale)+3; ny=int(GH/scale)+3; lat=[rng.random() for _ in range(nx*ny)]
        sm=lambda t:t*t*(3-2*t)
        def f(i,j):
            x=i/scale;y=j/scale;x0=int(x);y0=int(y);fx=sm(x-x0);fy=sm(y-y0);v=lambda a,b:lat[b*nx+a]
            return v(x0,y0)*(1-fx)*(1-fy)+v(x0+1,y0)*fx*(1-fy)+v(x0,y0+1)*(1-fx)*fy+v(x0+1,y0+1)*fx*fy
        return f
    T=L['terrain']
    # patch: <1 gives smaller forest/farmland patches (more natural boundaries between colours)
    sc=max(3,GW/14)*T.get('patch',1); n1=mknoise(sc); n2=mknoise(sc*.45); n3=mknoise(sc*1.3)
    # extra noise fields use their own rng so that switching them on leaves the rest of the map unchanged
    rng2=random.Random(L['seed']+99)
    def mknoise2(scale):
        nx=int(GW/scale)+3; ny=int(GH/scale)+3; lat=[rng2.random() for _ in range(nx*ny)]
        sm=lambda t:t*t*(3-2*t)
        def f(i,j):
            x=i/scale;y=j/scale;x0=int(x);y0=int(y);fx=sm(x-x0);fy=sm(y-y0);v=lambda a,b:lat[b*nx+a]
            return v(x0,y0)*(1-fx)*(1-fy)+v(x0+1,y0)*fx*(1-fy)+v(x0,y0+1)*(1-fx)*fy+v(x0+1,y0+1)*fx*fy
        return f
    nh=mknoise2(sc*T.get('hedge_scale',1.6)); nh2=mknoise2(sc*T.get('hedge_scale',1.6)*0.8); no=mknoise2(max(1.5,sc*0.35))
    # distance to coast (bfs)
    from collections import deque
    dist=[-1]*(GW*GH); dq=deque()
    for id in range(GW*GH):
        if own[id]<0: continue
        i,j=id%GW,id//GW
        for a,b in((1,0),(-1,0),(0,1),(0,-1)):
            x,y=i+a,j+b
            if x<0 or y<0 or x>=GW or y>=GH or own[y*GW+x]<0: dist[id]=0;dq.append(id);break
    while dq:
        id=dq.popleft();i,j=id%GW,id//GW
        for a,b in((1,0),(-1,0),(0,1),(0,-1)):
            x,y=i+a,j+b
            if 0<=x<GW and 0<=y<GH and own[y*GW+x]>=0 and dist[y*GW+x]<0: dist[y*GW+x]=dist[id]+1;dq.append(y*GW+x)
    maxd=max(dist) or 1
    g=[-1]*(GW*GH)
    for id in range(GW*GH):
        if own[id]<0: continue
        i,j=id%GW,id//GW; lon,lat=ll(i,j); pt=Point(lon,lat)
        e=elev(lon,lat); h=cell/k/3
        emax=max(e,*(elev(lon+a,lat+b) for a,b in((h,h),(-h,h),(h,-h),(-h,-h))))
        ctx=dict(lat=lat,lon=lon,d=dist[id]/maxd,dc=dist[id],a=n1(i,j)*0.7+n2(i,j)*0.3-T.get('forest_bias',0),b=n2(i,j),c=n3(i,j),e=e)
        c=None
        if inside(TG,GL,pt) or emax>=T.get('white_m',2500): c=7
        elif e>=T.get('mtn_m',1000): c=5
        elif T.get('des',True) and inside(TD,DS,pt) and ctx['b']>0.15: c=6
        if c is None:
            c=T['fn'](ctx)
            # hedge: forest belts winding through farmland (isolines of smooth noise), natural field boundaries
            hw=T.get('hedge',0)
            if c==2 and hw and (abs(nh(i,j)-0.5)<hw or abs(nh2(i,j)-0.5)<hw*T.get('hedge2',0)): c=1
        # oasis: small farmland spots inside desert
        if c==6 and no(i,j)<T.get('oasis',0): c=2
        if inside(TL,LK,pt) or (L['kind']!='boss' and inside(TL10,LK10,pt)): c=3
        g[id]=c
    # rivers
    rivcells=set()
    for f in (RIV if L['kind']=='boss' else RIV10):
        if (f['properties'].get('scalerank') or 99)>T.get('river_rank',6 if L['kind']=='boss' else 9): continue
        if f['geometry'] is None: continue
        geom=shape(f['geometry'])
        lines=[geom] if geom.geom_type=='LineString' else list(geom.geoms)
        for ln in lines:
            if not ln.intersects(allg): continue
            Lg=ln.length; steps=max(2,int(Lg/(cell/k*0.4)))
            for s in range(steps+1):
                p=ln.interpolate(s/steps,normalized=True)
                i=int((p.x-minx)*k/cell); j=int((maxy-p.y)/cell)
                if 0<=i<GW and 0<=j<GH and g[j*GW+i]>=0:
                    if T.get('nile'):
                        for a in(-1,0,1):
                            for b in(-1,0,1):
                                x,y=i+a,j+b
                                if 0<=x<GW and 0<=y<GH and g[y*GW+x] in(6,1): g[y*GW+x]=2
                    g[j*GW+i]=3; rivcells.add(j*GW+i)
    # riparian: forest strips along river banks where the river runs through farmland
    if T.get('riparian'):
        for id in list(rivcells):
            i,j=id%GW,id//GW
            for a,b in((1,0),(-1,0),(0,1),(0,-1)):
                x,y=i+a,j+b
                if 0<=x<GW and 0<=y<GH and g[y*GW+x]==2 and rng2.random()<T['riparian']: g[y*GW+x]=1
    # river towns: real towns sitting on a river become city cells that cut the river
    if T.get('river_towns'):
        towns=sorted([f['properties'] for f in (PP if L['kind']=='boss' else PP10) if f['properties']['adm0_a3'] in set(a for a,_ in parts)],key=lambda p:-p['pop_max'])
        done=0
        for p in towns:
            if done>=T['river_towns']: break
            i=int((p['longitude']-minx)*k/cell); j=int((maxy-p['latitude'])/cell)
            near=[(x,y) for x in range(i-1,i+2) for y in range(j-1,j+2) if 0<=x<GW and 0<=y<GH and y*GW+x in rivcells and g[y*GW+x]==3]
            if near:
                x,y=near[0]; g[y*GW+x]=4; done+=1
    # metropolitan areas
    if T.get('urban',True):
        for id in range(GW*GH):
            if g[id]<0 or g[id]==3: continue
            i,j=id%GW,id//GW; lon,lat=ll(i,j); cb=box(lon-cell/k/2,lat-cell/2,lon+cell/k/2,lat+cell/2)
            a=0
            for q in TU.query(cb):
                if UR[q].intersects(cb): a+=UR[q].intersection(cb).area
            if a>T.get('urban_frac',0.2)*cb.area: g[id]=4
    # borders
    land=own
    for id in range(GW*GH):
        if land[id]<0 or g[id]==3: continue
        i,j=id%GW,id//GW
        for a,b in((1,0),(-1,0),(0,1),(0,-1)):
            x,y=i+a,j+b
            if x<0 or y<0 or x>=GW or y>=GH or land[y*GW+x]<0: g[id]=0;break
            if (a,b) in((1,0),(0,1)) and land[y*GW+x]!=land[id] and g[y*GW+x]!=3: g[id]=0;break
    # cities
    a3s=set(a for a,_ in parts)
    pl=sorted([f['properties'] for f in (PP if L['kind']=='boss' else PP10) if f['properties']['adm0_a3'] in ([L['a3']] if L['kind']!='boss' else a3s)],key=lambda p:-p['pop_max'])
    ncity=max(L.get('cities',5),GW//5) if L['kind']!='boss' else L.get('cities',16); placed=0; taken=set()
    for p in pl:
        if placed>=ncity: break
        i=int((p['longitude']-minx)*k/cell); j=int((maxy-p['latitude'])/cell)
        if not(0<=i<GW and 0<=j<GH) or (i,j) in taken: continue
        if any(abs(i-a)+abs(j-b)<3 for a,b in taken): continue
        sz=2 if placed<2 and L['kind']!='boss' else 1
        ok=False
        for a in range(sz):
            for b in range(sz):
                x,y=i+a,j+b
                if 0<=x<GW and 0<=y<GH and g[y*GW+x]>=0: g[y*GW+x]=4; ok=True
        if ok: taken.add((i,j)); placed+=1
    return GW,GH,g,own

NB=((1,0),(-1,0),(0,1),(0,-1))
SLOTS=5  # must match the 5 slots in index.html
NCOL=8   # colour classes, must match COLORS in index.html
class Sim:
    """Deterministic eating model shared with the game: per colour, ants eat the exposed cell
    nearest the bottom centre of the map (squared distance, ties by cell index). Same key as LK in index.html."""
    def __init__(s,g,GW,GH):
        s.g=g[:];s.GW=GW;s.GH=GH;s.q=[[] for _ in range(NCOL)];s.exp=bytearray(len(g));s.left=0
        N=len(g); s.key=[((2*(id%GW)+1-GW)**2+(2*GH-2*(id//GW)-1)**2)*N+id for id in range(N)]
        for id,v in enumerate(s.g):
            if v>=0:
                s.left+=1
                if s.isexp(id): s.exp[id]=1; heapq.heappush(s.q[v],(s.key[id],id))
    def isexp(s,id):
        i,j=id%s.GW,id//s.GW
        for a,b in NB:
            x,y=i+a,j+b
            if x<0 or y<0 or x>=s.GW or y>=s.GH or s.g[y*s.GW+x]<0: return True
        return False
    def avail(s,c): return len(s.q[c])
    def pop(s,c):
        id=heapq.heappop(s.q[c])[1]; s.eat(id); return id
    def eat(s,id):
        s.g[id]=-1;s.left-=1
        i,j=id%s.GW,id//s.GW
        for a,b in NB:
            x,y=i+a,j+b
            if 0<=x<s.GW and 0<=y<s.GH:
                n=y*s.GW+x
                if s.g[n]>=0 and not s.exp[n]: s.exp[n]=1; heapq.heappush(s.q[s.g[n]],(s.key[n],n))

def gen_trays(g,GW,GH,D,rng):
    s=Sim(g,GW,GH);seq=[];last=-1
    while s.left>0:
        cand=[(c,min(s.avail(c),25)*(0.25 if c==last else 1)) for c in range(NCOL) if s.avail(c)]
        r=rng.random()*sum(w for _,w in cand); c=cand[0][0]
        for cc,w in cand:
            r-=w
            if r<=0: c=cc;break
        target=rng.randint(D['cmin'],D['cmax'])
        cells=[]
        while len(cells)<target and s.avail(c):
            cells.append(s.pop(c))
        if seq and seq[-1]['c']==c and len(seq[-1]['cells'])+len(cells)<=D['cmax']: seq[-1]['cells']+=cells
        else: seq.append({'c':c,'cells':cells})
        last=c
    # split very small trailing? fine
    return seq


def playout(g,GW,GH,cols,keymap,rng,pgood,record=None):
    s=Sim(g,GW,GH); cs=[list(c) for c in cols]; slots=[]; unlocked=set()
    while True:
        prog=True
        while prog:
            prog=False
            for sl in slots:
                while sl[1]>0 and s.avail(sl[0]):
                    p=s.pop(sl[0]); sl[1]-=1; prog=True
                    if p in keymap: unlocked.add(keymap[p])
            slots=[x for x in slots if x[1]>0]
        if s.left==0: return True
        free=SLOTS-len(slots)
        if free<=0: return False
        tops={k:cs[k][0] for k in range(len(cs)) if cs[k]}
        def ok(k):
            tr=tops[k]
            if tr[2]>=0 and tr[2] not in unlocked: return False
            if tr[3]>=0:
                if free<2: return False
                return any(kk!=k and tops[kk][3]==tr[3] for kk in tops)
            return True
        cand=[k for k in tops if ok(k)]
        if not cand: return False
        good=[k for k in cand if s.avail(tops[k][0])]
        pick=rng.choice(good) if good and rng.random()<pgood else rng.choice(cand)
        if record is not None: record.append(pick)
        tr=cs[pick].pop(0); slots.append([tr[0],tr[1]])
        if tr[3]>=0:
            for kk in sorted(tops):
                if kk!=pick and tops[kk][3]==tr[3]:
                    t2=cs[kk].pop(0); slots.append([t2[0],t2[1]]); break

def solve(g,GW,GH,cols,keys,rng,tries=200,pgood=0.93):
    km={k['cell']:k['lock'] for k in keys}
    for _ in range(tries):
        rec=[]
        if playout(g,GW,GH,cols,km,rng,pgood,rec): return rec
    return None
LOCK_GAP=4       # padlocks at least this many trays apart (solution order and within a column)
LOCK_MIN_ROW=3   # no padlock in the rows visible at the start (portrait and landscape both show 3)
BOT_MIN=0.05     # naive bot must win at least 3 of 60 games
def bot_rate(g,GW,GH,cols,keys,rng,n=60):
    km={k['cell']:k['lock'] for k in keys}
    return sum(playout(g,GW,GH,cols,km,rng,0.8) for _ in range(n))/n


def make_fog(g,own,GW,GH,D,rng,keys):
    hidden=[0]*len(g)
    land=[i for i,v in enumerate(g) if v>=0]
    if D['hidden']<=0: return hidden
    target=D['hidden']*len(land); count=0
    kinds=D.get('fog',['band','blob','region'])
    big=min(max(GW,GH),math.sqrt(len(land))*1.3); guard=0
    while count<target*0.85 and guard<120:
        guard+=1
        kind=rng.choice(kinds); cells=[]
        if kind=='band':
            th=rng.uniform(0.07,0.12)*big; ang=rng.uniform(0,math.pi)
            c=rng.choice(land); cx,cy=c%GW,c//GW; nx,ny=-math.sin(ang),math.cos(ang)
            wob=rng.uniform(0,6.28)
            for id in land:
                x,y=id%GW,id//GW; along=(x-cx)*math.cos(ang)+(y-cy)*math.sin(ang)
                if abs((x-cx)*nx+(y-cy)*ny + math.sin(along*0.15+wob)*th*0.35)<th/2: cells.append(id)
        elif kind=='blob':
            r=rng.uniform(0.1,0.18)*big; c=rng.choice(land); cx,cy=c%GW,c//GW; ph=[rng.uniform(0,6.28) for _ in range(3)]
            for id in land:
                x,y=id%GW,id//GW; a=math.atan2(y-cy,x-cx)
                rr=r*(1+0.25*math.sin(3*a+ph[0])+0.15*math.sin(5*a+ph[1]))
                if (x-cx)**2+(y-cy)**2<rr*rr: cells.append(id)
        else:
            regs=list(set(own[i] for i in land))
            if len(regs)<3: continue
            rid=rng.choice(regs); cells=[i for i in land if own[i]==rid]
            if len(cells)>0.25*len(land): continue
        new=[id for id in cells if not hidden[id]]
        if count+len(new)>target*1.15 and count>0: continue
        if len(new)>target*1.15: continue
        for id in new: hidden[id]=1; count+=1
    for k in keys: hidden[k['cell']]=0
    return hidden

def layout(g,GW,GH,D,rng):
    seq=gen_trays(g,GW,GH,D,rng); n=len(seq)
    keys=[];locks={};ties={}
    if D['locks']:
        # Siim's rules: padlocks never come in sequence (at least LOCK_GAP trays apart in solution order)
        idxs=list(range(6,n)); rng.shuffle(idxs); picked=[]
        for p in idxs:
            if len(picked)>=D['locks']: break
            if all(abs(p-q)>=LOCK_GAP for q in picked): picked.append(p)
        for li,p in enumerate(sorted(picked)):
            mode=D.get('key_mode','random')
            if mode=='random':
                src=rng.randint(max(0,p-8),p-2)
                cells=[x for x in seq[src]['cells'] if g[x]!=0] or seq[src]['cells']
                kc=rng.choice(cells)
            else:
                # 'rare': key in the chunk of the rarest colour within key_back colonies before the padlock;
                # 'far': random chunk as usual. Both put the key on the chunk's last-eaten cell, the one
                # farthest along its colour's eating order, so the colony that gets it must be timed.
                win=range(max(0,p-D.get('key_back',8)),p-1)
                if mode=='rare':
                    total=lambda c:g.count(c) if c!=0 else 10**9
                    src=min(win,key=lambda q:(total(seq[q]['c']),-q))
                else: src=rng.choice(list(win))
                cells=[x for x in seq[src]['cells'] if g[x]!=0] or seq[src]['cells']
                kc=cells[-1]
            keys.append({'cell':kc,'lock':li}); locks[p]=li
    tid=0; tries=0
    while tid<D['ties'] and tries<300:
        tries+=1
        i=rng.randint(3,n-4); j=i+rng.randint(*D.get('tie_span',(1,3)))  # partners 1-3 apart in solution order
        if j>=n or i in locks or j in locks or i in ties or j in ties: continue
        # no tied colonies straight after a padlock
        if any(0<i-p<=2 or 0<j-p<=2 for p in locks): continue
        if seq[i]['c']==seq[j]['c']: continue
        ties[i]=tid; ties[j]=tid; tid+=1
    for _try in range(80):
        order=sorted(range(n),key=lambda i:i+rng.random()*D['w'])
        ncol=D['cols'];cols=[[] for _ in range(ncol)]; colof={}; rowof={}
        for r,i in enumerate(order):
            lens=[len(c) for c in cols]; opts=list(range(ncol)); forced=False
            if i in ties:
                partner=[q for q in ties if ties[q]==ties[i] and q!=i][0]
                if partner in colof:
                    opts=[k for k in opts if abs(k-colof[partner])==1]
                    rmin,rmax=D.get('tie_rows',(0,5))  # row distance between partners (Siim: at most 5)
                    near=[k for k in opts if rmin<=abs(lens[k]-rowof[partner])<=rmax]
                    if near: opts=near; forced=rmin>0
            if forced: k=rng.choice(opts)  # a minimum partner depth wins over keeping columns even
            else: m=min(lens[k] for k in opts); o2=[k for k in opts if lens[k]<=m+1]; k=rng.choice(o2)
            rowof[i]=len(cols[k])
            cols[k].append([seq[i]['c'],len(seq[i]['cells']),locks.get(i,-1),ties.get(i,-1)]); colof[i]=k
        rmin,rmax=D.get('tie_rows',(0,5))
        okk=all(rmin<=abs(rowof[a]-rowof[b])<=rmax and abs(colof[a]-colof[b])==1 for a in ties for b in ties if a<b and ties[a]==ties[b])
        # padlock rules as seen on screen: not in the rows visible at the start, never two in a row
        # in one column, and the two colonies under a padlock are not tied
        for p in locks:
            col=cols[colof[p]]; r=rowof[p]
            if r<LOCK_MIN_ROW: okk=False
            if any(t[2]>=0 for t in col[max(0,r-LOCK_GAP+1):r]): okk=False
            if any(t[3]>=0 for t in col[r+1:r+3]): okk=False
        if okk: break
    else:
        return None,None
    return cols,keys

def make_level(L,D,target):
    GW,GH,g,own=build(L)
    D0=dict(D); D=dict(D); best=None; att=0
    # per-level tuning from levels.py (tune=...): longer search and rare-colour keys when too easy.
    # Levels without `tune` build exactly as before.
    tune=L.get('tune',{})
    for rnd in range(tune.get('rounds',10)):
        for c in range(tune.get('cands',20)):
            att+=1; rng=random.Random(L['seed']*1000+att)
            cols,keys=layout(g,GW,GH,D,rng)
            if cols is None: continue
            p=bot_rate(g,GW,GH,cols,keys,rng,n=tune.get('bot_games',60))  # more games = less luck in picking
            if p<BOT_MIN: continue  # the naive bot must win sometimes, a solver-only win is not enough
            if best is not None and abs(p-target)>=best[0]: continue
            sol=solve(g,GW,GH,cols,keys,rng)
            if sol is None: continue
            best=(abs(p-target),p,cols,keys,dict(D),sol)
        if best and abs(best[1]-target)<=tune.get('tol',0.1): break
        if best is None or best[1]<target-0.1:
            D['w']=max(0,D['w']-2)
            if D['ties']>1: D['ties']-=1
            if D['locks']>1: D['locks']-=1
        else:
            # harder: more shuffling and ties, but never more padlocks than the level's base number
            D['w']+=2.5
            if D['ties']>0: D['ties']=min(D0['ties']+2,D['ties']+1)
            # the strongest fair lever found: put padlock keys on a rare colour (see CLAUDE.md)
            if tune.get('rare_keys') and D['locks']>0 and D.get('key_mode','random')=='random':
                D['key_mode']='rare'; D['key_back']=12
    if best is None: raise Exception('unsolvable '+L['name'])
    _,p,cols,keys,D,sol=best
    hidden=make_fog(g,own,GW,GH,D,random.Random(L['seed']+5),keys)
    cells=''.join('.' if v<0 else str(v) for v in g)
    return {'name':L['name'],'kind':L['kind'],'GW':GW,'GH':GH,'cells':cells,'hidden':''.join(map(str,hidden)),
            'keys':keys,'cols':cols,'fact':L['fact'],'intro':L.get('intro',''),'spawn':D['spawn'],'colors':sorted(set(v for v in g if v>=0)),'D':D,'attempt':att,'p':p,'sol':sol}
