import os
import logging
import json
import io
from datetime import datetime, timedelta
from flask import Flask, Response, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image
from utils.gemini_handler import initialize_gemini, get_response_stream, get_conversation_title
from utils.analysis_handler import analyze_sentiment
from utils.search_handler import is_realtime_query, fetch_realtime_info

# --- Basic App Setup ---
load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a-very-secret-key-for-production')
logging.basicConfig(level=logging.INFO)

# --- Database Configuration ---
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'users.db')
app.config['SQLALCHEMY_BINDS'] = {'chats': 'sqlite:///' + os.path.join(basedir, 'chats.db')}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import models and initialize database
from models import db, User, Conversation, Message, UserProfile, UserMemory, TaskAutomation, EmotionLog, ProactiveTask

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
    logout_user()
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
    # Add debug logging
    logging.info(f"Chat route accessed. Current user: {current_user}")
    logging.info(f"Current user ID: {getattr(current_user, 'id', 'No ID attribute')}")
    logging.info(f"Is authenticated: {current_user.is_authenticated}")

    user_prompt = request.form.get("prompt", "")
    image_file = request.files.get("image")
    conversation_id = request.form.get("conversation_id", type=int)

    image_data = image_file.read() if image_file else None

    if not conversation_id:
        return jsonify({"error": "Missing conversation ID."}), 400

    # CRITICAL FIX: Capture user_id before entering the generator
    user_id = current_user.id  # Store this outside the generator

    # Verify conversation ownership
    initial_conversation = db.session.get(Conversation, conversation_id)
    if not initial_conversation or initial_conversation.user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    def generate_and_save():
        with app.app_context():
            full_bot_response = ""
            try:
                # Re-fetch the conversation object within this new context
                conversation = db.session.get(Conversation, conversation_id)
                if not conversation:
                    raise ValueError("Conversation not found inside generator.")

                # FIXED: Use captured user_id instead of current_user.id
                memory_manager = MemoryManager(user_id)
                emotion_analyzer = EmotionAnalyzer()
                proactive_assistant = ProactiveAssistant(user_id)
                automation_manager = TaskAutomationManager(user_id)

                is_first_exchange = len(conversation.messages) == 0

                # FIXED: Use user_id consistently throughout
                emotions = emotion_analyzer.analyze_emotion(user_prompt, user_id, conversation_id)
                yield f"event: emotion\ndata: {json.dumps(emotions)}\n\n"

                # Check for task automation triggers
                triggered_actions = automation_manager.check_triggers(user_prompt)
                if triggered_actions:
                    automation_results = automation_manager.execute_actions(triggered_actions)
                    yield f"event: automation\ndata: {json.dumps(automation_results)}\n\n"

                # Retrieve relevant memories
                relevant_memories = memory_manager.retrieve_relevant_memories(user_prompt)
                memory_context = "\n".join([f"{m.key}: {m.value}" for m in relevant_memories])

                # Generate proactive suggestions
                proactive_suggestions = proactive_assistant.generate_proactive_suggestions({
                    'current_message': user_prompt,
                    'emotions': emotions,
                    'memories': relevant_memories
                })

                if proactive_suggestions:
                    yield f"event: proactive\ndata: {json.dumps(proactive_suggestions)}\n\n"

                # Store user message
                save_message_to_db(conversation_id, 'user', user_prompt)

                # Store important information as memories
                if any(keyword in user_prompt.lower() for keyword in ['remember', 'important', 'deadline', 'meeting']):
                    memory_manager.store_memory('user_request', 'important_info', user_prompt, importance=1.5)

                # Load conversation history
                history = [{'role': msg.role, 'parts': [{'text': msg.content}]} for msg in conversation.messages]

                # Initialize Gemini with conversation history
                chat_session = initialize_gemini(history=history)
                if not chat_session:
                    raise ConnectionError("Failed to initialize Gemini session.")

                # FIXED: Prepare enhanced prompt with context integrated into user message
                enhanced_prompt = user_prompt

                # Add memory context to the user prompt instead of system message
                if memory_context:
                    context_prefix = f"[Context from previous interactions: {memory_context[:500]}...]\n[Current emotional state: {emotions}]\n\n"
                    enhanced_prompt = context_prefix + enhanced_prompt

                if emotions.get('stress', 0) > 0.6:
                    enhanced_prompt += "\n\n[Note: I'm feeling stressed, please be supportive.]"
                elif emotions.get('happiness', 0) > 0.7:
                    enhanced_prompt += "\n\n[Note: I'm in a great mood today!]"

                # Prepare prompt parts
                prompt_parts = []
                if image_data:
                    img = Image.open(io.BytesIO(image_data))
                    prompt_parts.extend([enhanced_prompt, img])
                elif is_realtime_query(user_prompt):
                    context = fetch_realtime_info(user_prompt)
                    prompt_parts.append(f"Based on this real-time info: '{context}'. Answer: '{enhanced_prompt}'")
                else:
                    prompt_parts.append(enhanced_prompt)

                # Send sentiment analysis
                sentiment_scores = analyze_sentiment(user_prompt or " ")
                yield f"event: sentiment\ndata: {json.dumps(sentiment_scores)}\n\n"

                # Stream response with emotional awareness
                stream_generator = get_response_stream(chat_session, prompt_parts)
                for chunk_text in stream_generator:
                    full_bot_response += chunk_text
                    yield f"data: {json.dumps({'text': chunk_text})}\n\n"

                # Save bot response
                save_message_to_db(conversation_id, 'model', full_bot_response)

                # Store interaction patterns as memories
                memory_manager.store_memory('interaction_pattern',
                                            f"query_type_{datetime.now().strftime('%Y%m%d')}",
                                            {'query': user_prompt, 'response_length': len(full_bot_response),
                                             'emotions': emotions})

                # Update conversation title if first exchange
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
    user_id = current_user.id  # Capture user_id
    automation_manager = TaskAutomationManager(user_id)

    if request.method == 'POST':
        data = request.get_json()
        trigger_phrase = data.get('trigger_phrase')
        actions = data.get('actions')

        if trigger_phrase and actions:
            automation_id = automation_manager.create_automation(trigger_phrase, actions)
            return jsonify({'success': True, 'automation_id': automation_id})
        return jsonify({'success': False, 'error': 'Missing required fields'})

    # GET request - return automation statistics
    stats = automation_manager.get_automation_statistics()
    return jsonify(stats)


