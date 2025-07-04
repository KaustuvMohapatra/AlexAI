# Alex - AI-Powered Voice Assistant

A sophisticated Flask-based AI assistant with advanced voice capabilities, emotion recognition, proactive suggestions, and intelligent automation features.

## 🌟 Features

### Core Capabilities
- **Voice-Powered Interaction**: Speech-to-text with auto-submission
- **Multimodal Support**: Text, voice, and image processing
- **Real-time Streaming**: Live response generation with SSE
- **Conversation Management**: Persistent chat history and context
- **User Authentication**: Secure login/registration system

### Advanced AI Features
- **Emotion Recognition**: Analyzes user sentiment and adjusts responses
- **Memory Management**: Remembers important information across conversations
- **Proactive Assistance**: Anticipates user needs and offers suggestions
- **Task Automation**: Custom triggers for routine actions
- **Context Awareness**: Maintains conversation context and user preferences

### User Experience
- **Dark/Light Theme**: Seamless theme switching with persistence
- **Text-to-Speech**: Optional voice output for responses
- **Image Upload**: Visual content analysis capabilities
- **Responsive Design**: Works across desktop and mobile devices
- **Keyboard Shortcuts**: Efficient navigation and controls

## 🏗️ Architecture

### Backend (Flask)
```
app.py                 # Main Flask application
models.py              # Database models and schemas
utils/
├── gemini_handler.py  # AI model integration
├── emotion_handler.py # Emotion analysis
├── memory_handler.py  # Memory management
├── proactive_handler.py # Proactive suggestions
├── automation_handler.py # Task automation
├── analysis_handler.py # Sentiment analysis
└── search_handler.py  # Real-time search
```

### Frontend
```
templates/
├── index.html         # Main chat interface
├── login.html         # Authentication pages
└── register.html
static/
├── style.css          # Responsive styling
└── script.js          # Interactive functionality
```

### Database Schema
- **Users**: Authentication and user profiles
- **Conversations**: Chat sessions and metadata
- **Messages**: Individual chat messages
- **UserMemory**: Persistent user information
- **EmotionLog**: Emotion tracking history
- **TaskAutomation**: Custom automation rules
- **ProactiveTask**: Scheduled suggestions

## 🚀 Installation

### Prerequisites
- Python 3.8+
- Node.js (for frontend dependencies)
- SQLite (included with Python)

### Setup Instructions

1. **Clone the repository**
```bash
git clone 
cd alex-ai-assistant
```

2. **Create virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment configuration**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize database**
```bash
python app.py
# Database tables will be created automatically
```

6. **Run the application**
```bash
python app.py
```

Visit `http://localhost:5000` to access the application.

## ⚙️ Configuration

### Environment Variables
```env
FLASK_SECRET_KEY=your-secret-key-here
GEMINI_API_KEY=your-gemini-api-key
DATABASE_URL=sqlite:///app.db
DEBUG=True
```

### Feature Configuration
- **Voice Recognition**: Automatically enabled in supported browsers
- **Theme Persistence**: Stored in localStorage
- **Memory Retention**: Configurable importance scoring
- **Automation Triggers**: User-customizable phrases

## 🎯 Usage Guide

### Basic Chat
1. Register/login to access the interface
2. Type messages or use voice input (🎙️ button)
3. Upload images for visual analysis
4. Switch themes using the theme toggle (🌙/☀️)

### Voice Features
- **Click microphone** to start voice recognition
- **Speak naturally** - text appears automatically
- **Auto-submission** after speech recognition completes
- **Toggle TTS** for voice responses

### Advanced Features

#### Automation Setup
```javascript
// Example: Morning routine automation
Trigger: "good morning"
Actions: [
  { type: 'weather_update' },
  { type: 'calendar_events' },
  { type: 'daily_motivation' }
]
```

#### Memory Management
- Important information is automatically stored
- Use keywords like "remember", "important", "deadline"
- Context persists across conversation sessions

#### Proactive Suggestions
- Break reminders during long sessions
- Deadline alerts from conversation history
- Learning resource suggestions
- Productivity pattern analysis

## 🔧 API Reference

### Chat Endpoint
```http
POST /chat
Content-Type: multipart/form-data

Parameters:
- prompt: string (required)
- conversation_id: integer (required)
- image: file (optional)
```

### Management APIs
```http
GET /api/memories?query=search_term
GET /api/emotions/trend?hours=24
GET /api/automations
POST /api/automations
GET /api/stats/dashboard
```

## 🎨 Customization

### Theme Customization
Modify CSS variables in `style.css`:
```css
:root {
    --primary-color: #your-color;
    --bg-color: #your-background;
    /* ... other variables */
}
```

### Adding New Automation Actions
1. Extend `TaskAutomationManager` in `automation_handler.py`
2. Add action type to `_execute_single_action` method
3. Implement action logic

### Custom Proactive Suggestions
1. Add suggestion logic to `ProactiveAssistant`
2. Define trigger conditions
3. Specify action recommendations

## 🔒 Security Features

- **Session Management**: Flask-Login with secure sessions
- **Input Validation**: File type and size restrictions
- **CSRF Protection**: Built-in Flask security
- **Authentication**: Required for all chat endpoints
- **Data Isolation**: User-specific data separation

## 🧪 Testing

### Manual Testing
1. **Authentication Flow**: Register → Login → Chat
2. **Voice Features**: Speech recognition and TTS
3. **Theme Switching**: Dark/light mode persistence
4. **Image Upload**: File validation and processing
5. **Automation**: Trigger phrase detection

### Browser Compatibility
- **Chrome**: Full feature support
- **Firefox**: Full feature support
- **Safari**: Limited voice recognition
- **Edge**: Full feature support

## 📊 Performance

### Optimization Features
- **Streaming Responses**: Real-time message delivery
- **Lazy Loading**: Conversation history pagination
- **Memory Management**: Automatic cleanup of old data
- **Caching**: Static asset optimization

### Resource Usage
- **Memory**: ~50MB base + conversation data
- **Storage**: SQLite databases (users.db, chats.db)
- **Network**: Minimal - only chat data transfer

## 🐛 Troubleshooting

### Common Issues

**Voice recognition not working**
- Check browser permissions for microphone
- Ensure HTTPS connection (required for speech API)
- Verify browser compatibility

**Theme not persisting**
- Check localStorage availability
- Clear browser cache if corrupted

**Database errors**
- Delete database files and restart application
- Check file permissions in project directory

**Memory/automation not working**
- Verify utility file imports
- Check database model synchronization

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Make changes and test thoroughly
4. Submit pull request with detailed description

### Code Standards
- **Python**: Follow PEP 8 guidelines
- **JavaScript**: Use ES6+ features
- **CSS**: Maintain responsive design principles
- **Documentation**: Update README for new features

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Google Gemini**: AI model integration
- **Flask**: Web framework foundation
- **Highlight.js**: Code syntax highlighting
- **Markdown-it**: Markdown rendering
- **Roboto Font**: Typography

## 📞 Support

For issues, feature requests, or questions:
- Create an issue in the repository
- Check existing documentation
- Review troubleshooting section

**Alex AI Assistant** - Bringing intelligent conversation to your fingertips with voice, emotion, and proactive capabilities.
