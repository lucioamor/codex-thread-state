import unittest
import daemon

class DaemonRules(unittest.TestCase):
    def test_goal_prompt_is_detected(self):
        class S:
            def call(self, method, params): return {'goal': None}
        goal, flag=daemon.goal_info(S(),{'id':'t','preview':'/goal Execute o plano'})
        self.assertIsNone(goal); self.assertTrue(flag)

    def test_usage_failure_wins(self):
        state, reason=daemon.classify({}, {'status':'failed','error':{'message':'You’ve hit your usage limit'}}, None, True)
        self.assertEqual(state,'usage_limited')

    def test_goal_budget_is_not_usage_limit(self):
        state, reason=daemon.classify({}, {'status':'completed','items':[]}, {'status':'budget_limited'}, True)
        self.assertEqual(state,'budget_limited')

    def test_active_turn_is_blue(self):
        self.assertEqual(daemon.classify({}, {'status':'inProgress'}, None, False)[0],'running')

    def test_completed_turn_default_is_complete(self):
        self.assertEqual(daemon.classify({}, {'status':'completed','items':[]}, None, False)[0],'complete')

    def test_pending_phrase_beats_completed_default(self):
        turn={'status':'completed','items':[{'type':'agentMessage','text':'Falta validar no Chrome.'}]}
        self.assertEqual(daemon.classify({},turn,None,False)[0],'pending')

    def test_discussion_of_missing_product_fields_is_not_task_pending(self):
        text='Faltam campos obrigatórios no produto analisado.\n\nMinha recomendação final compara as duas skills.'
        turn={'status':'completed','items':[{'type':'agentMessage','text':text}]}
        self.assertEqual(daemon.classify({},turn,None,False)[0],'complete')

    def test_title_is_idempotent_and_bounded(self):
        title=daemon.compose('running',True,'jevify','x'*100,60)
        self.assertLessEqual(len(title),60)
        self.assertEqual(daemon.strip_status(title),'[jevify] '+title.split('] ',1)[1])

    def test_git_origin_supplies_project(self):
        t={'name':'Conversa','cwd':'C:/tmp','gitInfo':{'originUrl':'https://github.com/a/MyRepo.git'}}
        self.assertEqual(daemon.project_tag(t,{'projectRoots':{}}),'myrepo')

if __name__=='__main__': unittest.main()
