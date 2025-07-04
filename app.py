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
from flask_migrate import Migrate

# Import models first
from models import db, User, Conversation, Message, UserProfile, UserMemory, TaskAutomation, EmotionLog, ProactiveTask

# --- Basic App Setup ---
load_dotenv()
app = Flask(__name__)

# Enhanced session configuration for proper logout
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a-very-secret-key-for-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

logging.basicConfig(level=logging.INFO)


# --- Enhanced PostgreSQL Database Configuration ---
def configure_database():
    """Configure database with enhanced PostgreSQL support and migration handling"""
    DATABASE_URL = os.environ.get('DATABASE_URL')

    if DATABASE_URL:
        # Production: Railway PostgreSQL
        logging.info("Configuring PostgreSQL database for production")

        # Handle Railway's postgres:// URL format
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
            logging.info("Converted postgres:// to postgresql:// URL format")

        # PostgreSQL configuration
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
        app.config['SQLALCHEMY_BINDS'] = {'chats': DATABASE_URL}

        # Enhanced PostgreSQL engine options
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 10,
            'pool_recycle': 120,
            'pool_pre_ping': True,
            'max_overflow': 20,
            'pool_timeout': 30,
            'echo': False  # Set to True for SQL debugging
        }

        logging.info("PostgreSQL database configured successfully")

    else:
        # Development: SQLite
        logging.info("Configuring SQLite database for development")
        basedir = os.path.abspath(os.path.dirname(__file__))
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'users.db')
        app.config['SQLALCHEMY_BINDS'] = {'chats': 'sqlite:///' + os.path.join(basedir, 'chats.db')}

        # SQLite engine options
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
        }


# Configure database
configure_database()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize db with app
db.init_app(app)

# --- Database Migration Setup ---
migrate = Migrate(app, db)

# --- Login Manager Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
login_manager.session_protection = "strong"

# Import utility handlers with fallbacks
try:
    from utils.gemini_handler import initialize_gemini, get_response_stream, get_conversation_title
    from utils.analysis_handler import analyze_sentiment
    from utils.search_handler import is_realtime_query, fetch_realtime_info
    from utils.memory_handler import MemoryManager
    from utils.emotion_handler import EmotionAnalyzer
    from utils.proactive_handler import ProactiveAssistant
    from utils.automation_handler import TaskAutomationManager

    UTILS_AVAILABLE = True
    logging.info("All utility modules loaded successfully")
except ImportError as e:
    logging.warning(f"Some utility modules not found: {e}")
    UTILS_AVAILABLE = False


    # Create fallback functions
    def initialize_gemini(history=None):
        return None


    def get_response_stream(chat_session, prompt_parts):
        yield "AI response functionality not available. Please check your Gemini API configuration."


    def get_conversation_title(user_prompt, bot_response):
        return f"Chat: {user_prompt[:30]}..."


    def analyze_sentiment(text):
        return {'positive': 0.5, 'neutral': 0.3, 'negative': 0.2}


    def is_realtime_query(query):
        return False


    def fetch_realtime_info(query):
        return "Real-time info not available"


    class MemoryManager:
        def __init__(self, user_id):
            self.user_id = user_id

        def retrieve_relevant_memories(self, query, limit=10):
            return []

        def store_memory(self, memory_type, key, value, importance=1.0):
            pass


    class EmotionAnalyzer:
        def analyze_emotion(self, text, user_id, conversation_id):
            return {'neutral': 1.0}

        def get_emotion_trend(self, user_id, hours):
            return []


    class ProactiveAssistant:
        def __init__(self, user_id):
            self.user_id = user_id

        def generate_proactive_suggestions(self, context):
            return []


    class TaskAutomationManager:
        def __init__(self, user_id):
            self.user_id = user_id

        def check_triggers(self, text):
            return []

        def execute_actions(self, actions):
            return []

        def create_automation(self, trigger, actions):
            return 1

        def get_automation_statistics(self):
            return {'total': 0, 'active': 0}


@login_manager.user_loader
def load_user(user_id):
    try:
        # Enhanced user loading with better error handling
        user = db.session.execute(
            db.select(User).where(User.id == int(user_id))
        ).scalar_one_or_none()
        return user
    except Exception as e:
        logging.error(f"Error loading user {user_id}: {e}")
        return None


