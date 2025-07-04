from datetime import datetime, timedelta
from flask import current_app
from models import db, Message, Conversation, ProactiveTask
import json
import re


class ProactiveAssistant:
    def __init__(self, user_id):
        self.user_id = user_id
        self.work_session_threshold = 20  # messages
        self.break_reminder_interval = 90  # minutes

    def analyze_coding_patterns(self, current_message):
        """Analyze coding-related queries and suggest improvements"""
        coding_keywords = ['code', 'programming', 'debug', 'error', 'function', 'class', 'variable']
        suggestions = []

        if any(keyword in current_message.lower() for keyword in coding_keywords):
            # Check for common coding issues
            if 'error' in current_message.lower() or 'bug' in current_message.lower():
                suggestions.append({
                    'type': 'debug_assistance',
                    'message': "I notice you're dealing with an error. Would you like me to help debug this step by step?",
                    'actions': ['debug_walkthrough', 'error_analysis', 'suggest_fixes'],
                    'priority': 'high'
                })

            if 'optimize' in current_message.lower() or 'improve' in current_message.lower():
                suggestions.append({
                    'type': 'code_optimization',
                    'message': "I can help optimize your code for better performance and readability!",
                    'actions': ['performance_analysis', 'code_review', 'best_practices'],
                    'priority': 'medium'
                })

        return suggestions

    def check_work_session_duration(self):
        """Check if user needs a break reminder"""
        try:
            # Check recent conversation activity
            two_hours_ago = datetime.utcnow() - timedelta(hours=2)
            recent_messages = Message.query.join(Conversation).filter(
                Conversation.user_id == self.user_id,
                Message.created_at >= two_hours_ago
            ).count()

            if recent_messages > self.work_session_threshold:
                return {
                    'type': 'break_reminder',
                    'message': "You've been quite active for the past 2 hours! Consider taking a 10-15 minute break to recharge.",
                    'actions': ['suggest_break_activities', 'set_break_timer'],
                    'priority': 'medium'
                }
        except Exception as e:
            current_app.logger.error(f"Error checking work session duration: {e}")

        return None

    def check_upcoming_deadlines(self):
        """Check for upcoming deadlines mentioned in conversations"""
        try:
            # Search for deadline-related keywords in recent messages
            deadline_keywords = ['deadline', 'due date', 'submit by', 'finish by', 'complete by']
            suggestions = []

            # Look for messages containing deadline information
            recent_messages = Message.query.join(Conversation).filter(
                Conversation.user_id == self.user_id,
                Message.created_at >= datetime.utcnow() - timedelta(days=7)
            ).all()

            for message in recent_messages:
                content_lower = message.content.lower()
                if any(keyword in content_lower for keyword in deadline_keywords):
                    # Extract potential dates using regex
                    date_patterns = [
                        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # MM/DD/YYYY or MM-DD-YYYY
                        r'\b\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{2,4}\b',
                        r'\b(today|tomorrow|next week|this week)\b'
                    ]

                    for pattern in date_patterns:
                        matches = re.findall(pattern, content_lower, re.IGNORECASE)
                        if matches:
                            suggestions.append({
                                'type': 'deadline_alert',
                                'message': f"Reminder: You mentioned a deadline - '{message.content[:100]}...'",
                                'context': message.content,
                                'priority': 'high'
                            })
                            break

            return suggestions[:3]  # Limit to 3 most recent
        except Exception as e:
            current_app.logger.error(f"Error checking deadlines: {e}")
            return []

    def suggest_learning_resources(self, current_message):
        """Suggest learning resources based on user queries"""
        learning_keywords = ['learn', 'tutorial', 'how to', 'explain', 'understand', 'guide']
        suggestions = []

        if any(keyword in current_message.lower() for keyword in learning_keywords):
            # Identify the topic
            topics = {
                'python': ['python', 'django', 'flask', 'pandas'],
                'javascript': ['javascript', 'js', 'react', 'node'],
                'web': ['html', 'css', 'web development', 'frontend'],
                'data': ['data science', 'machine learning', 'ai', 'analytics'],
                'database': ['sql', 'database', 'mysql', 'postgresql']
            }

            detected_topic = None
            for topic, keywords in topics.items():
                if any(keyword in current_message.lower() for keyword in keywords):
                    detected_topic = topic
                    break

            if detected_topic:
                suggestions.append({
                    'type': 'learning_assistance',
                    'message': f"I can create a personalized {detected_topic} learning plan with resources and practice exercises!",
                    'actions': ['create_learning_plan', 'find_resources', 'practice_exercises'],
                    'topic': detected_topic,
                    'priority': 'medium'
                })

        return suggestions

    def check_productivity_patterns(self):
        """Analyze productivity patterns and suggest improvements"""
        try:
            suggestions = []

            # Check message frequency patterns
            now = datetime.utcnow()  # Use utcnow() for consistency
            last_hour = now - timedelta(hours=1)
            last_day = now - timedelta(days=1)

            recent_messages = Message.query.join(Conversation).filter(
                Conversation.user_id == self.user_id,
                Message.created_at >= last_hour
            ).count()

            daily_messages = Message.query.join(Conversation).filter(
                Conversation.user_id == self.user_id,
                Message.created_at >= last_day
            ).count()

            # High activity suggestion
            if recent_messages > 15:
                suggestions.append({
                    'type': 'productivity_break',
                    'message': "You've been very active this hour! A short break might help maintain your focus and creativity.",
                    'actions': ['suggest_break', 'breathing_exercise', 'stretch_reminder'],
                    'priority': 'medium'
                })

            # Low activity encouragement
            elif daily_messages < 5 and now.hour > 10:
                suggestions.append({
                    'type': 'engagement_boost',
                    'message': "How's your day going? I'm here if you need help with any projects or questions!",
                    'actions': ['daily_goals', 'project_check', 'motivation'],
                    'priority': 'low'
                })

            return suggestions
        except Exception as e:
            current_app.logger.error(f"Error checking productivity patterns: {e}")
            return []

    def generate_contextual_suggestions(self, current_message, emotion_data=None):
        """Generate contextual suggestions based on current message and emotions"""
        suggestions = []

        # Emotion-based suggestions
        if emotion_data:
            if emotion_data.get('stress', 0) > 0.6:
                suggestions.append({
                    'type': 'stress_relief',
                    'message': "I sense you might be feeling stressed. Would you like some relaxation techniques or a quick mental break?",
                    'actions': ['breathing_exercise', 'calming_music', 'positive_affirmations'],
                    'priority': 'high'
                })

            elif emotion_data.get('happiness', 0) > 0.7:
                suggestions.append({
                    'type': 'momentum_boost',
                    'message': "You seem to be in a great mood! This might be a perfect time to tackle challenging tasks or learn something new!",
                    'actions': ['challenging_project', 'skill_building', 'creative_task'],
                    'priority': 'medium'
                })

        # Time-based suggestions (use utcnow() for consistency)
        current_hour = datetime.utcnow().hour
        if 9 <= current_hour <= 11:  # Morning
            suggestions.append({
                'type': 'morning_productivity',
                'message': "Good morning! This is typically a great time for focused work. What would you like to accomplish today?",
                'actions': ['daily_planning', 'priority_tasks', 'goal_setting'],
                'priority': 'low'
            })

        elif 14 <= current_hour <= 16:  # Afternoon
            suggestions.append({
                'type': 'afternoon_energy',
                'message': "Afternoon energy dip is common. Would you like suggestions to boost your focus or take a strategic break?",
                'actions': ['energy_boost', 'focus_techniques', 'power_nap'],
                'priority': 'low'
            })

        return suggestions

    def generate_proactive_suggestions(self, context):
        """Main method to generate all proactive suggestions"""
        all_suggestions = []

        current_message = context.get('current_message', '')
        emotions = context.get('emotions', {})

        try:
            # Check various proactive scenarios
            break_suggestion = self.check_work_session_duration()
            if break_suggestion:
                all_suggestions.append(break_suggestion)

            deadline_suggestions = self.check_upcoming_deadlines()
            all_suggestions.extend(deadline_suggestions)

            coding_suggestions = self.analyze_coding_patterns(current_message)
            all_suggestions.extend(coding_suggestions)

            learning_suggestions = self.suggest_learning_resources(current_message)
            all_suggestions.extend(learning_suggestions)

            productivity_suggestions = self.check_productivity_patterns()
            all_suggestions.extend(productivity_suggestions)

            contextual_suggestions = self.generate_contextual_suggestions(current_message, emotions)
            all_suggestions.extend(contextual_suggestions)

            # Sort by priority and limit results
            priority_order = {'high': 3, 'medium': 2, 'low': 1}
            all_suggestions.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 1), reverse=True)

            return all_suggestions[:5]  # Return top 5 suggestions
        except Exception as e:
            current_app.logger.error(f"Error generating proactive suggestions: {e}")
            return []
