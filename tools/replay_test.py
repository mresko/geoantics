"""Replays every stored solver solution in the real game engine (headless Chromium).
All levels must end in 'win'. Usage: python3 tools/replay_test.py index.html tools/solutions.json
Needs: pip install playwright && playwright install chromium"""
import json, sys, pathlib
from playwright.sync_api import sync_playwright
html = pathlib.Path(sys.argv[1]).resolve().as_uri()
sols = json.load(open(sys.argv[2]))
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1280, 'height': 800})
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(html); pg.wait_for_timeout(300)
    res = pg.evaluate("""(sols)=>{const out=[];for(let n=0;n<LEVELS.length;n++){startLevel(n);state='play';let bad=0;
      for(const k of sols[n]){let g=0;const t=columns[k][0];const need=t&&t.tie>=0?2:1;
        while(slots.filter(s=>!s).length<need&&g<20000){update(0.03);g++;}
        if(!canTake(k)){bad++;break;} pickColumn(k);}
      let g=0;while(state==='play'&&g<40000){update(0.03);g++;}
      out.push([LEVELS[n].name,state,eatenCount+'/'+total]);}return out;}""", sols)
    ok = True
    for r in res:
        print(r); ok = ok and r[1] == 'win'
    print('page errors:', errs); b.close()
    sys.exit(0 if ok and not errs else 1)
