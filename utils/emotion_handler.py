from datetime import datetime, timedelta
from flask import current_app
from models import db, EmotionLog

try:
    from textblob import TextBlob

    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False


class EmotionAnalyzer:
    def __init__(self):
        self.stress_indicators = [
            'stressed', 'overwhelmed', 'anxious', 'worried', 'frustrated',
            'tired', 'exhausted', 'deadline', 'urgent', 'pressure'
        ]

        self.happiness_indicators = [
            'happy', 'excited', 'great', 'awesome', 'wonderful',
            'fantastic', 'amazing', 'love', 'perfect', 'excellent'
        ]

    def analyze_emotion(self, text, user_id, conversation_id):
        """Analyze emotion from text"""
        if TEXTBLOB_AVAILABLE:
            blob = TextBlob(text.lower())
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
        else:
            # Simple fallback analysis
            polarity = 0.0
            subjectivity = 0.5

        # Pattern-based emotion detection
        text_lower = text.lower()
        stress_score = sum(1 for word in self.stress_indicators if word in text_lower) / max(len(text.split()), 1)
        happiness_score = sum(1 for word in self.happiness_indicators if word in text_lower) / max(len(text.split()), 1)

        # Calculate emotion scores
        emotions = {
            'happiness': max(0, polarity) + happiness_score,
            'stress': stress_score + max(0, -polarity),
            'neutral': 1 - abs(polarity),
            'confidence': subjectivity
        }

        # Normalize scores
        total = sum(emotions.values())
        if total > 0:
            emotions = {k: v / total for k, v in emotions.items()}

        # Store emotion log with CORRECT column name
        try:
            emotion_log = EmotionLog(
                user_id=user_id,
                conversation_id=conversation_id,
                emotions=emotions  # ✅ Changed from 'emotion_scores' to 'emotions'
            )

            db.session.add(emotion_log)
            db.session.commit()

        except Exception as e:
            logging.error(f"Error storing emotion log: {e}")
            db.session.rollback()

        return emotions

    def get_emotion_trend(self, user_id, hours=24):
        """Get recent emotion trends"""
        since = datetime.utcnow() - timedelta(hours=hours)

        try:
            logs = EmotionLog.query.filter(
                EmotionLog.user_id == user_id,
                EmotionLog.created_at >= since  # ✅ Changed from 'detected_at' to 'created_at'
            ).all()

            if not logs:
                return {'happiness': 0.5, 'stress': 0.3, 'neutral': 0.2}

            # Average emotions over time period
            avg_emotions = {'happiness': 0, 'stress': 0, 'neutral': 0}
            for log in logs:
                # Access the emotions JSON field correctly
                emotion_data = log.emotions if log.emotions else {}
                for emotion, score in emotion_data.items():
                    if emotion in avg_emotions:
                        avg_emotions[emotion] += score

            count = len(logs)
            return {k: v / count for k, v in avg_emotions.items()}

        except Exception as e:
            logging.error(f"Error retrieving emotion trend: {e}")
            return {'happiness': 0.5, 'stress': 0.3, 'neutral': 0.2}
