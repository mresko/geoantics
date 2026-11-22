from build import *
import sys
def mix(x,bias=0.0):
    e=x['e']
    p=0.22 if e<150 else 0.42 if e<450 else 0.72
    return 1 if x['a']<p+bias else 2
def forest(share): return lambda x: 1 if x['a']<share else 2
def italy(x):
    e=x['e']
    p=0.2 if e<120 else 0.5 if e<350 else 0.8
    return 1 if x['a']<p else 2
def egypt(x): return 6
def kenya(x):
    if x['lat']>1.0 and x['e']<900 and x['a']>0.3: return 6
    return 1 if x['a']<(0.45 if x['e']>1700 else 0.2) else 2
def nigeria(x):
    if x['lat']>12.6 and x['a']>0.35: return 6
    share=0.6 if x['lat']<6.8 else 0.2
    return 1 if x['a']<share else 2
def madagascar(x):
    share=0.7 if x['lon']>48.2 else 0.25
    return 1 if x['a']<share else 2
def iceland(x): return 2 if x['a']<0.7 else 1
def japan(x): return mix(x,0.2)
def srilanka(x): return mix(x,0.25)
def mongolia(x):
    if x['lat']<45 and x['a']>0.25: return 6
    if x['lat']>48.5 and x['a']<0.4: return 1
    return 2
def india(x):
    return 1 if x['a']<(0.45 if x['e']>500 else 0.15) else 2
def europe(x):
    return mix(x,0.15 if x['lat']>57 else -0.05)
def africa(x):
    lat=x['lat']
    if 16<lat<31 and x['a']>0.12: return 6
    if -28<lat<-17 and x['lon']<25 and x['a']>0.55: return 6
    share=0.7 if -5<lat<6 else 0.25
    return 1 if x['a']<share else 2
def asia(x):
    lat=x['lat']
    if 50<lat<=72: return 1 if x['a']<0.7 else 2
    if 22<lat<47 and 40<x['lon']<110 and x['a']>0.55: return 6
    if lat<12: return 1 if x['a']<0.6 else 2
    return mix(x,-0.1)

LEVELS=[
 dict(name='Estonia',a3='EST',kind='country',target=1300,terrain=dict(fn=forest(0.5),des=False,mtn_m=9999),
      fact='About half of Estonia is forest, and it has more than 2,000 islands. Saaremaa, in the southwest, is the biggest.',
      intro='Tap a colony to send its ants out. They eat blocks of their own colour, starting from the edges. Rivers and mountain ranges split the map into pockets.'),
 dict(name='Finland',a3='FIN',kind='country',target=1500,terrain=dict(fn=forest(0.72),des=False,mtn_m=9999),
      fact='Finland has around 188,000 lakes, and roughly three quarters of the country is forest.',
      intro='Fog. Purple areas hide what lies underneath. Use what you know about the country to guess which colours you will need.'),
 dict(name='Italy',a3='ITA',kind='country',group='region',target=1700,terrain=dict(fn=italy,mtn_m=720,urban_frac=0.3),cities=9,
      fact='Two whole countries sit inside Italy: San Marino and Vatican City.',
      intro='Keys and padlocks. Eat the block with the golden key to open a locked colony.'),
 dict(name='Iceland',a3='ISL',kind='country',target=1800,terrain=dict(fn=iceland,mtn_m=650),cities=5,
      fact='About a tenth of Iceland is covered by glaciers. Vatnajökull is one of the largest ice caps in Europe.',
      intro='Tied colonies. Two colonies with the same chain badge sit in neighbouring columns and only move together, when both are on top and two slots are free.'),
 dict(name='Europe',kind='boss',continents=['Europe'],bbox=(-25,34,45,71.5),exclude=[],target=2600,
      terrain=dict(fn=europe,mtn_m=1100,river_rank=4,urban=False),cities=16,
      fact='Europe is home to the Vatican, the smallest country in the world, and part of Russia, the largest.',
      intro='Boss level! A whole continent, with every country border to chew through.'),
 dict(name='Egypt',a3='EGY',kind='country',target=1900,terrain=dict(fn=egypt,nile=True,des=False,river_rank=9,mtn_m=900),cities=7,
      fact='Almost all Egyptians live along the Nile valley and delta, on just a few percent of the land.',
      intro='The desert hides a lot. Most of the life is along one river.'),
 dict(name='Kenya',a3='KEN',kind='country',target=2000,terrain=dict(fn=kenya,mtn_m=1900),cities=7,
      fact='The equator runs right through Kenya, yet Mount Kenya near it still has glaciers.',intro='More fog, more locks. Plan two or three moves ahead.'),
 dict(name='Nigeria',a3='NGA',kind='country',target=2100,terrain=dict(fn=nigeria,mtn_m=900),cities=9,
      fact='Nigeria has the largest population in Africa, over 200 million people.',intro='Colonies are shuffled harder from here on.'),
 dict(name='Madagascar',a3='MDG',kind='country',target=2200,terrain=dict(fn=madagascar,mtn_m=1450),cities=6,
      fact='Around 90% of the plants and animals on Madagascar live nowhere else on Earth, lemurs included.',intro='Two tied pairs on one island. Keep slots free for them.'),
 dict(name='Africa',kind='boss',continents=['Africa'],bbox=(-26,-36,60,38),exclude=[],target=2900,
      terrain=dict(fn=africa,river_rank=3,mtn_m=1700,urban=False),cities=18,
      fact='Africa has 54 countries, and the Sahara is the largest hot desert in the world.',
      intro='Boss level! Fifty-four countries, one very big puzzle.'),
 dict(name='Japan',a3='JPN',kind='country',target=2200,bbox=(128.5,30.5,146,45.7),terrain=dict(fn=japan,mtn_m=1000),cities=9,
      fact='A 2023 recount found that Japan is made up of over 14,000 islands.',intro='Mountains everywhere, squeezed between two seas.'),
 dict(name='Sri Lanka',a3='LKA',kind='country',group='region',target=2300,terrain=dict(fn=srilanka,mtn_m=800),cities=6,
      fact='Sri Lanka is one of the world\u2019s biggest tea exporters, grown mostly in its central highlands.',intro='Small island, big puzzle. Watch the central highlands.'),
 dict(name='Mongolia',a3='MNG',kind='country',target=2400,terrain=dict(fn=mongolia,des=False,mtn_m=1950),cities=6,
      fact='Mongolia is the most sparsely populated country in the world. The Gobi desert covers its south.',intro='Lots of open land, and lots of fog.'),
 dict(name='India',a3='IND',kind='country',target=2500,terrain=dict(fn=india,mtn_m=1400),cities=10,
      fact='India became the most populous country in the world in 2023.',intro='The last country. Everything you have learned, all at once.'),
 dict(name='Asia',kind='boss',continents=['Asia'],extra=['RUS'],bbox=(26,-11,150,77.5),exclude=['IDN','TLS','PHL','MYS','BRN','PNG'],target=3200,
      terrain=dict(fn=asia,river_rank=2,mtn_m=1700,urban=False),cities=20,
      fact='Asia is the largest continent, with about 30% of the world\u2019s land and around 60% of its people.',
      intro='Final boss! The biggest continent of all.'),
]
for i,L in enumerate(LEVELS): L['seed']=101+i*17

