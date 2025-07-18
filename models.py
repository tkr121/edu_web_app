# models.py
from exts import db
from flask_login import UserMixin
from datetime import datetime, timedelta, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.orm import relationship

class PracticeHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    count = db.Column(db.Integer)
    date = db.Column(db.Date)

    @classmethod
    def get_weekly_practice(cls, student_id):
        today = datetime.now(timezone(timedelta(hours=8))).date()
        # 查询最近7天记录
        records = cls.query.filter(
            cls.student_id == student_id,
            cls.date >= today - timedelta(days=6),
            cls.date <= today
        ).all()

        # 构建日期到练习次数的映射
        record_map = {record.date: record.count for record in records}

        # 补全缺失日期，默认为 0
        labels = []
        data = []
        for i in range(7):
            day = today - timedelta(days=i)
            labels.append(day.strftime('%m-%d'))
            data.append(record_map.get(day, None))  # 先设为 None 表示可能缺失

        # 补全缺失的记录
        for i in range(7):
            day = today - timedelta(days=i)
            if data[i] is None:
                # 插入默认记录
                new_record = PracticeHistory(
                    student_id=student_id,
                    count=0,
                    date=day
                )
                db.session.add(new_record)
                data[i] = 0  # 补为0

        db.session.commit()  # 提交新增的默认记录

        # 返回顺序：从早到晚（倒序）
        return {"labels": labels[::-1], "data": data[::-1]}

class Teacher(db.Model, UserMixin):
    __tablename__ = 'teacher'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100))  # 教授科目（可选）
    teacher_id = db.Column(db.String(50), unique=True, nullable=False)

# 新增中间表 student_question（自动映射）
student_question = db.Table('student_question',
    db.Column('student_id', db.Integer, db.ForeignKey('student.id'), primary_key=True),
    db.Column('question_id', db.Integer, db.ForeignKey('questions.id'), primary_key=True),
    db.Column('added_at', db.DateTime, default=datetime.utcnow)
)

class Student(db.Model, UserMixin):
    __tablename__ = 'student'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    student_id = db.Column(db.String(50), unique=True, nullable=False)
    # 错题记录（新增的 relationship）
    wrong_questions = db.relationship('WrongQuestion', back_populates='student')
    recommended_topics = db.relationship('RecommendedTopic', back_populates='student', lazy=True)
    tasks = db.relationship('Task', back_populates='student')


class WrongQuestion(db.Model):
    __tablename__ = 'wrong_question'

    id = db.Column(db.Integer, primary_key=True)  # 主键ID
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)  # 所属学生ID
    question_text = db.Column(db.Text, nullable=False)  # 题目内容
    correct_answer = db.Column(db.Text, nullable=False)  # 正确答案
    error_reason = db.Column(db.Text, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)  # 记录时间

    # 与 Student 表的关联，反向引用到 Student 的错题记录
    student = db.relationship("Student", back_populates="wrong_questions")

class RecommendedTopic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    topics_json = db.Column(db.Text)  # 存储 JSON 字符串
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship('Student', back_populates='recommended_topics')



class Question(db.Model):
    __tablename__ = 'questions'  # 表名
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_text = db.Column(db.Text, nullable=False)  # 题目内容
    topic = db.Column(db.String(100), nullable=True)  # 所属知识点/章节
    correct_answer = db.Column(db.Text, nullable=False)  # 正确答案
    type = db.Column(db.String(50), nullable=True)  # 题目类型：选择题、简答题等
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 与 Student 表的关联
    student = db.relationship("Student", back_populates="tasks")
    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'name': self.name,
            'completed': bool(self.completed) if self.completed is not None else False,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


