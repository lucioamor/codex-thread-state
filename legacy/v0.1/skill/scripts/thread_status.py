"""Read-only title proposals from Codex tool snapshots. Python 3, no dependencies."""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ICONS = {'running':'🔵', 'usage_limited':'🚩', 'budget_limited':'⏳',
         'failed':'🔴', 'blocked':'🔴', 'interrupted':'⏸️', 'paused':'⏸️',
         'pending':'🟡', 'complete':'✅', 'monitoring':'🔁', 'unknown':'⚪'}
LABELS = {'running':'Em execução', 'usage_limited':'Interrompida por limite de uso',
          'budget_limited':'Orçamento do goal esgotado', 'failed':'Falha',
          'blocked':'Bloqueada', 'interrupted':'Interrompida', 'paused':'Pausada',
          'pending':'Pendência declarada', 'complete':'Entrega declarada concluída',
          'monitoring':'Monitoramento recorrente', 'unknown':'Revisão necessária'}

def latest(t):
    return (t.get('turns') or [{}])[0]

def final_text(t):
    return '\n'.join(i.get('text','') for i in latest(t).get('items',[])
                     if i.get('type') == 'agentMessage' and i.get('phase') in ('final_answer','final'))

def fingerprint(t):
    return hashlib.sha256(final_text(t).encode('utf-8')).hexdigest()

def usage_error(error):
    # Only runtime error fields; never user prompts, tool failures, or quoted text.
    message = json.dumps(error, ensure_ascii=False).lower()
    return any(s in message for s in ('hit your usage limit','usage_limit_reached',
               'insufficient_quota','credit balance exhausted','usage limit exceeded'))

def classify(t, goal=None, review=None):
    turn = latest(t)
    state, reason, source = 'unknown', 'Sem evidência suficiente de conclusão.', 'conservative'
    valid_review = (review and review.get('turnId') == turn.get('id')
                    and review.get('finalSha256') == fingerprint(t))
    warnings = []
    if review and not valid_review:
        warnings.append('Revisão semântica antiga ignorada: turno/texto mudou.')
    has_goal = bool(goal) or bool(valid_review and review.get('goalEvidence'))
    if goal and goal['updated_at_ms'] < (turn.get('startedAt') or 0)*1000:
        warnings.append('Goal persistido anterior ao último turno: '+goal['status'])
        current_goal = None
    else:
        current_goal = goal
    if t.get('status') == 'active' or turn.get('status') == 'inProgress':
        state, reason, source = 'running', 'Turno em execução no snapshot.', 'runtime'
    elif turn.get('status') == 'failed':
        state = 'usage_limited' if usage_error(turn.get('error')) else 'failed'
        reason, source = str((turn.get('error') or {}).get('message','Turno falhou.')), 'runtime'
    elif turn.get('status') in ('interrupted','cancelled'):
        state, reason, source = 'interrupted', 'Turno interrompido; causa não presumida.', 'runtime'
    elif current_goal and current_goal['status'] != 'complete':
        state = current_goal['status']
        if state == 'active': state = 'pending'
        if state not in ICONS: state = 'unknown'
        reason, source = 'Estado formal atual do goal: '+current_goal['status'], 'goal'
    elif valid_review:
        state, reason, source = review['state'], review['reason'], 'semantic_review'
    elif current_goal and current_goal['status'] == 'complete':
        state, reason, source = 'complete', 'Goal formal marcado complete.', 'goal'
    project = review.get('project') if valid_review else None
    return {'state':state, 'reason':reason, 'source':source, 'goal':has_goal,
            'project':project, 'warnings':warnings,
            'historyUsageErrors':sum(usage_error(x.get('error')) for x in t.get('turns',[])[1:])}

def title_for(title, state, goal=False, project=None):
    # Recognized status-prefix convention only; preserve existing [project] and wording.
    body = title
    tokens = sorted(set(ICONS.values()) | {'🏁'},key=len,reverse=True)
    prefix = re.compile(r'^(?:'+ '|'.join(map(re.escape,tokens)) +r')\s+')
    while prefix.match(body): body = prefix.sub('',body,count=1)
    if project and not re.match(r'^\[[^\]]+\]', body): body = '['+project+'] '+body
    return ICONS[state]+' '+('🏁 ' if goal else '')+body

