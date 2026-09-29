import copy
import unittest
from thread_status import classify, fingerprint, propose, title_for

def thread(status='completed', text='Resposta encerrada.', error=None):
    return {'id':'t','title':'[cue] Exemplo','status':'idle','turns':[
        {'id':'turn','status':status,'startedAt':200,'error':error,'items':[
            {'type':'agentMessage','phase':'final_answer','text':text}]}]}

class StatusTests(unittest.TestCase):
    def test_completed_turn_is_not_completed_task(self):
        self.assertEqual(classify(thread())['state'],'unknown')
    def test_structured_usage_error(self):
        self.assertEqual(classify(thread('failed',error={'message':'You’ve hit your usage limit.'}))['state'],'usage_limited')
    def test_usage_words_in_final_are_not_runtime_error(self):
        self.assertEqual(classify(thread(text='Exemplo: You’ve hit your usage limit.'))['state'],'unknown')
    def test_resumed_turn_wins_over_previous_failure(self):
        t=thread('inProgress'); t['turns'].append(thread('failed',error={'message':'You’ve hit your usage limit.'})['turns'][0])
        result=classify(t)
        self.assertEqual(result['state'],'running'); self.assertEqual(result['historyUsageErrors'],1)
    def test_stale_goal_is_not_current_failure(self):
        result=classify(thread(),{'status':'usage_limited','updated_at_ms':100000})
        self.assertEqual(result['state'],'unknown'); self.assertTrue(result['goal']); self.assertTrue(result['warnings'])
    def test_budget_is_distinct_from_usage(self):
        self.assertEqual(classify(thread(),{'status':'budget_limited','updated_at_ms':300000})['state'],'budget_limited')
    def test_review_bound_to_turn_and_content(self):
        t=thread(); review={'turnId':'turn','finalSha256':fingerprint(t),'state':'complete','reason':'Entregue'}
        self.assertEqual(classify(t,review=review)['state'],'complete')
        newer=copy.deepcopy(t); newer['turns'][0]['id']='new'
        self.assertEqual(classify(newer,review=review)['state'],'unknown')
        newer=thread(text='Ainda não finalizado.')
        self.assertEqual(classify(newer,review=review)['state'],'unknown')
    def test_prefixes_idempotent_and_project_preserved(self):
        title=title_for('[contra] Texto português','pending',True,'cue')
        self.assertEqual(title,'🟡 🏁 [contra] Texto português')
        self.assertEqual(title_for(title,'pending',True,'cue'),title)
        self.assertEqual(title_for(title,'complete',True),'✅ 🏁 [contra] Texto português')
    def test_nul_title_requires_manual_review(self):
        t=thread('inProgress'); t['title']='Título\x00'
        r=propose([t],{}, {})[0]
        self.assertFalse(r['applyEligible']); self.assertEqual(r['oldTitle'],'Título\x00')
    def test_long_title_is_not_reversibly_mutated(self):
        t=thread('inProgress'); t['title']='x'*61
        r=propose([t],{}, {})[0]
        self.assertFalse(r['applyEligible'])
        self.assertTrue(any('60 caracteres' in w for w in r['warnings']))
    def test_generic_failure_not_credit(self):
        self.assertEqual(classify(thread('failed',error={'message':'Network disconnected'}))['state'],'failed')
    def test_interruption_not_inferred_as_credit(self):
        self.assertEqual(classify(thread('interrupted'))['state'],'interrupted')

if __name__=='__main__': unittest.main()
