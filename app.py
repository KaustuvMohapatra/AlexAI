import os
import logging
import json
import io
from datetime import datetime, timedelta
from flask import Flask, Response, render_template, request, jsonify, redirect, url_for, session, flash
from dotenv import load_dotenv
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image
from utils.gemini_handler import initialize_gemini, get_response_stream, get_conversation_title
from utils.analysis_handler import analyze_sentiment
from utils.search_handler import is_realtime_query, fetch_realtime_info

# Import models and initialize database
from models import db, User, Conversation, Message, UserProfile, UserMemory, TaskAutomation, EmotionLog, ProactiveTask

# --- Basic App Setup ---
load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a-very-secret-key-for-production')
logging.basicConfig(level=logging.INFO)

# --- Database Configuration ---
# Use PostgreSQL for production (Railway), SQLite for development
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Railway PostgreSQL
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_BINDS'] = {'chats': DATABASE_URL}
else:
    # Local development
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'users.db')
    app.config['SQLALCHEMY_BINDS'] = {'chats': 'sqlite:///' + os.path.join(basedir, 'chats.db')}

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize db with app
db.init_app(app)

# --- Login Manager Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import handlers after database initialization
from utils.memory_handler import MemoryManager
from utils.emotion_handler import EmotionAnalyzer
from utils.proactive_handler import ProactiveAssistant
from utils.automation_handler import TaskAutomationManager

@login_manager.user_loader
def load_user(user_id):
    try:
        user = db.session.get(User, int(user_id))
        logging.info(f"Loading user: {user}")
        return user
    except Exception as e:
        logging.error(f"Error loading user {user_id}: {e}")
        return None

def save_message_to_db(conversation_id, role, content):
    message = Message(role=role, content=content, conversation_id=conversation_id)
    db.session.add(message)
    db.session.commit()

# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user, remember=True)
            return redirect(url_for('index'))
        return render_template('login.html', error="Invalid username or password.")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user:
            return render_template('register.html', error="Username already exists.")

        new_user = User(username=request.form['username'])
        new_user.set_password(request.form['password'])
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    logout_user()
    flash('You have been successfully logged out.', 'info')
    return redirect(url_for('login'))

@app.route("/")
@login_required
def index():
    new_convo = Conversation(user_id=current_user.id)
    db.session.add(new_convo)
    db.session.commit()
    return redirect(url_for('load_conversation', conversation_id=new_convo.id))

