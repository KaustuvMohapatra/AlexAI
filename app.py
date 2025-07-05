import os
import logging
import json
import io
import re
import sys
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

# Enhanced session configuration for Railway deployment
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'a-very-secret-key-for-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Railway-specific session configuration
if os.environ.get('RAILWAY_ENVIRONMENT'):
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_DOMAIN'] = None
else:
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

logging.basicConfig(level=logging.INFO)


# --- Environment Detection ---
def get_environment():
    """Detect current environment"""
    if os.environ.get('RAILWAY_ENVIRONMENT'):
        return 'railway'
    elif os.environ.get('DATABASE_URL'):
        return 'production'
    else:
        return 'development'


# --- Validation Helper Functions ---
def validate_username(username):
    """Enhanced username validation with detailed error messages"""
    errors = []

    if not username:
        errors.append({
            'field': 'username',
            'message': 'Username is required!',
            'code': 'REQUIRED'
        })
        return errors

    username = username.strip()

    if len(username) < 3:
        errors.append({
            'field': 'username',
            'message': 'Username must be at least 3 characters long!',
            'code': 'TOO_SHORT'
        })

    if len(username) > 50:
        errors.append({
            'field': 'username',
            'message': 'Username must be less than 50 characters long!',
            'code': 'TOO_LONG'
        })

    # Check for valid characters (alphanumeric and underscore only)
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        errors.append({
            'field': 'username',
            'message': 'Username can only contain letters, numbers, and underscores!',
            'code': 'INVALID_CHARACTERS'
        })

    # Check if username starts with a letter
    if not username[0].isalpha():
        errors.append({
            'field': 'username',
            'message': 'Username must start with a letter!',
            'code': 'INVALID_START'
        })

    return errors


def validate_password(password):
    """Enhanced password validation with detailed error messages"""
    errors = []

    if not password:
        errors.append({
            'field': 'password',
            'message': 'Password is required!',
            'code': 'REQUIRED'
        })
        return errors

    if len(password) < 6:
        errors.append({
            'field': 'password',
            'message': 'Password must be at least 6 characters long!',
            'code': 'TOO_SHORT'
        })

    if len(password) > 128:
        errors.append({
            'field': 'password',
            'message': 'Password must be less than 128 characters long!',
            'code': 'TOO_LONG'
        })

    # Check for at least one letter
    if not re.search(r'[A-Za-z]', password):
        errors.append({
            'field': 'password',
            'message': 'Password must contain at least one letter!',
            'code': 'NO_LETTER'
        })

    # Check for at least one number
    if not re.search(r'[0-9]', password):
        errors.append({
            'field': 'password',
            'message': 'Password must contain at least one number!',
            'code': 'NO_NUMBER'
        })

    return errors


def validate_form_data(username, password, check_existing_user=False):
    """Comprehensive form validation"""
    errors = []

    # Validate username
    username_errors = validate_username(username)
    errors.extend(username_errors)

    # Validate password
    password_errors = validate_password(password)
    errors.extend(password_errors)

    # Check if username already exists (for registration)
    if check_existing_user and username and len(username) >= 3:
        try:
            existing_user = User.query.filter_by(username=username.strip()).first()
            if existing_user:
                errors.append({
                    'field': 'username',
                    'message': 'Username already exists. Please choose a different one!',
                    'code': 'ALREADY_EXISTS'
                })
        except Exception as e:
            logging.error(f"Error checking existing user: {e}")
            errors.append({
                'field': 'general',
                'message': 'Database error occurred. Please try again.',
                'code': 'DATABASE_ERROR'
            })

    return errors


