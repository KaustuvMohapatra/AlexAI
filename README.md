# Alex AI Assistant - Advanced Voice-Powered AI Chat Application

A sophisticated Flask-based AI assistant featuring voice interaction, emotion recognition, proactive suggestions, memory management, and intelligent task automation.

## 🌟 Features

### Core Capabilities
- **🎙️ Voice-Powered Interaction**: Speech-to-text with automatic submission
- **🖼️ Multimodal Support**: Text, voice, and image processing capabilities
- **⚡ Real-time Streaming**: Live response generation with Server-Sent Events
- **💬 Conversation Management**: Persistent chat history with context awareness
- **🔐 Secure Authentication**: User registration, login, and session management

### Advanced AI Features
- **😊 Emotion Recognition**: Analyzes user sentiment and adjusts responses accordingly
- **🧠 Memory Management**: Remembers important information across conversations
- **💡 Proactive Assistance**: Anticipates user needs and offers intelligent suggestions
- **🤖 Task Automation**: Custom triggers for routine actions and workflows
- **🎯 Context Awareness**: Maintains conversation context and user preferences

### User Experience
- **🌙 Dark/Light Theme**: Seamless theme switching with localStorage persistence
- **🔊 Text-to-Speech**: Optional voice output for AI responses
- **📸 Image Upload**: Visual content analysis and processing
- **📱 Responsive Design**: Optimized for desktop and mobile devices
- **⌨️ Keyboard Shortcuts**: Efficient navigation and controls

## 🏗️ Architecture

### Backend Structure
```
app.py                    # Main Flask application with all routes
models.py                 # Database models and schemas
utils/
├── gemini_handler.py     # Google Gemini AI integration
├── emotion_handler.py    # Emotion analysis and tracking
├── memory_handler.py     # User memory management system
├── proactive_handler.py  # Proactive suggestions engine
├── automation_handler.py # Task automation system
├── analysis_handler.py   # Sentiment analysis utilities
└── search_handler.py     # Real-time search capabilities
```

### Frontend Components
```
templates/
├── index.html           # Main chat interface
├── login.html          # User authentication
└── register.html       # User registration
static/
├── style.css           # Responsive styling with theme support
└── script.js           # Interactive functionality and voice features
```

### Database Schema
- **Users**: Authentication and user profiles
- **Conversations**: Chat sessions and metadata
- **Messages**: Individual chat messages with timestamps
- **UserMemory**: Persistent user information and preferences
- **EmotionLog**: Emotion tracking and analysis history
- **TaskAutomation**: Custom automation rules and triggers
- **ProactiveTask**: Scheduled suggestions and reminders

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Git for version control
- Modern web browser with microphone support

### Local Development Setup

1. **Clone the repository**
```bash
git clone https://github.com/KaustuvMohapatra/AlexAI.git
cd AlexAI
```

2. **Create and activate virtual environment**
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment configuration**
```bash
# Create .env file with your configuration
FLASK_SECRET_KEY=your-super-secure-secret-key-here
GEMINI_API_KEY=your-google-gemini-api-key
FLASK_ENV=development
DEBUG=True
```

5. **Initialize database**
```bash
python app.py
# Database tables will be created automatically on first run
```

6. **Access the application**
```
Open your browser and navigate to: http://localhost:5000
```

## ⚙️ Configuration

### Environment Variables
```env
FLASK_SECRET_KEY=your-secret-key-here
GEMINI_API_KEY=your-gemini-api-key
DATABASE_URL=sqlite:///app.db
FLASK_ENV=production
DEBUG=False
PORT=5000
```

### Feature Configuration
- **Voice Recognition**: Automatically enabled in supported browsers
- **Theme Persistence**: Stored in browser localStorage
- **Memory Retention**: Configurable importance scoring system
- **Automation Triggers**: User-customizable phrase detection

## 🎯 Usage Guide

### Getting Started
1. **Register** a new account or **login** with existing credentials
2. **Start chatting** by typing messages or using voice input
3. **Upload images** for visual analysis and discussion
4. **Customize settings** including theme preferences and automation

### Voice Features
- **Click the microphone button** (🎙️) to start voice recognition
- **Speak naturally** - text appears automatically in the input field
- **Auto-submission** occurs after speech recognition completes
- **Toggle TTS** (🔊/🔇) for voice responses from the AI

### Advanced Features

#### Automation Setup
Create custom automation triggers for routine tasks:
```javascript
// Example: Morning routine
Trigger: "good morning"
Actions: [
  { type: 'weather_update', priority: 1 },
  { type: 'calendar_events', priority: 2 },
  { type: 'daily_motivation', priority: 3 }
]
```

#### Memory Management
- Important information is automatically stored and recalled
- Use keywords like "remember", "important", "deadline", "meeting"
- Context persists across conversation sessions
- Memory importance scoring for relevance

#### Proactive Suggestions
- **Break reminders** during extended work sessions
- **Deadline alerts** extracted from conversation history
- **Learning resource suggestions** based on topics discussed
- **Productivity pattern analysis** and recommendations

## 🔧 API Reference

### Chat Endpoint
```http
POST /chat
Content-Type: multipart/form-data

Parameters:
- prompt: string (required) - User's message
- conversation_id: integer (required) - Active conversation ID
- image: file (optional) - Image file for analysis
```

