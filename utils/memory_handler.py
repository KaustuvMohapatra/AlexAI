import json
from datetime import datetime, timedelta
from flask import current_app
from models import db, UserMemory  # Import from models instead of app

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class MemoryManager:
    def __init__(self, user_id):
        self.user_id = user_id
        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')

    def store_memory(self, memory_type, key, value, importance=1.0):
        """Store a memory with importance scoring"""
        memory = UserMemory(
            user_id=self.user_id,
            memory_type=memory_type,
            key=key,
            value=json.dumps(value) if isinstance(value, dict) else str(value),
            importance_score=importance
        )
        db.session.add(memory)
        db.session.commit()

    def retrieve_relevant_memories(self, query, limit=5):
        """Retrieve memories relevant to current query"""
        memories = UserMemory.query.filter_by(user_id=self.user_id).all()

        if not memories:
            return []

        if not SKLEARN_AVAILABLE:
            # Fallback to recent memories if sklearn not available
            return UserMemory.query.filter_by(user_id=self.user_id) \
                .order_by(UserMemory.last_accessed.desc()).limit(limit).all()

        # Create text corpus from memories
        memory_texts = [f"{m.key} {m.value}" for m in memories]
        memory_texts.append(query)

        # Calculate similarity
        try:
            tfidf_matrix = self.vectorizer.fit_transform(memory_texts)
            query_vector = tfidf_matrix[-1]
            memory_vectors = tfidf_matrix[:-1]

            similarities = cosine_similarity(query_vector, memory_vectors).flatten()

            # Get top memories with importance weighting
            scored_memories = []
            for i, memory in enumerate(memories):
                score = similarities[i] * memory.importance_score
                scored_memories.append((memory, score))

            # Sort by score and return top results
            scored_memories.sort(key=lambda x: x[1], reverse=True)
            return [mem[0] for mem in scored_memories[:limit]]

        except Exception as e:
            # Fallback to recent memories
            return UserMemory.query.filter_by(user_id=self.user_id) \
                .order_by(UserMemory.last_accessed.desc()).limit(limit).all()

    def update_memory_importance(self, memory_id, interaction_type='access'):
        """Update memory importance based on usage"""
        memory = UserMemory.query.get(memory_id)
        if memory:
            if interaction_type == 'access':
                memory.importance_score *= 1.1
            elif interaction_type == 'positive_feedback':
                memory.importance_score *= 1.3
            memory.last_accessed = datetime.utcnow()
            db.session.commit()