# --- Enhanced PostgreSQL Database Configuration for Railway ---
def configure_database():
    """Enhanced database configuration with Railway-specific optimizations"""
    DATABASE_URL = os.environ.get('DATABASE_URL')
    environment = get_environment()

    logging.info(f"Running in {environment} environment")

    if DATABASE_URL:
        logging.info("Configuring PostgreSQL database for production")

        # Validate DATABASE_URL format
        if not DATABASE_URL.startswith(('postgres://', 'postgresql://')):
            logging.error(f"Invalid DATABASE_URL format: {DATABASE_URL[:50]}...")
            raise ValueError("DATABASE_URL must start with postgres:// or postgresql://")

        # Handle Railway's postgres:// URL format
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
            logging.info("Converted postgres:// to postgresql:// URL format")

        # PostgreSQL configuration with Railway optimizations
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
        app.config['SQLALCHEMY_BINDS'] = {'chats': DATABASE_URL}

        # Railway-optimized engine options
        if environment == 'railway':
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'pool_size': 5,
                'pool_recycle': 300,
                'pool_pre_ping': True,
                'max_overflow': 10,
                'pool_timeout': 30,
                'connect_args': {
                    'connect_timeout': 10,
                    'application_name': 'AlexAI_Railway',
                    'sslmode': 'require'
                }
            }
        else:
            # Standard production settings
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'pool_size': 10,
                'pool_recycle': 120,
                'pool_pre_ping': True,
                'max_overflow': 20,
                'pool_timeout': 30,
                'connect_args': {
                    'connect_timeout': 10,
                    'application_name': 'AlexAI_Production'
                }
            }

        logging.info("PostgreSQL database configured successfully")

    else:
        # Development: SQLite fallback
        logging.info("No DATABASE_URL found, configuring SQLite for development")
        basedir = os.path.abspath(os.path.dirname(__file__))
        sqlite_path = os.path.join(basedir, 'app_data.db')

        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{sqlite_path}'
        app.config['SQLALCHEMY_BINDS'] = {'chats': f'sqlite:///{sqlite_path}'}

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

        # Add debug logging for user loading
        logging.debug(f"Loading user {user_id}: {'Found' if user else 'Not found'}")
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


# --- Enhanced Database Migration Functions ---
def check_database_migration():
    """Check if database migration is needed with proper error handling"""
    try:
        # Ensure we're in application context
        if not hasattr(app, 'app_context') or not app.app_context:
            raise RuntimeError("No application context available")

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
    """Perform database migration with enhanced error handling"""
    try:
        logging.info("Starting database migration...")

        # Ensure we're in application context
        if not hasattr(app, 'app_context') or not app.app_context:
            raise RuntimeError("No application context available")

        # Create all tables
        db.create_all()

        # Verify migration success
        db.session.execute(db.text('SELECT 1'))
        db.session.commit()

        logging.info("Database migration completed successfully")

    except Exception as e:
        logging.error(f"Database migration failed: {e}")
        db.session.rollback()
        raise


def initialize_database_with_migration():
    """Initialize database with proper application context and error handling"""
    try:
        with app.app_context():
            # Test database connection first
            try:
                db.session.execute(db.text('SELECT 1'))
                logging.info("Database connection successful")
            except Exception as conn_error:
                logging.error(f"Database connection failed: {conn_error}")

                # Check if we're in development and should fall back to SQLite
                if not os.environ.get('DATABASE_URL'):
                    logging.info("Falling back to SQLite for development")
                    basedir = os.path.abspath(os.path.dirname(__file__))
                    sqlite_path = os.path.join(basedir, 'emergency_fallback.db')
                    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{sqlite_path}'
                    app.config['SQLALCHEMY_BINDS'] = {'chats': f'sqlite:///{sqlite_path}'}

                    # Reinitialize db with new config
                    db.init_app(app)
                else:
                    raise conn_error

            # Check if migration is needed
            needs_migration = check_database_migration()

            if needs_migration:
                logging.info("Performing database migration...")
                perform_database_migration()
            else:
                logging.info("Database schema is up to date")

            # Final connection test
            db.session.execute(db.text('SELECT 1'))
            db.session.commit()

            # Log database info
            db_type = 'PostgreSQL' if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'SQLite'
            logging.info(f"Database initialization completed successfully using {db_type}")

    except Exception as e:
        logging.error(f"Database initialization failed: {e}")

        # Emergency fallback to SQLite
        try:
            logging.info("Attempting emergency fallback to SQLite...")
            basedir = os.path.abspath(os.path.dirname(__file__))
            sqlite_path = os.path.join(basedir, 'emergency_fallback.db')

            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{sqlite_path}'
            app.config['SQLALCHEMY_BINDS'] = {'chats': f'sqlite:///{sqlite_path}'}

            # Reinitialize with SQLite
            with app.app_context():
                db.create_all()
                logging.info("Emergency SQLite fallback successful")

        except Exception as fallback_error:
            logging.critical(f"Emergency fallback failed: {fallback_error}")
            raise RuntimeError("Complete database initialization failure") from e


