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

# Import models first
from models import db, User, Conversation, Message, UserProfile, UserMemory, TaskAutomation, EmotionLog, ProactiveTask

# --- Basic App Setup ---
load_dotenv()
app = Flask(__name__)

# Enhanced session configuration
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a-very-secret-key-for-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

logging.basicConfig(level=logging.INFO)

# --- Database Configuration ---
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
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Initialize db with app
db.init_app(app)

# --- Login Manager Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
login_manager.session_protection = "strong"  # Enhanced session protection

# Import utility handlers
try:
    from utils.gemini_handler import initialize_gemini, get_response_stream, get_conversation_title
    from utils.analysis_handler import analyze_sentiment
    from utils.search_handler import is_realtime_query, fetch_realtime_info
    from utils.memory_handler import MemoryManager
    from utils.emotion_handler import EmotionAnalyzer
    from utils.proactive_handler import ProactiveAssistant
    from utils.automation_handler import TaskAutomationManager
except ImportError as e:
    logging.warning(f"Some utility modules not found: {e}")


    # Create fallback functions
    def initialize_gemini(history=None):
        return None


    def get_response_stream(chat_session, prompt_parts):
        yield "AI response functionality not available"


    def get_conversation_title(user_prompt, bot_response):
        return f"Chat: {user_prompt[:30]}..."


    def analyze_sentiment(text):
        return {'positive': 0.5, 'neutral': 0.3, 'negative': 0.2}


    def is_realtime_query(query):
        return False


    def fetch_realtime_info(query):
        return "Real-time info not available"


@login_manager.user_loader
def load_user(user_id):
    try:
        # Force fresh query to avoid caching issues
        user = db.session.execute(
            db.select(User).where(User.id == int(user_id))
        ).scalar_one_or_none()
        return user
    except Exception as e:
        logging.error(f"Error loading user {user_id}: {e}")
        return None


# FIXED: Session validation with proper exclusions
@app.before_request
def validate_session():
    """Enhanced session validation that doesn't interfere with logout"""
    # Skip validation for auth routes and static files
    excluded_endpoints = ['login', 'register', 'logout', 'force_logout', 'static']

    if request.endpoint in excluded_endpoints:
        return

    # Skip validation for logout-related requests
    if request.path.startswith('/logout') or 'logout' in request.path:
        return

    if current_user.is_authenticated:
        # Check session timeout only for authenticated routes
        if 'last_activity' in session:
            try:
                last_activity = datetime.fromisoformat(session['last_activity'])
                if datetime.utcnow() - last_activity > app.config['PERMANENT_SESSION_LIFETIME']:
                    logging.info(f"Session expired for user {current_user.username}")
                    logout_user()
                    session.clear()
                    flash('Your session has expired. Please log in again.', 'warning')
                    return redirect(url_for('login'))
            except (ValueError, TypeError):
                # Invalid timestamp, clear session
                logout_user()
                session.clear()
                return redirect(url_for('login'))

        # Update last activity
        session['last_activity'] = datetime.utcnow().isoformat()


def save_message_to_db(conversation_id, role, content):
    try:
        message = Message(role=role, content=content, conversation_id=conversation_id)
        db.session.add(message)
        db.session.commit()
    except Exception as e:
        logging.error(f"Error saving message: {e}")
        db.session.rollback()


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

                # Login user with fresh session
                login_user(user, remember=True, fresh=True)
                session.permanent = True
                session['login_time'] = datetime.utcnow().isoformat()
                session['last_activity'] = datetime.utcnow().isoformat()
                session['user_id'] = user.id

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
            flash('Login failed. Please try again.', 'error')
            return render_template('login.html', error="Login failed.")

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Basic validation
        if not username or len(username) < 3:
            flash('Username must be at least 3 characters long.', 'error')
            return render_template('register.html', error="Username too short.")

        if not password or len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('register.html', error="Password too short.")

        try:
            user = User.query.filter_by(username=username).first()
            if user:
                flash('Username already exists. Please choose a different one.', 'error')
                return render_template('register.html', error="Username already exists.")

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


# FIXED: Enhanced logout with complete session cleanup
@app.route('/logout')
@login_required
def logout():
    username = getattr(current_user, 'username', 'Unknown')
    user_id = getattr(current_user, 'id', 'Unknown')

    try:
        logging.info(f"User {username} (ID: {user_id}) initiating logout")

        # Store logout info before clearing
        logout_time = datetime.utcnow()

        # Clear Flask-Login session
        logout_user()

        # Completely clear session
        session.clear()

        # Create clean response
        response = redirect(url_for('login'))

        # Clear all cookies
        response.set_cookie('session', '', expires=0, secure=True, httponly=True)
        response.set_cookie('remember_token', '', expires=0, secure=True, httponly=True)

        # Add cache control headers
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

        flash('You have been successfully logged out.', 'info')
        logging.info(f"User {username} logged out successfully at {logout_time}")

        return response

    except Exception as e:
        logging.error(f"Error during logout: {e}")
        # Force logout even if there's an error
        session.clear()
        response = redirect(url_for('login'))
        response.set_cookie('session', '', expires=0)
        flash('Logout completed.', 'info')
        return response


# Emergency logout route
@app.route('/force-logout')
def force_logout():
    """Emergency logout that clears everything"""
    try:
        if current_user.is_authenticated:
            username = current_user.username
            logout_user()
            logging.info(f"Force logout executed for user: {username}")

        session.clear()
        response = redirect(url_for('login'))
        response.set_cookie('session', '', expires=0)
        response.set_cookie('remember_token', '', expires=0)
        flash('Emergency logout completed.', 'info')
        return response

    except Exception as e:
        logging.error(f"Error during force logout: {e}")
        session.clear()
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
        logging.error(f"Error creating conversation: {e}")
        db.session.rollback()
        flash('Error creating conversation. Please try again.', 'error')
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
        logging.error(f"Error loading conversation: {e}")
        return redirect(url_for('index'))


@app.route("/chat", methods=["POST"])
@login_required
def chat():
    user_prompt = request.form.get("prompt", "")
    conversation_id = request.form.get("conversation_id", type=int)

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

                save_message_to_db(conversation_id, 'user', user_prompt)

                # Simple response for now
                full_bot_response = f"Echo: {user_prompt}"

                yield f"data: {json.dumps({'text': full_bot_response})}\n\n"

                save_message_to_db(conversation_id, 'model', full_bot_response)

            except Exception as e:
                logging.error(f"Error during response generation: {e}")
                yield f"event: error\ndata: {json.dumps({'error': 'A server error occurred.'})}\n\n"

    return Response(generate_and_save(), mimetype='text/event-stream')


# --- Error Handlers ---
@app.errorhandler(401)
def unauthorized_error(error):
    if request.is_json:
        return jsonify({'error': 'Authentication required'}), 401
    flash('Please log in to access this page.', 'warning')
    return redirect(url_for('login'))


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logging.error(f"Internal server error: {error}")
    return render_template('500.html'), 500


# --- Create Database and Run App ---
with app.app_context():
    try:
        db.create_all()
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Database creation error: {e}")

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
