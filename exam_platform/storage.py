"""Application persistence backed by MySQL via SQLAlchemy."""
import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy import text
from database import engine, initialize_database
from .models import Test, Question, Student, Attempt, Response, AnswerImage, ContentBlock

initialize_database()

class MySQLStorage:
    def __init__(self):
        self.tests, self.questions, self.students = {}, {}, {}
        self.attempts, self.responses, self.images = {}, {}, {}
        self._load_cache()

    @staticmethod
    def _dt(value):
        if not value: return None
        return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))

    def _load_cache(self):
        with engine.connect() as db:
            for r in db.execute(text("SELECT * FROM tests")).mappings():
                self.tests[r['test_id']] = Test(r['test_id'],r['title'],r['subject'],r['class_level'],r['duration_minutes'],r['total_marks'],json.loads(r['questions_json']),r['status'],r['board'],str(r['test_date']) if r['test_date'] else None,r['test_type'])
            for r in db.execute(text("SELECT * FROM questions")).mappings():
                blocks=[ContentBlock(**x) for x in json.loads(r['question_content_json'])]
                self.questions[r['question_id']] = Question(r['question_id'],r['question_type'],r['answer_mode'],blocks,json.loads(r['answer_choices_json']),r['correct_answer'],r['marks'],r['handwritten_upload_mode'],r['subject'],r['board'],r['class_level'],r['chapter'],r['topic'],r['subtopic'],r['difficulty'],r['competency'],r['source'],r['source_year'],r.get('status','active'))
            for r in db.execute(text("SELECT * FROM students")).mappings():
                self.students[r['student_id']] = Student(r['student_id'],r['name'],r['email'],r['phone'],r['city'],r['role'],r['class_level'],r['board'],r['school'],str(r['registration_date']) if r['registration_date'] else None,r['registration_source'],r['status'])
            for r in db.execute(text("SELECT * FROM attempts")).mappings():
                self.attempts[r['attempt_id']] = Attempt(r['attempt_id'],r['student_id'],r['test_id'],self._dt(r['started_at']),self._dt(r['submitted_at']),r['status'],r['score'],r['percentage'],r['attempt_rate'],r['accuracy'],r['time_taken_seconds'])
            for r in db.execute(text("SELECT * FROM responses")).mappings():
                self.responses[r['response_id']] = Response(r['response_id'],r['attempt_id'],r['question_id'],r['selected_answer'],r['answer_status'],r['marks_awarded'],bool(r['is_correct']) if r['is_correct'] is not None else None,self._dt(r['answered_at']))
            for r in db.execute(text("SELECT * FROM answer_images")).mappings():
                self.images[r['image_id']] = AnswerImage(r['image_id'],r['attempt_id'],r['question_id'],r['page_number'],r['original_filename'],r['file_path'],self._dt(r['uploaded_at']))

    def create_test(self,test: Test):
        with engine.begin() as db:
            db.execute(text("""INSERT INTO tests(test_id,title,subject,class_level,board,test_date,duration_minutes,total_marks,test_type,status,questions_json) VALUES(:id,:title,:subject,:class,:board,:date,:duration,:marks,:type,:status,:questions) ON DUPLICATE KEY UPDATE title=VALUES(title),status=VALUES(status),questions_json=VALUES(questions_json),subject=VALUES(subject),class_level=VALUES(class_level),board=VALUES(board),test_date=VALUES(test_date),duration_minutes=VALUES(duration_minutes),total_marks=VALUES(total_marks),test_type=VALUES(test_type)"""),{'id':test.test_id,'title':test.title,'subject':test.subject,'class':test.class_level,'board':test.board,'date':test.test_date,'duration':test.duration_minutes,'marks':test.total_marks,'type':test.test_type,'status':test.status,'questions':json.dumps(test.questions)})
            db.execute(text("DELETE FROM test_questions WHERE test_id=:id"),{'id':test.test_id})
            for i,qid in enumerate(test.questions,1):
                q=self.questions.get(qid)
                if q: db.execute(text("INSERT INTO test_questions(test_id,question_id,sequence_number,marks) VALUES(:t,:q,:s,:m)"),{'t':test.test_id,'q':qid,'s':i,'m':q.marks})
        self.tests[test.test_id]=test

    def get_test(self,test_id): return self.tests.get(test_id)

    def create_question(self,q: Question):
        content=json.dumps([{'type':c.type,'value':c.value,'asset_id':c.asset_id,'metadata':c.metadata} for c in q.question_content],ensure_ascii=False)
        p={'id':q.question_id,'subject':q.subject,'board':q.board,'class':q.class_level,'chapter':q.chapter,'topic':q.topic,'subtopic':q.subtopic,'type':q.question_type,'mode':q.answer_mode,'difficulty':q.difficulty,'competency':q.competency,'content':content,'choices':json.dumps(q.answer_choices,ensure_ascii=False),'correct':q.correct_answer,'marks':q.marks,'upload':q.handwritten_upload_mode,'source':q.source,'year':q.source_year,'status':q.status}
        with engine.begin() as db:
            db.execute(text("""INSERT INTO questions(question_id,subject,board,class_level,chapter,topic,subtopic,question_type,answer_mode,difficulty,competency,question_content_json,answer_choices_json,correct_answer,marks,handwritten_upload_mode,source,source_year,status) VALUES(:id,:subject,:board,:class,:chapter,:topic,:subtopic,:type,:mode,:difficulty,:competency,:content,:choices,:correct,:marks,:upload,:source,:year,:status) ON DUPLICATE KEY UPDATE question_content_json=VALUES(question_content_json),answer_choices_json=VALUES(answer_choices_json),correct_answer=VALUES(correct_answer),marks=VALUES(marks),handwritten_upload_mode=VALUES(handwritten_upload_mode),chapter=VALUES(chapter),topic=VALUES(topic),subtopic=VALUES(subtopic),difficulty=VALUES(difficulty),competency=VALUES(competency),subject=VALUES(subject),board=VALUES(board),class_level=VALUES(class_level),answer_mode=VALUES(answer_mode),question_type=VALUES(question_type),source=VALUES(source),source_year=VALUES(source_year),status=VALUES(status)"""),p)
        self.questions[q.question_id]=q

    def get_question(self,qid): return self.questions.get(qid)
    def get_questions(self,qids: List[str]): return [self.questions[x] for x in qids if x in self.questions]

    def delete_question(self,qid):
        with engine.begin() as db:
            db.execute(text("UPDATE questions SET status='inactive' WHERE question_id=:id"), {'id': qid})
        if qid in self.questions:
            self.questions[qid].status = 'inactive'

    def activate_question(self,qid):
        with engine.begin() as db:
            db.execute(text("UPDATE questions SET status='active' WHERE question_id=:id"), {'id': qid})
        if qid in self.questions:
            self.questions[qid].status = 'active'

    def create_student(self,s: Student):
        with engine.begin() as db:
            db.execute(text("""INSERT INTO students(student_id,name,email,phone,city,role,class_level,board,school,registration_date,registration_source,status) VALUES(:id,:name,:email,:phone,:city,:role,:class,:board,:school,:reg,:source,:status) ON DUPLICATE KEY UPDATE name=VALUES(name),phone=VALUES(phone),city=VALUES(city),role=VALUES(role),class_level=VALUES(class_level),board=VALUES(board),school=VALUES(school),registration_source=VALUES(registration_source),status=VALUES(status)"""),{'id':s.student_id,'name':s.name,'email':s.email,'phone':s.phone,'city':s.city,'role':s.role,'class':s.class_level,'board':s.board,'school':s.school,'reg':s.registration_date,'source':s.registration_source,'status':s.status})
        self.students[s.student_id]=s

    def get_student(self,sid): return self.students.get(sid)

    def create_attempt(self,a: Attempt):
        with engine.begin() as db: db.execute(text("INSERT INTO attempts(attempt_id,student_id,test_id,started_at,submitted_at,status,score,percentage,attempt_rate,accuracy,time_taken_seconds) VALUES(:id,:student,:test,:started,:submitted,:status,:score,:percentage,:rate,:accuracy,:time)"),{'id':a.attempt_id,'student':a.student_id,'test':a.test_id,'started':a.started_at,'submitted':a.submitted_at,'status':a.status,'score':a.score,'percentage':a.percentage,'rate':a.attempt_rate,'accuracy':a.accuracy,'time':a.time_taken_seconds})
        self.attempts[a.attempt_id]=a

    def get_attempt(self,aid): return self.attempts.get(aid)
    def get_student_test_attempt(self,sid,tid):
        rows=[a for a in self.attempts.values() if a.student_id==sid and a.test_id==tid]
        return max(rows,key=lambda x:x.started_at) if rows else None

    def update_attempt(self,a: Attempt):
        with engine.begin() as db: db.execute(text("UPDATE attempts SET submitted_at=:submitted,status=:status,score=:score,percentage=:percentage,attempt_rate=:rate,accuracy=:accuracy,time_taken_seconds=:time WHERE attempt_id=:id"),{'submitted':a.submitted_at,'status':a.status,'score':a.score,'percentage':a.percentage,'rate':a.attempt_rate,'accuracy':a.accuracy,'time':a.time_taken_seconds,'id':a.attempt_id})
        self.attempts[a.attempt_id]=a

    def create_response(self,r: Response):
        with engine.begin() as db: db.execute(text("INSERT INTO responses(response_id,attempt_id,question_id,selected_answer,answer_status,marks_awarded,is_correct,answered_at) VALUES(:id,:attempt,:question,:answer,:status,:marks,:correct,:at) ON DUPLICATE KEY UPDATE selected_answer=VALUES(selected_answer),answer_status=VALUES(answer_status),marks_awarded=VALUES(marks_awarded),is_correct=VALUES(is_correct),answered_at=VALUES(answered_at)"),{'id':r.response_id,'attempt':r.attempt_id,'question':r.question_id,'answer':r.selected_answer,'status':r.answer_status,'marks':r.marks_awarded,'correct':r.is_correct,'at':r.answered_at})
        self.responses[r.response_id]=r

    def get_response(self,aid,qid): return next((r for r in self.responses.values() if r.attempt_id==aid and r.question_id==qid),None)
    def get_attempt_responses(self,aid): return [r for r in self.responses.values() if r.attempt_id==aid]
    def update_response(self,r): self.create_response(r)

    def create_image(self,i: AnswerImage):
        with engine.begin() as db: db.execute(text("INSERT INTO answer_images(image_id,attempt_id,question_id,page_number,original_filename,file_path,uploaded_at) VALUES(:id,:attempt,:question,:page,:name,:path,:uploaded)"),{'id':i.image_id,'attempt':i.attempt_id,'question':i.question_id,'page':i.page_number,'name':i.original_filename,'path':i.file_path,'uploaded':i.uploaded_at})
        self.images[i.image_id]=i

    def get_attempt_images(self,aid,qid): return sorted([i for i in self.images.values() if i.attempt_id==aid and i.question_id==qid],key=lambda x:x.page_number)
    def delete_image(self,iid):
        with engine.begin() as db: db.execute(text("DELETE FROM answer_images WHERE image_id=:id"),{'id':iid})
        self.images.pop(iid,None)

    def record_academic_profile(self,student_id,study_hours_per_week,preparation_level,study_methods,completed_chapters,current_chapter,most_difficult_chapter,improvement_areas):
        with engine.begin() as db: db.execute(text("INSERT INTO student_academic_profiles(student_id,study_hours_per_week,preparation_level,current_study_methods_json,completed_chapters_json,current_chapter,most_difficult_chapter,improvement_areas_json) VALUES(:id,:hours,:level,:methods,:completed,:current,:difficult,:areas)"),{'id':student_id,'hours':study_hours_per_week,'level':preparation_level,'methods':json.dumps(study_methods,ensure_ascii=False),'completed':json.dumps(completed_chapters,ensure_ascii=False),'current':current_chapter,'difficult':most_difficult_chapter,'areas':json.dumps(improvement_areas,ensure_ascii=False)})

    def record_chapter_status(self,student_id,chapter,status,board=None,class_level=None):
        with engine.begin() as db: db.execute(text("INSERT INTO student_chapter_status(student_id,chapter,status,board,class_level) VALUES(:id,:chapter,:status,:board,:class)"),{'id':student_id,'chapter':chapter,'status':status,'board':board,'class':class_level})

    def record_improvement_area(self,student_id,area,priority=1):
        with engine.begin() as db: db.execute(text("INSERT INTO student_improvement_areas(student_id,area,priority) VALUES(:id,:area,:priority)"),{'id':student_id,'area':area,'priority':priority})

    def create_plan(self,plan_id,name,description,amount_paise,billing_interval='monthly'):
        with engine.begin() as db: db.execute(text("INSERT INTO plans(plan_id,name,description,amount_paise,billing_interval,active) VALUES(:id,:name,:description,:amount,:interval,1) ON DUPLICATE KEY UPDATE name=VALUES(name),description=VALUES(description),amount_paise=VALUES(amount),billing_interval=VALUES(billing_interval),active=1"),{'id':plan_id,'name':name,'description':description,'amount':amount_paise,'interval':billing_interval})

    def create_subscription(self,subscription_id,student_id,plan_id,start_date,end_date,status):
        with engine.begin() as db: db.execute(text("INSERT INTO subscriptions(subscription_id,student_id,plan_id,start_date,end_date,status) VALUES(:id,:student,:plan,:start,:end,:status)"),{'id':subscription_id,'student':student_id,'plan':plan_id,'start':start_date,'end':end_date,'status':status})

    def record_payment(self,payment_id,student_id,amount_paise,billing_period,status,subscription_id=None,payment_date=None,payment_method=None,transaction_reference=None):
        with engine.begin() as db: db.execute(text("INSERT INTO payments(payment_id,student_id,subscription_id,billing_period,amount_paise,currency,payment_date,payment_method,transaction_reference,status) VALUES(:id,:student,:subscription,:period,:amount,'INR',:date,:method,:reference,:status)"),{'id':payment_id,'student':student_id,'subscription':subscription_id,'period':billing_period,'amount':amount_paise,'date':payment_date,'method':payment_method,'reference':transaction_reference,'status':status})

    def get_payment_for_period(self,student_id,billing_period):
        with engine.connect() as db: return db.execute(text("SELECT * FROM payments WHERE student_id=:student AND billing_period=:period ORDER BY created_at DESC LIMIT 1"),{'student':student_id,'period':billing_period}).mappings().first()

    def record_question_history(self,student_id,question_id,correct,marks_awarded,attempted_at,error_summary=None):
        with engine.begin() as db: db.execute(text("""INSERT INTO question_history(student_id,question_id,attempt_count,correct_count,last_attempted_at,last_correct_at,last_marks_awarded,last_error_summary) VALUES(:student,:question,1,:correct_count,:attempted,:correct_at,:marks,:errors) ON DUPLICATE KEY UPDATE attempt_count=attempt_count+1,correct_count=correct_count+VALUES(correct_count),last_attempted_at=VALUES(last_attempted_at),last_correct_at=IF(VALUES(last_correct_at) IS NOT NULL,VALUES(last_correct_at),last_correct_at),last_marks_awarded=VALUES(last_marks_awarded),last_error_summary=VALUES(last_error_summary)"""),{'student':student_id,'question':question_id,'correct_count':1 if correct else 0,'attempted':attempted_at,'correct_at':attempted_at if correct else None,'marks':marks_awarded,'errors':error_summary})

    def get_question_history(self,student_id,question_id=None):
        with engine.connect() as db:
            if question_id: return db.execute(text("SELECT * FROM question_history WHERE student_id=:student AND question_id=:question"),{'student':student_id,'question':question_id}).mappings().first()
            return db.execute(text("SELECT * FROM question_history WHERE student_id=:student ORDER BY last_attempted_at DESC"),{'student':student_id}).mappings().all()

storage=MySQLStorage()