# --- Debug Routes (Remove in production) ---
@app.route('/debug/users')
def debug_users():
    """Debug route to check user count"""
    try:
        users = User.query.all()
        user_list = [{'id': u.id, 'username': u.username} for u in users]
        return jsonify({
            'total_users': len(users),
            'users': user_list
        })
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/debug/create-test-user')
def create_test_user():
    """Debug route to create a test user"""
    try:
        # Check if test user already exists
        existing_user = User.query.filter_by(username='admin').first()
        if existing_user:
            return jsonify({'message': 'Test user already exists', 'username': 'admin'})

        # Create test user
        test_user = User(username='admin')
        test_user.set_password('password123')
        db.session.add(test_user)
        db.session.commit()

        return jsonify({
            'message': 'Test user created successfully',
            'username': 'admin',
            'password': 'password123'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error creating test user: {e}'})


@app.route('/debug/db-status')
def debug_db_status():
    """Debug route to check database status"""
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))

        # Count tables
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()

        # Count users
        user_count = User.query.count()

        return jsonify({
            'database_connected': True,
            'tables': tables,
            'user_count': user_count,
            'database_url': app.config['SQLALCHEMY_DATABASE_URI'][:50] + '...',
            'environment': get_environment()
        })
    except Exception as e:
        return jsonify({'error': str(e)})


# --- Enhanced Session Validation Middleware ---
@app.before_request
def validate_session():
    """Enhanced session validation that doesn't interfere with logout"""
    # Skip validation for static files, auth routes, and debug routes
    skip_endpoints = ['static', 'login', 'register', 'logout', 'force_logout', 'health_check',
                      'favicon', 'validate_field', 'debug_users', 'create_test_user', 'debug_db_status']

    if request.endpoint in skip_endpoints:
        return

    # Skip validation for API routes that don't require auth
    if request.path.startswith('/api/auth/status') or request.path.startswith(
            '/api/validate') or request.path.startswith('/debug'):
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


