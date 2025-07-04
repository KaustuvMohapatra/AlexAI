import json
from datetime import datetime, timedelta
from flask import current_app
from models import db, TaskAutomation
import requests
import re


class TaskAutomationManager:
    def __init__(self, user_id):
        self.user_id = user_id
        self.default_automations = self._create_default_automations()

    def _create_default_automations(self):
        """Create default automation templates"""
        return {
            'good morning': [
                {'type': 'weather_update', 'priority': 1},
                {'type': 'calendar_events', 'priority': 2},
                {'type': 'daily_motivation', 'priority': 3},
                {'type': 'news_briefing', 'priority': 4}
            ],
            'start work': [
                {'type': 'focus_mode', 'priority': 1},
                {'type': 'productivity_music', 'priority': 2},
                {'type': 'task_list', 'priority': 3},
                {'type': 'distraction_blocker', 'priority': 4}
            ],
            'end work': [
                {'type': 'work_summary', 'priority': 1},
                {'type': 'tomorrow_prep', 'priority': 2},
                {'type': 'relaxation_mode', 'priority': 3},
                {'type': 'evening_routine', 'priority': 4}
            ],
            'break time': [
                {'type': 'break_timer', 'duration': 15, 'priority': 1},
                {'type': 'relaxing_music', 'priority': 2},
                {'type': 'stretch_reminder', 'priority': 3},
                {'type': 'hydration_reminder', 'priority': 4}
            ],
            'study session': [
                {'type': 'focus_timer', 'duration': 25, 'priority': 1},
                {'type': 'study_music', 'priority': 2},
                {'type': 'note_taking_setup', 'priority': 3},
                {'type': 'progress_tracking', 'priority': 4}
            ]
        }

    def create_automation(self, trigger_phrase, actions):
        """Create a new task automation"""
        automation = TaskAutomation(
            user_id=self.user_id,
            trigger_phrase=trigger_phrase.lower(),
            actions=actions
        )
        db.session.add(automation)
        db.session.commit()
        return automation.id

    def check_triggers(self, user_message):
        """Check if user message triggers any automations"""
        user_message_lower = user_message.lower()
        triggered_actions = []

        # Check custom automations first
        automations = TaskAutomation.query.filter(
            TaskAutomation.user_id == self.user_id,
            TaskAutomation.is_active == True
        ).all()

        for automation in automations:
            if automation.trigger_phrase in user_message_lower:
                triggered_actions.extend(automation.actions)
                # Update usage statistics
                automation.usage_count += 1
                automation.last_used = datetime.utcnow()
                db.session.commit()

        # Check default automations
        for trigger, actions in self.default_automations.items():
            if trigger in user_message_lower:
                triggered_actions.extend(actions)

        return triggered_actions

    def execute_actions(self, actions):
        """Execute triggered actions"""
        results = []

        # Sort actions by priority
        sorted_actions = sorted(actions, key=lambda x: x.get('priority', 999))

        for action in sorted_actions:
            try:
                result = self._execute_single_action(action)
                if result:
                    results.append(result)
            except Exception as e:
                results.append({
                    'type': 'error',
                    'message': f"Failed to execute {action.get('type', 'unknown')} action: {str(e)}",
                    'success': False
                })

        return results

    def _execute_single_action(self, action):
        """Execute a single action"""
        action_type = action.get('type')

        if action_type == 'weather_update':
            return self.get_weather_update()
        elif action_type == 'calendar_events':
            return self.get_calendar_events()
        elif action_type == 'daily_motivation':
            return self.get_daily_motivation()
        elif action_type == 'news_briefing':
            return self.get_news_briefing()
        elif action_type == 'focus_mode':
            return self.activate_focus_mode()
        elif action_type == 'productivity_music':
            return self.play_productivity_music()
        elif action_type == 'task_list':
            return self.get_task_list()
        elif action_type == 'work_summary':
            return self.generate_work_summary()
        elif action_type == 'break_timer':
            return self.start_break_timer(action.get('duration', 15))
        elif action_type == 'focus_timer':
            return self.start_focus_timer(action.get('duration', 25))
        elif action_type == 'relaxing_music':
            return self.play_relaxing_music()
        elif action_type == 'study_music':
            return self.play_study_music()
        else:
            return self.handle_custom_action(action)

    def get_weather_update(self):
        """Get weather information"""
        try:
            # Simulate weather API call
            weather_data = {
                'temperature': 22,
                'condition': 'sunny',
                'humidity': 65,
                'wind_speed': 10
            }

            return {
                'type': 'weather',
                'message': f"🌤️ Today's weather: {weather_data['condition'].title()}, {weather_data['temperature']}°C. Humidity: {weather_data['humidity']}%, Wind: {weather_data['wind_speed']} km/h",
                'data': weather_data,
                'success': True
            }
        except Exception as e:
            return {
                'type': 'weather',
                'message': "Unable to fetch weather information at the moment.",
                'success': False
            }

    def get_calendar_events(self):
        """Get calendar events"""
        # Simulate calendar integration
        events = [
            {'time': '9:00 AM', 'title': 'Team Standup', 'duration': '30 min'},
            {'time': '2:00 PM', 'title': 'Project Review', 'duration': '1 hour'},
            {'time': '4:00 PM', 'title': 'Client Call', 'duration': '45 min'}
        ]

        if events:
            event_list = "\n".join([f"• {event['time']}: {event['title']} ({event['duration']})" for event in events])
            message = f"📅 Your schedule for today:\n{event_list}"
        else:
            message = "📅 You have no scheduled events today. Great time for focused work!"

        return {
            'type': 'calendar',
            'message': message,
            'data': {'events': events, 'count': len(events)},
            'success': True
        }

    def get_daily_motivation(self):
        """Get daily motivation quote"""
        motivational_quotes = [
            "The way to get started is to quit talking and begin doing. - Walt Disney",
            "Innovation distinguishes between a leader and a follower. - Steve Jobs",
            "Your limitation—it's only your imagination.",
            "Push yourself, because no one else is going to do it for you.",
            "Great things never come from comfort zones.",
            "Dream it. Wish it. Do it.",
            "Success doesn't just find you. You have to go out and get it.",
            "The harder you work for something, the greater you'll feel when you achieve it."
        ]

        import random
        quote = random.choice(motivational_quotes)

        return {
            'type': 'motivation',
            'message': f"💪 Daily Motivation: {quote}",
            'data': {'quote': quote},
            'success': True
        }

    def get_news_briefing(self):
        """Get news briefing"""
        # Simulate news API
        news_items = [
            "Tech: Major breakthrough in AI research announced",
            "Business: Stock markets showing positive trends",
            "Science: New discoveries in renewable energy"
        ]

        briefing = "\n".join([f"• {item}" for item in news_items])

        return {
            'type': 'news',
            'message': f"📰 Quick News Briefing:\n{briefing}",
            'data': {'items': news_items},
            'success': True
        }

    def activate_focus_mode(self):
        """Activate focus mode"""
        return {
            'type': 'focus_mode',
            'message': "🎯 Focus mode activated! Distractions minimized, productivity maximized.",
            'data': {'mode': 'focus', 'duration': 'until_deactivated'},
            'success': True
        }

    def play_productivity_music(self):
        """Play productivity music"""
        playlists = [
            "Deep Focus Instrumentals",
            "Coding Beats",
            "Ambient Concentration",
            "Lo-fi Study Vibes"
        ]

        import random
        selected_playlist = random.choice(playlists)

        return {
            'type': 'music',
            'message': f"🎵 Now playing: {selected_playlist} - Perfect for productive work!",
            'data': {'playlist': selected_playlist, 'type': 'productivity'},
            'success': True
        }

    def get_task_list(self):
        """Get task list"""
        # Simulate task management integration
        tasks = [
            {'task': 'Complete project documentation', 'priority': 'high', 'due': 'today'},
            {'task': 'Review code pull requests', 'priority': 'medium', 'due': 'tomorrow'},
            {'task': 'Prepare presentation slides', 'priority': 'medium', 'due': 'this week'}
        ]

        if tasks:
            task_list = "\n".join(
                [f"• {task['task']} (Priority: {task['priority']}, Due: {task['due']})" for task in tasks])
            message = f"📋 Your current tasks:\n{task_list}"
        else:
            message = "📋 No pending tasks found. You're all caught up!"

        return {
            'type': 'tasks',
            'message': message,
            'data': {'tasks': tasks, 'count': len(tasks)},
            'success': True
        }

    def generate_work_summary(self):
        """Generate work summary"""
        # Simulate work tracking
        summary = {
            'hours_worked': 7.5,
            'tasks_completed': 4,
            'meetings_attended': 2,
            'productivity_score': 85
        }

        return {
            'type': 'work_summary',
            'message': f"📊 Work Summary:\n• Hours worked: {summary['hours_worked']}\n• Tasks completed: {summary['tasks_completed']}\n• Meetings attended: {summary['meetings_attended']}\n• Productivity score: {summary['productivity_score']}%",
            'data': summary,
            'success': True
        }

    def start_break_timer(self, duration):
        """Start break timer"""
        return {
            'type': 'timer',
            'message': f"⏰ Break timer started for {duration} minutes. Take a well-deserved rest!",
            'data': {'duration': duration, 'type': 'break', 'started_at': datetime.utcnow().isoformat()},
            'success': True
        }

    def start_focus_timer(self, duration):
        """Start focus timer (Pomodoro technique)"""
        return {
            'type': 'timer',
            'message': f"🍅 Focus timer started for {duration} minutes. Time to concentrate!",
            'data': {'duration': duration, 'type': 'focus', 'started_at': datetime.utcnow().isoformat()},
            'success': True
        }

    def play_relaxing_music(self):
        """Play relaxing music"""
        playlists = [
            "Peaceful Piano",
            "Nature Sounds",
            "Meditation Music",
            "Calm Acoustic"
        ]

        import random
        selected_playlist = random.choice(playlists)

        return {
            'type': 'music',
            'message': f"🎼 Now playing: {selected_playlist} - Perfect for relaxation.",
            'data': {'playlist': selected_playlist, 'type': 'relaxation'},
            'success': True
        }

    def play_study_music(self):
        """Play study music"""
        playlists = [
            "Classical Study Music",
            "Brain Food Instrumentals",
            "Focus Flow",
            "Study Beats"
        ]

        import random
        selected_playlist = random.choice(playlists)

        return {
            'type': 'music',
            'message': f"📚 Now playing: {selected_playlist} - Optimized for learning and retention.",
            'data': {'playlist': selected_playlist, 'type': 'study'},
            'success': True
        }

    def handle_custom_action(self, action):
        """Handle custom user-defined actions"""
        return {
            'type': 'custom',
            'message': f"Executed custom action: {action.get('type', 'Unknown')}",
            'data': action,
            'success': True
        }

    def get_automation_statistics(self):
        """Get automation usage statistics"""
        automations = TaskAutomation.query.filter_by(user_id=self.user_id).all()

        stats = {
            'total_automations': len(automations),
            'active_automations': len([a for a in automations if a.is_active]),
            'most_used': None,
            'total_executions': sum(a.usage_count for a in automations)
        }

        if automations:
            most_used = max(automations, key=lambda x: x.usage_count)
            stats['most_used'] = {
                'trigger': most_used.trigger_phrase,
                'usage_count': most_used.usage_count
            }

        return stats
