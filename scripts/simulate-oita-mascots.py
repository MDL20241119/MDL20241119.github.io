"""Reproduce a fictional vote from explicit subjective assessments. No survey data."""
import json,math,random
from pathlib import Path
file=Path(__file__).resolve().parents[1]/'oita-mirai-mobility-consortium/mascots/simulation.json'
result=json.loads(file.read_text())
candidates=sorted(result['ranking'],key=lambda c:c['id'])
for c in candidates:c['votes']=0
rng=random.Random(result['seed'])
for profile in result['profiles']:
 weights=[math.exp(sum(a*b for a,b in zip(c['scores'],profile['weights']))/result['temperature']) for c in candidates]
 for i in rng.choices(range(len(candidates)),weights=weights,k=profile['n']):candidates[i]['votes']+=1
ranking=sorted(candidates,key=lambda c:(-c['votes'],c['id']))
for i,c in enumerate(ranking):c['rank']=i+1
result['ranking']=ranking
result['topFive']=[c['id'] for c in ranking[:5]]
assert sum(c['votes'] for c in ranking)==result['virtualVoters']
file.write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({'type':result['type'],'virtualVotes':result['virtualVoters'],'topFive':result['topFive'],'alwaysFeature':result['alwaysFeature']},ensure_ascii=False))