# --- Enhanced Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Handle both form data and JSON requests
        if request.is_json:
            data = request.get_json()
            username = data.get('username', '').strip()
            password = data.get('password', '')
        else:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

        # Add debug logging
        logging.info(f"Login attempt for username: {username}")

        # Validate input
        validation_errors = validate_form_data(username, password, check_existing_user=False)

        if validation_errors:
            error_response = {
                'success': False,
                'errors': validation_errors,
                'message': validation_errors[0]['message']
            }

            if request.is_json:
                return jsonify(error_response), 400
            else:
                flash(validation_errors[0]['message'], 'error')
                return render_template('login.html',
                                       error=validation_errors[0]['message'],
                                       validation_errors=validation_errors)

        try:
            user = User.query.filter_by(username=username).first()
            logging.info(f"User query result: {'Found' if user else 'Not found'}")

            if user and user.check_password(password):
                # Clear any existing session data
                session.clear()

                # Login user
                login_user(user, remember=True)
                session.permanent = True
                session['login_time'] = datetime.utcnow().isoformat()
                session['last_activity'] = datetime.utcnow().isoformat()

                success_message = f'Welcome back, {user.username}!'
                logging.info(f"User {user.username} logged in successfully")

                if request.is_json:
                    next_page = request.json.get('next') or url_for('index')
                    return jsonify({
                        'success': True,
                        'message': success_message,
                        'redirect': next_page
                    })
                else:
                    flash(success_message, 'success')
                    next_page = request.args.get('next')
                    return redirect(next_page) if next_page else redirect(url_for('index'))
            else:
                error_msg = 'Invalid username or password!'
                logging.warning(f"Login failed for username: {username}")

                if request.is_json:
                    return jsonify({
                        'success': False,
                        'field': 'password',
                        'message': error_msg
                    }), 401
                else:
                    flash(error_msg, 'error')
                    return render_template('login.html', error=error_msg)

        except Exception as e:
            logging.error(f"Login error: {e}")
            error_msg = 'An error occurred during login. Please try again.'

            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 500
            else:
                flash(error_msg, 'error')
                return render_template('login.html', error=error_msg)

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Handle both form data and JSON requests
        if request.is_json:
            data = request.get_json()
            username = data.get('username', '').strip()
            password = data.get('password', '')
        else:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

        # Comprehensive validation
        validation_errors = validate_form_data(username, password, check_existing_user=True)

        if validation_errors:
            error_response = {
                'success': False,
                'errors': validation_errors,
                'message': validation_errors[0]['message']
            }

            if request.is_json:
                return jsonify(error_response), 400
            else:
                for error in validation_errors:
                    flash(error['message'], 'error')
                return render_template('register.html',
                                       errors=validation_errors,
                                       error=validation_errors[0]['message'])

        try:
            # Create new user
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            success_message = 'Registration successful! Please log in.'
            logging.info(f"New user registered: {username}")

            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': success_message,
                    'redirect': url_for('login')
                })
            else:
                flash(success_message, 'success')
                return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
            logging.error(f"Registration error: {e}")
            error_msg = 'Registration failed. Please try again.'

            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 500
            else:
                flash(error_msg, 'error')
                return render_template('register.html', error=error_msg)

    return render_template('register.html')


# --- Real-time Validation API ---
@app.route('/api/validate/field', methods=['POST'])
def validate_field():
    """Real-time field validation API"""
    try:
        data = request.get_json()
        field_name = data.get('field')
        field_value = data.get('value', '')

        errors = []

        if field_name == 'username':
            errors = validate_username(field_value)

            # Check if username exists (only if no other errors)
            if not errors and field_value:
                try:
                    existing_user = User.query.filter_by(username=field_value.strip()).first()
                    if existing_user:
                        errors.append({
                            'field': 'username',
                            'message': 'Username already exists!',
                            'code': 'ALREADY_EXISTS'
                        })
                except Exception as e:
                    logging.error(f"Error checking username availability: {e}")

        elif field_name == 'password':
            errors = validate_password(field_value)

        return jsonify({
            'valid': len(errors) == 0,
            'errors': errors
        })

    except Exception as e:
        logging.error(f"Field validation error: {e}")
        return jsonify({
            'valid': False,
            'errors': [{
                'field': 'general',
                'message': 'Validation error occurred',
                'code': 'VALIDATION_ERROR'
            }]
        }), 500


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
        'environment': get_environment()
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


# --- Main Application Entry Point ---
if __name__ == "__main__":
    # Initialize database only when running the app directly
    try:
        initialize_database_with_migration()
        logging.info("Application startup successful")
    except Exception as e:
        logging.critical(f"Application startup failed: {e}")
        sys.exit(1)

    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
else:
    # For production deployments (gunicorn, etc.)
    try:
        initialize_database_with_migration()
        logging.info("Production application initialization successful")
    except Exception as e:
        logging.critical(f"Production application initialization failed: {e}")
        # Don't exit in production, let the deployment handle the error