def propose(threads, goals, reviews):
    rows=[]
    for t in threads:
        result=classify(t,goals.get(t['id']),reviews.get(t['id']))
        invalid_title=bool(re.search(r'[\x00-\x1f]',t['title']))
        if invalid_title: result['warnings'].append('Título recebido contém caractere de controle; revisão manual obrigatória.')
        proposed=title_for(t['title'],result['state'],result['goal'],result['project'])
        over_limit=len(t['title'])>60 or len(proposed)>60
        if over_limit: result['warnings'].append('Título excede o limite observado de 60 caracteres; mutação não é reversível pela API suportada.')
        rows.append({'id':t['id'],'turnId':latest(t).get('id'),'oldTitle':t['title'],
                     'proposedTitle':proposed,
                     'observedThreadStatus':t.get('status'),
                     'applyEligible':not invalid_title and not over_limit and result['state']!='unknown', **result})
    return rows

def cell(s):
    return str(s).replace('\x00','[NUL]').replace('|','\\|').replace('\n',' ')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot',type=Path,default=Path(__file__).with_name('snapshot.json'))
    p.add_argument('--evidence',type=Path,default=Path(__file__).with_name('evidence.json'))
    p.add_argument('--out',type=Path,default=Path(__file__).parent)
    a=p.parse_args()
    threads=json.loads(a.snapshot.read_text(encoding='utf-8'))
    evidence=json.loads(a.evidence.read_text(encoding='utf-8'))
    rows=propose(threads,evidence.get('goals',{}),evidence.get('reviews',{}))
    counts=Counter(r['state'] for r in rows)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'proposals.json').write_text(json.dumps({'dryRun':True,'counts':counts,'threads':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Simulação dos títulos — 30 conversas Codex', '',
      'Snapshot de 28/09/2026. Nenhum título foi alterado. Seleção: 30 conversas Codex não arquivadas devolvidas por list_threads, ordenadas por updatedAt. ChatGPT excluído.', '',
      'Leitura: último turno de cada conversa; nesta conversa, dois turnos para registrar a interrupção e a retomada. Goals consultados em SQLite somente leitura. Não é auditoria integral dos projetos.', '',
      '✅ significa conclusão declarada da entrega/escopo, não validação independente. 🟡 pode incluir ressalvas ainda abertas mesmo quando a implementação foi entregue. ⚪ exige mais contexto. Prefixos de projeto adicionados são sugestões editoriais baseadas nos caminhos e conteúdos observados.', '',
      'A revisão semântica foi feita nesta execução e fica vinculada ao ID do turno e SHA-256 da resposta final. O script não inventa uma classificação semântica para novos turnos.', '',
      'Contagem: '+', '.join(f'{ICONS[k]} {LABELS[k]}: {v}' for k,v in counts.items()), '',
      '| # | Título atual | Proposta | Evidência / ressalva |','|---|---|---|---|']
    for n,r in enumerate(rows,1):
        detail=r['reason']+' Fonte: '+r['source']+'. '+ '; '.join(r['warnings'])
        if r['historyUsageErrors']: detail+=' Interrupção anterior por limite de uso confirmada; retomada atual prevalece.'
        lines.append(f"| {n} | {cell(r['oldTitle'])} | {cell(r['proposedTitle'])} | {cell(detail)} |")
    lines += ['', 'A regra não reescreve títulos truncados nem corrige NUL por suposição. O JSON preserva título original, proposta, ID e evidência para revisão e eventual reversão.', '',
              'Casos sintéticos para estados ausentes: 🚩 🏁 [cue] Tarefa = limite de uso; ⏳ 🏁 [cue] Tarefa = orçamento do goal; ✅ 🏁 [cue] Tarefa = goal concluído.']
    (a.out/'dry-run.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'threads':len(rows),'counts':counts,'mutations':0},ensure_ascii=False))

if __name__=='__main__': main()