@app.route('/api/memories', methods=['GET'])
@login_required
def get_memories():
    user_id = current_user.id  # Capture user_id
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
    user_id = current_user.id  # Capture user_id
    emotion_analyzer = EmotionAnalyzer()
    hours = request.args.get('hours', 24, type=int)

    trend = emotion_analyzer.get_emotion_trend(user_id, hours)
    return jsonify({'trend': trend, 'period_hours': hours})


# --- Additional API Routes for Enhanced Features ---
@app.route('/api/proactive/suggestions', methods=['GET'])
@login_required
def get_proactive_suggestions():
    user_id = current_user.id
    proactive_assistant = ProactiveAssistant(user_id)

    context = {
        'current_message': request.args.get('message', ''),
        'emotions': {},
        'memories': []
    }

    suggestions = proactive_assistant.generate_proactive_suggestions(context)
    return jsonify({'suggestions': suggestions})


@app.route('/api/user/profile', methods=['GET', 'POST'])
@login_required
def manage_user_profile():
    user_id = current_user.id

    if request.method == 'POST':
        data = request.get_json()

        # Find or create user profile
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.session.add(profile)

        # Update profile data
        if 'timezone' in data:
            profile.timezone = data['timezone']
        if 'work_schedule_start' in data:
            profile.work_schedule_start = datetime.strptime(data['work_schedule_start'], '%H:%M').time()
        if 'work_schedule_end' in data:
            profile.work_schedule_end = datetime.strptime(data['work_schedule_end'], '%H:%M').time()
        if 'break_interval' in data:
            profile.break_interval = data['break_interval']
        if 'preferences' in data:
            profile.preferences = data['preferences']

        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated successfully'})

    # GET request - return user profile
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if profile:
        profile_data = {
            'timezone': profile.timezone,
            'work_schedule_start': profile.work_schedule_start.strftime(
                '%H:%M') if profile.work_schedule_start else None,
            'work_schedule_end': profile.work_schedule_end.strftime('%H:%M') if profile.work_schedule_end else None,
            'break_interval': profile.break_interval,
            'preferences': profile.preferences or {}
        }
    else:
        profile_data = {
            'timezone': 'UTC',
            'work_schedule_start': None,
            'work_schedule_end': None,
            'break_interval': 60,
            'preferences': {}
        }

    return jsonify({'profile': profile_data})


@app.route('/api/conversations/export', methods=['GET'])
@login_required
def export_conversations():
    user_id = current_user.id
    conversations = Conversation.query.filter_by(user_id=user_id).all()

    export_data = []
    for conv in conversations:
        conv_data = {
            'id': conv.id,
            'title': conv.title,
            'messages': [{
                'role': msg.role,
                'content': msg.content,
                'created_at': msg.created_at.isoformat() if msg.created_at else None
            } for msg in conv.messages]
        }
        export_data.append(conv_data)

    return jsonify({'conversations': export_data})


@app.route('/api/stats/dashboard', methods=['GET'])
@login_required
def get_dashboard_stats():
    user_id = current_user.id

    # Get basic stats
    total_conversations = Conversation.query.filter_by(user_id=user_id).count()
    total_messages = Message.query.join(Conversation).filter(Conversation.user_id == user_id).count()

    # Get recent activity
    last_week = datetime.utcnow() - timedelta(days=7)
    recent_conversations = Conversation.query.filter(
        Conversation.user_id == user_id,
        Conversation.id.in_(
            db.session.query(Message.conversation_id).filter(Message.created_at >= last_week)
        )
    ).count()

    # Get emotion trends
    emotion_analyzer = EmotionAnalyzer()
    emotion_trend = emotion_analyzer.get_emotion_trend(user_id, 168)  # Last week

    # Get automation stats
    automation_manager = TaskAutomationManager(user_id)
    automation_stats = automation_manager.get_automation_statistics()

    # Get memory stats
    memory_count = UserMemory.query.filter_by(user_id=user_id).count()

    dashboard_data = {
        'total_conversations': total_conversations,
        'total_messages': total_messages,
        'recent_conversations': recent_conversations,
        'emotion_trend': emotion_trend,
        'automation_stats': automation_stats,
        'memory_count': memory_count,
        'last_updated': datetime.utcnow().isoformat()
    }

    return jsonify(dashboard_data)


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
    app.run(host="0.0.0.0", port=5000, debug=True)
