from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    conversations = db.relationship('Conversation', foreign_keys='Conversation.user_id',
                                    primaryjoin='User.id == Conversation.user_id', lazy=True,
                                    cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Conversation(db.Model):
    __bind_key__ = 'chats'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), default="New Conversation")
    user_id = db.Column(db.Integer, nullable=False)
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade="all, delete-orphan")

class Message(db.Model):
    __bind_key__ = 'chats'
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timezone = db.Column(db.String(50), default='UTC')
    work_schedule_start = db.Column(db.Time)
    work_schedule_end = db.Column(db.Time)
    break_interval = db.Column(db.Integer, default=60)
    preferences = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserMemory(db.Model):
    __bind_key__ = 'chats'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    memory_type = db.Column(db.String(50))
    key = db.Column(db.String(100))
    value = db.Column(db.Text)
    importance_score = db.Column(db.Float, default=1.0)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TaskAutomation(db.Model):
    __bind_key__ = 'chats'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    trigger_phrase = db.Column(db.String(200))
    actions = db.Column(db.JSON)
    is_active = db.Column(db.Boolean, default=True)
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)

class EmotionLog(db.Model):
    __bind_key__ = 'chats'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'))
    emotion_scores = db.Column(db.JSON)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)

class ProactiveTask(db.Model):
    __bind_key__ = 'chats'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    task_type = db.Column(db.String(50))
    scheduled_for = db.Column(db.DateTime)
    is_completed = db.Column(db.Boolean, default=False)
    context_data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
