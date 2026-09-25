from exam_platform import question_sync

class FakeConnection:
    def __init__(self): self.calls = []
    def execute(self, statement, params=None): self.calls.append((str(statement), params))

class FakeBegin:
    def __init__(self, connection): self.connection = connection
    def __enter__(self): return self.connection
    def __exit__(self, exc_type, exc, tb): return False

class FakeEngine:
    def __init__(self): self.connection = FakeConnection()
    def begin(self): return FakeBegin(self.connection)

def test_sync_question_payload_executes_upsert():
    engine = FakeEngine()
    payload = {'id':'SYNC_TEST_001','subject':'Mathematics','board':'ICSE','class':10,'chapter':'Algebra','topic':None,'subtopic':None,'type':'mcq','mode':'option_selection','difficulty':'medium','competency':'application','content':'[]','choices':'[]','correct':'A','marks':1,'upload':'none','source':'sync-test','year':2026,'status':'active','source_type':'manual','verification_status':'VERIFIED','canonical_question_id':'SYNC_TEST_001'}
    question_sync.sync_question_payload(payload, engine=engine)
    assert len(engine.connection.calls) == 1
    _, params = engine.connection.calls[0]
    assert params['id'] == 'SYNC_TEST_001'
    assert params['canonical_question_id'] == 'SYNC_TEST_001'

def test_sync_question_solution_executes_upsert():
    engine = FakeEngine()
    question_sync.sync_question_solution('SYNC_TEST_001','x = 2','1 mark',verified=True,engine=engine)
    _, params = engine.connection.calls[0]
    assert params['question'] == 'SYNC_TEST_001'
    assert params['verified'] == 1

def test_deactivate_question_targets_secondary_database():
    engine = FakeEngine()
    question_sync.deactivate_question('SYNC_TEST_001', engine=engine)
    _, params = engine.connection.calls[0]
    assert params['id'] == 'SYNC_TEST_001'