### Management APIs
```http
# Memory management
GET /api/memories?query=search_term&limit=10

# Emotion trends
GET /api/emotions/trend?hours=24

# Automation management
GET /api/automations
POST /api/automations

# User profile
GET /api/user/profile
POST /api/user/profile

# Dashboard statistics
GET /api/stats/dashboard

# Authentication status
GET /api/auth/status
```

## 🚀 Deployment

### Railway Deployment (Recommended)

1. **Prepare deployment files**

Create `requirements.txt`:
```txt
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
python-dotenv==1.0.0
Werkzeug==2.3.7
Pillow==10.0.1
scikit-learn==1.3.0
textblob==0.17.1
requests==2.31.0
google-generativeai==0.3.0
gunicorn==21.2.0
```

Create `Procfile`:
```
web: python app.py
```

2. **Connect to Railway**
- Push your code to GitHub
- Connect your repository to Railway
- Railway automatically detects it as a Python application

3. **Configure environment variables in Railway dashboard**
```
FLASK_SECRET_KEY=your-production-secret-key
GEMINI_API_KEY=your-gemini-api-key
FLASK_ENV=production
PORT=5000
```

4. **Deploy and monitor**
- Railway automatically builds and deploys your application
- Monitor logs for any deployment issues
- Test all features once deployed

### Alternative Deployment Options

#### Heroku
```bash
# Install Heroku CLI and login
heroku create your-app-name
heroku config:set FLASK_SECRET_KEY=your-secret-key
heroku config:set GEMINI_API_KEY=your-gemini-key
git push heroku main
```

#### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

#### VPS/Cloud Server
```bash
# Install dependencies
sudo apt update && sudo apt install python3 python3-pip nginx
pip3 install -r requirements.txt

# Run with Gunicorn
gunicorn --bind 0.0.0.0:5000 app:app
```

## 🔒 Security Features

- **Session Management**: Secure Flask-Login with automatic timeout
- **Input Validation**: File type and size restrictions for uploads
- **CSRF Protection**: Built-in Flask security measures
- **Authentication Required**: All chat endpoints require valid login
- **Data Isolation**: User-specific data separation and access control
- **Password Hashing**: Secure password storage with Werkzeug
- **Session Cleanup**: Comprehensive logout with session clearing

## 🧪 Testing

### Manual Testing Checklist
- [ ] **Authentication Flow**: Register → Login → Chat → Logout
- [ ] **Voice Features**: Speech recognition and text-to-speech
- [ ] **Theme Switching**: Dark/light mode persistence
- [ ] **Image Upload**: File validation and AI analysis
- [ ] **Automation**: Trigger phrase detection and execution
- [ ] **Memory**: Information storage and retrieval
- [ ] **Emotion Analysis**: Sentiment detection and response adaptation
- [ ] **Proactive Suggestions**: Context-aware recommendations

### Browser Compatibility
- **Chrome/Chromium**: Full feature support including voice recognition
- **Firefox**: Full feature support with voice recognition
- **Safari**: Limited voice recognition support
- **Edge**: Full feature support including voice recognition

## 📊 Performance & Optimization

### Built-in Optimizations
- **Streaming Responses**: Real-time message delivery with SSE
- **Memory Management**: Automatic cleanup of old emotion logs
- **Database Indexing**: Optimized queries for conversation loading
- **Static Asset Caching**: Browser caching for CSS/JS files
- **Session Timeout**: Automatic cleanup of inactive sessions

### Resource Usage
- **Memory**: ~50MB base + conversation data
- **Storage**: SQLite databases (users.db, chats.db)
- **Network**: Minimal bandwidth usage for chat data
- **CPU**: Efficient processing with background AI analysis

## 🐛 Troubleshooting

### Common Issues

**Voice recognition not working**
- Check browser permissions for microphone access
- Ensure HTTPS connection (required for speech API)
- Verify browser compatibility with Web Speech API

**Theme not persisting**
- Check if localStorage is enabled in browser
- Clear browser cache if theme data is corrupted
- Verify JavaScript is enabled

**Database errors on startup**
- Delete existing database files and restart application
- Check file permissions in project directory
- Verify SQLAlchemy configuration

**AI features not responding**
- Verify GEMINI_API_KEY is correctly set
- Check internet connection for API access
- Review application logs for specific error messages

**Memory/automation not working**
- Verify all utility files are properly imported
- Check database model synchronization
- Ensure proper user authentication

## 🤝 Contributing

### Development Guidelines
1. **Fork the repository** and create a feature branch
2. **Follow PEP 8** Python coding standards
3. **Test thoroughly** before submitting pull requests
4. **Update documentation** for new features
5. **Maintain backward compatibility** when possible

### Code Standards
- **Python**: Follow PEP 8 guidelines with 4-space indentation
- **JavaScript**: Use ES6+ features and consistent formatting
- **CSS**: Maintain responsive design principles
- **Documentation**: Update README for significant changes

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Google Gemini**: AI model integration and natural language processing
- **Flask**: Robust web framework foundation
- **Highlight.js**: Code syntax highlighting in chat responses
- **Markdown-it**: Markdown rendering for formatted responses
- **Roboto Font**: Clean and readable typography
- **Railway**: Seamless deployment platform

## 📞 Support

For issues, feature requests, or questions:
- **Create an issue** in the GitHub repository
- **Check existing documentation** and troubleshooting section
- **Review logs** for specific error messages

**Alex AI Assistant** - Bringing intelligent conversation to your fingertips with advanced voice capabilities, emotional intelligence, and proactive assistance features.
