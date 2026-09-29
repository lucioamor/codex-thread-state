"""Build a safe rollback plan without changing any Codex thread."""
import argparse, json
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--results',type=Path,required=True)
    p.add_argument('--current',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    results=json.loads(a.results.read_text(encoding='utf-8'))['results']
    current=json.loads(a.current.read_text(encoding='utf-8'))
    if isinstance(current,dict): current=current.get('threads',[])
    by_id={t['id']:t for t in current}
    restore=[]; skipped=[]
    for row in results:
        now=by_id.get(row['id'])
        reason=None
        if not now: reason='thread_missing'
        elif now.get('title')!=row.get('actualTitle'): reason='title_changed_after_apply'
        elif not row.get('rollbackFullySupported'): reason='original_exceeds_supported_60_character_limit'
        if reason: skipped.append({'id':row['id'],'reason':reason,'currentTitle':now.get('title') if now else None})
        else: restore.append({'id':row['id'],'fromTitle':row['actualTitle'],'toTitle':row['oldTitle']})
    body={'schemaVersion':1,'mode':'rollback','status':'planned','restore':restore,'skipped':skipped}
    a.out.write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'restorable':len(restore),'skipped':len(skipped),'path':str(a.out)},ensure_ascii=False))

if __name__=='__main__': main()