def save_message_to_db(conversation_id, role, content):
    """Enhanced message saving with transaction management"""
    try:
        message = Message(role=role, content=content, conversation_id=conversation_id)
        db.session.add(message)
        db.session.commit()
        logging.debug(f"Message saved: {role} in conversation {conversation_id}")
    except Exception as e:
        logging.error(f"Error saving message: {e}")
        db.session.rollback()
        raise


# --- Database Migration Functions ---
def check_database_migration():
    """Check if database migration is needed"""
    try:
        # Test if all required tables exist
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()

        required_tables = ['user', 'conversation', 'message', 'user_profile',
                           'user_memory', 'task_automation', 'emotion_log', 'proactive_task']

        missing_tables = [table for table in required_tables if table not in existing_tables]

        if missing_tables:
            logging.warning(f"Missing database tables: {missing_tables}")
            return True

        return False
    except Exception as e:
        logging.error(f"Error checking database migration: {e}")
        return True


def perform_database_migration():
    """Perform database migration with data preservation"""
    try:
        logging.info("Starting database migration...")

        # Check if we're migrating from SQLite to PostgreSQL
        is_postgres = 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']

        if is_postgres:
            logging.info("Migrating to PostgreSQL database")

            # Create all tables
            db.create_all()

            # If migrating from SQLite, you would add data migration logic here
            # For now, we'll just create the schema

        else:
            logging.info("Creating SQLite database tables")
            db.create_all()

        # Verify migration success
        db.session.execute(db.text('SELECT 1'))
        logging.info("Database migration completed successfully")

    except Exception as e:
        logging.error(f"Database migration failed: {e}")
        raise


def initialize_database_with_migration():
    """Initialize database with migration support"""
    try:
        with app.app_context():
            # Check if migration is needed
            needs_migration = check_database_migration()

            if needs_migration:
                perform_database_migration()
            else:
                logging.info("Database schema is up to date")

            # Test database connection
            db.session.execute(db.text('SELECT 1'))

            # Log database info
            if os.environ.get('DATABASE_URL'):
                logging.info("Using PostgreSQL database (Production)")
            else:
                logging.info("Using SQLite database (Development)")

    except Exception as e:
        logging.error(f"Database initialization error: {e}")
        # Fallback: try basic table creation
        try:
            db.create_all()
            logging.info("Fallback: Basic database tables created")
        except Exception as fallback_error:
            logging.error(f"Fallback database creation failed: {fallback_error}")
            raise


# --- Enhanced Session Validation Middleware ---
@app.before_request
def validate_session():
    """Enhanced session validation that doesn't interfere with logout"""
    # Skip validation for static files and auth routes
    if request.endpoint in ['static', 'login', 'register', 'logout', 'force_logout', 'health_check', 'favicon']:
        return

    # Skip validation for API routes that don't require auth
    if request.path.startswith('/api/auth/status'):
        return

    if current_user.is_authenticated:
        # Check session timeout
        if 'last_activity' in session:
            try:
                last_activity = datetime.fromisoformat(session['last_activity'])
                if datetime.utcnow() - last_activity > app.config['PERMANENT_SESSION_LIFETIME']:
                    logout_user()
                    session.clear()
                    flash('Your session has expired. Please log in again.', 'warning')
                    return redirect(url_for('login'))
            except (ValueError, TypeError):
                # Invalid timestamp, clear session
                logout_user()
                session.clear()
                return redirect(url_for('login'))

        # Update last activity timestamp
        session['last_activity'] = datetime.utcnow().isoformat()


# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html', error="Please fill in all fields.")

        try:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                # Clear any existing session data
                session.clear()

                # Login user
                login_user(user, remember=True)
                session.permanent = True
                session['login_time'] = datetime.utcnow().isoformat()
                session['last_activity'] = datetime.utcnow().isoformat()

                flash(f'Welcome back, {user.username}!', 'success')
                logging.info(f"User {user.username} logged in successfully")

                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                flash('Invalid username or password.', 'error')
                logging.warning(f"Failed login attempt for username: {username}")
                return render_template('login.html', error="Invalid username or password.")
        except Exception as e:
            logging.error(f"Login error: {e}")
            flash('An error occurred during login. Please try again.', 'error')
            return render_template('login.html', error="Login failed.")

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Enhanced validation
        errors = []

        if not username:
            errors.append('Username is required.')
        elif len(username) < 3:
            errors.append('Username must be at least 3 characters long.')
        elif len(username) > 50:
            errors.append('Username must be less than 50 characters.')

        if not password:
            errors.append('Password is required.')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters long.')

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('register.html', errors=errors)

        try:
            # Check if username exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                flash('Username already exists. Please choose a different one.', 'error')
                return render_template('register.html', error="Username already exists.")

            # Create new user
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful! Please log in.', 'success')
            logging.info(f"New user registered: {username}")
            return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
            logging.error(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'error')
            return render_template('register.html', error="Registration failed.")

    return render_template('register.html')


