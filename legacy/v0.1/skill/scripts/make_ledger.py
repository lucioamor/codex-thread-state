"""Create an immutable apply plan from reviewed proposals and a fresh thread listing."""
import argparse, datetime, hashlib, json
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--proposals',type=Path,required=True)
    p.add_argument('--current',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    proposals=json.loads(a.proposals.read_text(encoding='utf-8'))['threads']
    current=json.loads(a.current.read_text(encoding='utf-8'))
    if isinstance(current,dict): current=current.get('threads',[])
    by_id={t['id']:t for t in current}
    changes=[]; skipped=[]
    for row in proposals:
        now=by_id.get(row['id'])
        reason=None
        if not row.get('applyEligible'): reason='proposal_ineligible'
        elif not now: reason='thread_missing_from_fresh_listing'
        elif now.get('title')!=row['oldTitle']: reason='title_changed_since_review'
        elif row.get('observedThreadStatus') is not None and now.get('status')!=row.get('observedThreadStatus'): reason='thread_status_changed_since_review'
        if reason:
            skipped.append({'id':row['id'],'reason':reason,'reviewedTitle':row['oldTitle'],'currentTitle':now.get('title') if now else None})
        else:
            changes.append({'id':row['id'],'turnId':row.get('turnId'),'oldTitle':row['oldTitle'],
                'appliedTitle':row['proposedTitle'],'state':row['state'],'source':row['source'],'reason':row['reason']})
    body={'schemaVersion':1,'createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'mode':'apply','status':'planned','changes':changes,'skipped':skipped,'results':[],'rollbackResults':[]}
    canonical=json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    body['planSha256']=hashlib.sha256(canonical).hexdigest()
    a.out.write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'planned':len(changes),'skipped':len(skipped),'path':str(a.out)},ensure_ascii=False))

if __name__=='__main__': main()
