# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade="all, delete-orphan")
    conversations = db.relationship('Conversation', backref='user', lazy=True, cascade="all, delete-orphan")
    memories = db.relationship('UserMemory', backref='user', lazy=True, cascade="all, delete-orphan")
    automations = db.relationship('TaskAutomation', backref='user', lazy=True, cascade="all, delete-orphan")
    emotion_logs = db.relationship('EmotionLog', backref='user', lazy=True, cascade="all, delete-orphan")
    proactive_tasks = db.relationship('ProactiveTask', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class UserProfile(db.Model):
    __tablename__ = 'user_profile'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100))
    preferences = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Conversation(db.Model):
    __tablename__ = 'conversation'
    # REMOVED: __bind_key__ = 'chats'  # This was causing the foreign key issue

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), default="New Conversation")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade="all, delete-orphan")
    emotion_logs = db.relationship('EmotionLog', backref='conversation', lazy=True, cascade="all, delete-orphan")


class Message(db.Model):
    __tablename__ = 'message'
    # REMOVED: __bind_key__ = 'chats'  # This was causing the foreign key issue

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(10), nullable=False)
    content = db.Column(db.Text, nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserMemory(db.Model):
    __tablename__ = 'user_memory'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    memory_type = db.Column(db.String(50))
    key = db.Column(db.String(200))
    value = db.Column(db.Text)
    importance_score = db.Column(db.Float, default=1.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TaskAutomation(db.Model):
    __tablename__ = 'task_automation'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trigger_phrase = db.Column(db.String(200))
    actions = db.Column(db.JSON)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class EmotionLog(db.Model):
    __tablename__ = 'emotion_log'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    emotions = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ProactiveTask(db.Model):
    __tablename__ = 'proactive_task'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_type = db.Column(db.String(50))
    content = db.Column(db.JSON)
    due_date = db.Column(db.DateTime)
    is_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