# --- Enhanced Logout Route ---
@app.route('/logout')
@login_required
def logout():
    username = getattr(current_user, 'username', 'Unknown')
    user_id = getattr(current_user, 'id', 'Unknown')

    try:
        # Log the logout attempt
        logging.info(f"User {username} (ID: {user_id}) initiating logout")

        # Perform Flask-Login logout first
        logout_user()

        # Clear all session data
        session.clear()

        # Add success message
        flash('You have been successfully logged out.', 'info')

        # Log successful logout
        logging.info(f"User {username} logged out successfully")

    except Exception as e:
        # Log any errors during logout
        logging.error(f"Error during logout for user {username}: {e}")
        flash('Logout completed.', 'info')

    # Create response with security headers
    response = redirect(url_for('login'))

    # Clear cookies securely
    response.set_cookie('session', '', expires=0, secure=True, httponly=True)
    response.set_cookie('remember_token', '', expires=0, secure=True, httponly=True)

    # Add security headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response


# --- Force Logout Route ---
@app.route('/force-logout')
def force_logout():
    """Emergency logout that clears everything without authentication checks"""
    try:
        if current_user.is_authenticated:
            username = getattr(current_user, 'username', 'Unknown')
            logout_user()
            logging.info(f"Force logout executed for user: {username}")

        session.clear()
        flash('Emergency logout completed.', 'info')

    except Exception as e:
        logging.error(f"Error during force logout: {e}")

    response = redirect(url_for('login'))
    response.set_cookie('session', '', expires=0)
    return response


@app.route("/")
@login_required
def index():
    try:
        new_convo = Conversation(user_id=current_user.id)
        db.session.add(new_convo)
        db.session.commit()
        return redirect(url_for('load_conversation', conversation_id=new_convo.id))
    except Exception as e:
        logging.error(f"Error creating new conversation: {e}")
        db.session.rollback()
        flash('Error creating new conversation.', 'error')
        return render_template('index.html', conversations=[], active_conversation=None)