def difficulty(n,boss):
    tier=(n-1)//5; pos=(n-1)%5
    D=dict(cols=3 if n==1 else 4,
      w=[1.5,3,4,5,0][pos]+1.5*tier,
      hidden=0 if n==1 else min(0.45,0.22+0.03*pos+0.05*tier),
      locks=0 if n<3 else 1+tier+(1 if pos>=2 else 0),
      ties=0 if n<4 else 1+tier+(1 if pos>=3 else 0),
      cmin=10+2*tier, cmax=32+4*tier, spawn=0.045,
      fog=['band','blob','region'])
    if boss:
        D.update(w=5.5+1.5*tier,locks=2+tier,ties=1+tier,cmin=14+2*tier,cmax=40+2*tier,spawn=0.03,hidden=0.18+0.03*tier)
    return D

TARGET=[0.75,0.5,0.4,0.32,0.25,0.3,0.25,0.2,0.17,0.12,0.15,0.12,0.1,0.08,0.06]

# levels that missed their target bot rate with the plain search (see CLAUDE.md, "What drives difficulty")
TUNE={n:dict(rounds=12,cands=40,rare_keys=True) for n in ('Iceland','Europe','Egypt','Kenya','Sri Lanka')}
for n in ('Iceland','Kenya'): TUNE[n].update(bot_games=150,tol=0.05)  # 60 games picked lucky layouts here (600-game check: 43%, 38%)
for L in LEVELS:
    if L['name'] in TUNE: L['tune']=TUNE[L['name']]

def build_one(n):
    L=LEVELS[n-1]; D=difficulty(n,L['kind']=='boss')
    lv=make_level(L,D,TARGET[n-1])
    cnt=[lv['cells'].count(str(c)) for c in range(8)]
    print(n,L['name'],'p=%.2f'%lv['p'],lv['D']['w'],lv['D']['locks'],lv['D']['ties'],lv['D'].get('key_mode','random'),lv['GW'],lv['GH'],len(lv['cells'])-lv['cells'].count('.'),cnt,'trays',sum(len(c) for c in lv['cols']),'att',lv['attempt'],file=sys.stderr,flush=True)
    return lv

def finish(lv):
    for k in ('D','attempt','p'): del lv[k]
    return lv.pop('sol'),lv

if __name__=='__main__':
    # python3 levels.py            rebuilds all levels
    # python3 levels.py Egypt Kenya  rebuilds only those and merges them into the existing levels.json/solutions.json
    names=sys.argv[1:]
    if names:
        import multiprocessing as mp
        idx=[n for n,L in enumerate(LEVELS,1) if L['name'] in names]
        assert len(idx)==len(names),'unknown level name'
        out=json.load(open('levels.json')); sols=json.load(open('solutions.json'))
        with mp.get_context('fork').Pool(len(idx)) as pool:
            for n,lv in zip(idx,pool.map(build_one,idx)):
                sols[n-1],out[n-1]=finish(lv)
    else:
        res=[finish(build_one(n)) for n in range(1,len(LEVELS)+1)]
        sols=[s for s,_ in res]; out=[l for _,l in res]
    json.dump(sols,open('solutions.json','w'))
    json.dump(out,open('levels.json','w'),separators=(',',':'))
