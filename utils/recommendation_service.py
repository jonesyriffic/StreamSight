"""
Recommendation service for document recommendations
"""

import logging
import random
from datetime import datetime, timedelta
from sqlalchemy import desc, and_, or_, func
from flask_login import current_user

from models import Document, User, UserActivity, UserDismissedRecommendation
from utils.relevance_generator import generate_team_relevance

logger = logging.getLogger(__name__)

def get_user_recommendations(user, max_recommendations=3):
    """
    Get personalized document recommendations for a user, excluding dismissed ones
    
    Args:
        user: User object
        max_recommendations: Maximum number of recommendations to return
        
    Returns:
        list: List of recommended Document objects with relevance score and reason
    """
    try:
        if not user or not user.is_authenticated:
            return []
            
        # Get user's team specialization
        team_specialization = user.team_specialization
        
        if not team_specialization:
            return []
            
        # Get IDs of documents the user has already dismissed
        dismissed_doc_ids = [dr.document_id for dr in 
                           UserDismissedRecommendation.query.filter_by(user_id=user.id).all()]
            
        # Get documents with relevant content to the user's team
        # Prioritize by:
        # 1. Documents with relevance reasons for the user's team
        # 2. Recently uploaded documents
        # 3. Documents the user hasn't viewed yet
        
        # Start with base query for all available documents
        query = Document.query.filter(Document.file_available == True)
        
        # Exclude documents the user has dismissed
        if dismissed_doc_ids:
            query = query.filter(Document.id.notin_(dismissed_doc_ids))
            
        # Get documents the user has already viewed
        viewed_doc_ids = [activity.document_id for activity in 
                         UserActivity.query.filter_by(user_id=user.id, activity_type='view').all()]
        
        # Mix of new and viewed documents, prioritizing new ones
        if viewed_doc_ids:
            # 80% new documents, 20% viewed ones if available
            all_docs = (
                query.filter(Document.id.notin_(viewed_doc_ids))
                .order_by(desc(Document.uploaded_at))
                .limit(int(max_recommendations * 0.8) + 1)
                .all()
            )
            
            # If we don't have enough new docs, add some viewed ones
            if len(all_docs) < max_recommendations:
                remaining_slots = max_recommendations - len(all_docs)
                viewed_docs = (
                    query.filter(Document.id.in_(viewed_doc_ids))
                    .order_by(desc(Document.uploaded_at))
                    .limit(remaining_slots)
                    .all()
                )
                all_docs.extend(viewed_docs)
        else:
            # User hasn't viewed any documents yet, just get the most recent ones
            all_docs = query.order_by(desc(Document.uploaded_at)).limit(max_recommendations).all()
            
        # Prioritize documents that have specific relevance reasons for the user's team
        # by moving them to the front of the list
        recommendations = []
        other_docs = []
        
        for doc in all_docs:
            if (doc.relevance_reasons and 
                isinstance(doc.relevance_reasons, dict) and 
                team_specialization in doc.relevance_reasons):
                recommendations.append(doc)
            else:
                other_docs.append(doc)
                
        # Add other documents to fill up to max_recommendations
        while len(recommendations) < max_recommendations and other_docs:
            recommendations.append(other_docs.pop(0))
            
        return recommendations[:max_recommendations]
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        return []


def dismiss_recommendation(user_id, document_id, feedback=None, feedback_type=None):
    """
    Dismiss a recommendation for a user
    
    Args:
        user_id: User ID
        document_id: Document ID
        feedback: Optional feedback text
        feedback_type: Optional feedback type (not_relevant, already_seen, not_interested)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if already dismissed
        existing = UserDismissedRecommendation.query.filter_by(
            user_id=user_id, 
            document_id=document_id
        ).first()
        
        if existing:
            # Update with new feedback if provided
            if feedback:
                existing.feedback = feedback
                
            # Update feedback type flags
            if feedback_type == 'not_relevant':
                existing.not_relevant = True
            elif feedback_type == 'already_seen':
                existing.already_seen = True
            elif feedback_type == 'not_interested':
                existing.not_interested = True
                
            # Save changes
            from app import db
            db.session.commit()
            return True
            
        # Create new dismissed recommendation
        dismissed = UserDismissedRecommendation(
            user_id=user_id,
            document_id=document_id,
            feedback=feedback,
            not_relevant=feedback_type == 'not_relevant',
            already_seen=feedback_type == 'already_seen',
            not_interested=feedback_type == 'not_interested'
        )
        
        # Save to database
        from app import db
        db.session.add(dismissed)
        db.session.commit()
        
        return True
        
    except Exception as e:
        logger.error(f"Error dismissing recommendation: {str(e)}")
        return False


def reset_dismissed_recommendations(user_id):
    """
    Reset all dismissed recommendations for a user
    
    Args:
        user_id: User ID
        
    Returns:
        int: Number of dismissed recommendations removed
    """
    try:
        # Delete all dismissed recommendations for the user
        from app import db
        count = UserDismissedRecommendation.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        
        return count
        
    except Exception as e:
        logger.error(f"Error resetting dismissed recommendations: {str(e)}")
        return 0