@app.route("/conversation/<int:conversation_id>")
@login_required
def load_conversation(conversation_id):
    try:
        conversation = db.session.get(Conversation, conversation_id)
        if conversation and conversation.user_id == current_user.id:
            all_conversations = Conversation.query.filter_by(user_id=current_user.id).order_by(
                Conversation.id.desc()).all()
            return render_template("index.html", conversations=all_conversations, active_conversation=conversation)
        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Error loading conversation {conversation_id}: {e}")
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

    # Verify conversation ownership
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

                # Initialize AI components
                memory_manager = MemoryManager(user_id)
                emotion_analyzer = EmotionAnalyzer()
                proactive_assistant = ProactiveAssistant(user_id)
                automation_manager = TaskAutomationManager(user_id)

                is_first_exchange = len(conversation.messages) == 0

                # Emotion analysis
                emotions = emotion_analyzer.analyze_emotion(user_prompt, user_id, conversation_id)
                yield f"event: emotion\ndata: {json.dumps(emotions)}\n\n"

                # Task automation
                triggered_actions = automation_manager.check_triggers(user_prompt)
                if triggered_actions:
                    automation_results = automation_manager.execute_actions(triggered_actions)
                    yield f"event: automation\ndata: {json.dumps(automation_results)}\n\n"

                # Memory retrieval
                relevant_memories = memory_manager.retrieve_relevant_memories(user_prompt)
                memory_context = "\n".join(
                    [f"{getattr(m, 'key', '')}: {getattr(m, 'value', '')}" for m in relevant_memories])

                # Proactive suggestions
                proactive_suggestions = proactive_assistant.generate_proactive_suggestions({
                    'current_message': user_prompt,
                    'emotions': emotions,
                    'memories': relevant_memories
                })

                if proactive_suggestions:
                    yield f"event: proactive\ndata: {json.dumps(proactive_suggestions)}\n\n"

                # Save user message
                save_message_to_db(conversation_id, 'user', user_prompt)

                # Store important information
                if any(keyword in user_prompt.lower() for keyword in ['remember', 'important', 'deadline', 'meeting']):
                    memory_manager.store_memory('user_request', 'important_info', user_prompt, importance=1.5)

                # Load conversation history
                history = [{'role': msg.role, 'parts': [{'text': msg.content}]} for msg in conversation.messages]

                # Initialize Gemini
                chat_session = initialize_gemini(history=history)
                if not chat_session and UTILS_AVAILABLE:
                    yield f"data: {json.dumps({'text': 'I apologize, but I am currently unable to connect to my AI service. Please check your API configuration and try again.'})}\n\n"
                    return

                # Prepare enhanced prompt
                enhanced_prompt = user_prompt

                if memory_context:
                    context_prefix = f"[Context: {memory_context[:500]}...]\n[Mood: {emotions}]\n\n"
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
                    prompt_parts.append(f"Real-time info: '{context}'. Answer: '{enhanced_prompt}'")
                else:
                    prompt_parts.append(enhanced_prompt)

                # Sentiment analysis
                sentiment_scores = analyze_sentiment(user_prompt or " ")
                yield f"event: sentiment\ndata: {json.dumps(sentiment_scores)}\n\n"

                # Generate response
                stream_generator = get_response_stream(chat_session, prompt_parts)
                for chunk_text in stream_generator:
                    full_bot_response += chunk_text
                    yield f"data: {json.dumps({'text': chunk_text})}\n\n"

                # Save bot response
                save_message_to_db(conversation_id, 'model', full_bot_response)

                # Store interaction patterns
                memory_manager.store_memory('interaction_pattern',
                                            f"query_type_{datetime.now().strftime('%Y%m%d')}",
                                            {'query': user_prompt, 'response_length': len(full_bot_response),
                                             'emotions': emotions})

                # Update conversation title
                if is_first_exchange:
                    title = get_conversation_title(user_prompt, full_bot_response)
                    if title:
                        conversation.title = title
                        db.session.commit()

            except Exception as e:
                logging.error(f"Error during response generation: {e}")
                yield f"event: error\ndata: {json.dumps({'error': 'A server error occurred.'})}\n\n"

    return Response(generate_and_save(), mimetype='text/event-stream')


# --- API Routes ---
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
        'id': getattr(m, 'id', 0),
        'type': getattr(m, 'memory_type', ''),
        'key': getattr(m, 'key', ''),
        'value': getattr(m, 'value', ''),
        'importance': getattr(m, 'importance_score', 1.0),
        'created_at': getattr(m, 'created_at', datetime.utcnow()).isoformat()
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


@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """Check if user is authenticated"""
    return jsonify({
        'authenticated': current_user.is_authenticated,
        'username': getattr(current_user, 'username', None) if current_user.is_authenticated else None,
        'user_id': getattr(current_user, 'id', None) if current_user.is_authenticated else None
    })


@app.route('/health')
def health_check():
    """Enhanced health check endpoint with database connectivity test"""
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        db_status = 'connected'
        db_type = 'PostgreSQL' if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'SQLite'
    except Exception as e:
        logging.error(f"Database health check failed: {e}")
        db_status = f'error: {str(e)}'
        db_type = 'unknown'

    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': {
            'status': db_status,
            'type': db_type,
            'url_configured': bool(os.environ.get('DATABASE_URL'))
        },
        'utils_available': UTILS_AVAILABLE,
        'environment': os.environ.get('FLASK_ENV', 'development')
    }), 200


@app.route('/favicon.ico')
def favicon():
    return '', 204


# --- Error Handlers ---
@app.errorhandler(401)
def unauthorized_error(error):
    if request.is_json:
        return jsonify({'error': 'Authentication required'}), 401
    flash('Please log in to access this page.', 'warning')
    return redirect(url_for('login'))


@app.errorhandler(403)
def forbidden_error(error):
    if request.is_json:
        return jsonify({'error': 'Access forbidden'}), 403
    flash('You do not have permission to access this resource.', 'error')
    return redirect(url_for('index'))


@app.errorhandler(404)
def not_found_error(error):
    try:
        return render_template('404.html'), 404
    except:
        return '<h1>404 - Page Not Found</h1>', 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    try:
        return render_template('500.html'), 500
    except:
        return '<h1>500 - Internal Server Error</h1>', 500


# --- Initialize Database with Migration Support ---
initialize_database_with_migration()

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