@app.route("/conversation/<int:conversation_id>")
@login_required
def load_conversation(conversation_id):
    conversation = db.session.get(Conversation, conversation_id)
    if conversation and conversation.user_id == current_user.id:
        all_conversations = Conversation.query.filter_by(user_id=current_user.id).order_by(Conversation.id.desc()).all()
        return render_template("index.html", conversations=all_conversations, active_conversation=conversation)
    return redirect(url_for('index'))

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    user_prompt = request.form.get("prompt", "")
    image_file = request.files.get("image")
    conversation_id = request.form.get("conversation_id", type=int)

    image_data = image_file.read() if image_file else None

    if not conversation_id:
        return jsonify({"error": "Missing conversation ID."}), 400

    user_id = current_user.id

    initial_conversation = db.session.get(Conversation, conversation_id)
    if not initial_conversation or initial_conversation.user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    def generate_and_save():
        with app.app_context():
            full_bot_response = ""
            try:
                conversation = db.session.get(Conversation, conversation_id)
                if not conversation:
                    raise ValueError("Conversation not found inside generator.")

                memory_manager = MemoryManager(user_id)
                emotion_analyzer = EmotionAnalyzer()
                proactive_assistant = ProactiveAssistant(user_id)
                automation_manager = TaskAutomationManager(user_id)

                is_first_exchange = len(conversation.messages) == 0

                emotions = emotion_analyzer.analyze_emotion(user_prompt, user_id, conversation_id)
                yield f"event: emotion\ndata: {json.dumps(emotions)}\n\n"

                triggered_actions = automation_manager.check_triggers(user_prompt)
                if triggered_actions:
                    automation_results = automation_manager.execute_actions(triggered_actions)
                    yield f"event: automation\ndata: {json.dumps(automation_results)}\n\n"

                relevant_memories = memory_manager.retrieve_relevant_memories(user_prompt)
                memory_context = "\n".join([f"{m.key}: {m.value}" for m in relevant_memories])

                proactive_suggestions = proactive_assistant.generate_proactive_suggestions({
                    'current_message': user_prompt,
                    'emotions': emotions,
                    'memories': relevant_memories
                })

                if proactive_suggestions:
                    yield f"event: proactive\ndata: {json.dumps(proactive_suggestions)}\n\n"

                save_message_to_db(conversation_id, 'user', user_prompt)

                if any(keyword in user_prompt.lower() for keyword in ['remember', 'important', 'deadline', 'meeting']):
                    memory_manager.store_memory('user_request', 'important_info', user_prompt, importance=1.5)

                history = [{'role': msg.role, 'parts': [{'text': msg.content}]} for msg in conversation.messages]

                chat_session = initialize_gemini(history=history)
                if not chat_session:
                    raise ConnectionError("Failed to initialize Gemini session.")

                enhanced_prompt = user_prompt

                if memory_context:
                    context_prefix = f"[Context from previous interactions: {memory_context[:500]}...]\n[Current mood: {emotions}]\n\n"
                    enhanced_prompt = context_prefix + enhanced_prompt

                if emotions.get('stress', 0) > 0.6:
                    enhanced_prompt += "\n\n[Note: I'm feeling stressed, please be supportive.]"
                elif emotions.get('happiness', 0) > 0.7:
                    enhanced_prompt += "\n\n[Note: I'm in a great mood today!]"

                prompt_parts = []
                if image_data:
                    img = Image.open(io.BytesIO(image_data))
                    prompt_parts.extend([enhanced_prompt, img])
                elif is_realtime_query(user_prompt):
                    context = fetch_realtime_info(user_prompt)
                    prompt_parts.append(f"Based on this real-time info: '{context}'. Answer: '{enhanced_prompt}'")
                else:
                    prompt_parts.append(enhanced_prompt)

                sentiment_scores = analyze_sentiment(user_prompt or " ")
                yield f"event: sentiment\ndata: {json.dumps(sentiment_scores)}\n\n"

                stream_generator = get_response_stream(chat_session, prompt_parts)
                for chunk_text in stream_generator:
                    full_bot_response += chunk_text
                    yield f"data: {json.dumps({'text': chunk_text})}\n\n"

                save_message_to_db(conversation_id, 'model', full_bot_response)

                memory_manager.store_memory('interaction_pattern',
                                            f"query_type_{datetime.now().strftime('%Y%m%d')}",
                                            {'query': user_prompt, 'response_length': len(full_bot_response),
                                             'emotions': emotions})

                if is_first_exchange:
                    title = get_conversation_title(user_prompt, full_bot_response)
                    if title:
                        conversation.title = title
                        db.session.commit()

            except Exception as e:
                logging.error(f"Error during enhanced response generation: {e}")
                yield f"event: error\ndata: {json.dumps({'error': 'A server error occurred.'})}\n\n"

    return Response(generate_and_save(), mimetype='text/event-stream')

# --- API Routes for Advanced Features ---
@app.route('/api/automations', methods=['GET', 'POST'])
@login_required
def manage_automations():
    user_id = current_user.id
    automation_manager = TaskAutomationManager(user_id)

    if request.method == 'POST':
        data = request.get_json()
        trigger_phrase = data.get('trigger_phrase')
        actions = data.get('actions')

        if trigger_phrase and actions:
            automation_id = automation_manager.create_automation(trigger_phrase, actions)
            return jsonify({'success': True, 'automation_id': automation_id})
        return jsonify({'success': False, 'error': 'Missing required fields'})

    stats = automation_manager.get_automation_statistics()
    return jsonify(stats)

@app.route('/api/memories', methods=['GET'])
@login_required
def get_memories():
    user_id = current_user.id
    memory_manager = MemoryManager(user_id)
    query = request.args.get('query', '')
    limit = request.args.get('limit', 10, type=int)

    memories = memory_manager.retrieve_relevant_memories(query, limit)
    memory_data = [{
        'id': m.id,
        'type': m.memory_type,
        'key': m.key,
        'value': m.value,
        'importance': m.importance_score,
        'created_at': m.created_at.isoformat()
    } for m in memories]

    return jsonify({'memories': memory_data})

@app.route('/api/emotions/trend', methods=['GET'])
@login_required
def get_emotion_trend():
    user_id = current_user.id
    emotion_analyzer = EmotionAnalyzer()
    hours = request.args.get('hours', 24, type=int)

    trend = emotion_analyzer.get_emotion_trend(user_id, hours)
    return jsonify({'trend': trend, 'period_hours': hours})

# --- Error Handlers ---
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# --- Create Database and Run App ---
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
