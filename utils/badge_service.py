"""
Badge service utility for handling badge awards
"""
from datetime import datetime
from models import db, User, Badge, UserActivity, Document

class BadgeService:
    """Service for tracking user activities and awarding badges"""
    
    @staticmethod
    def track_activity(user_id, activity_type, document_id=None):
        """
        Track a user activity and check for badge awards
        
        Args:
            user_id: ID of the user performing the activity
            activity_type: Type of activity (view, search, upload, summarize)
            document_id: Optional ID of the document associated with the activity
            
        Returns:
            dict: Dictionary containing new badges awarded, if any
        """
        # Create activity record
        activity = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            document_id=document_id,
            performed_at=datetime.utcnow()
        )
        db.session.add(activity)
        db.session.commit()
        
        # Check for badge awards
        return BadgeService.check_badges(user_id)
    
    @staticmethod
    def check_badges(user_id):
        """
        Check if user has earned any new badges
        
        Args:
            user_id: ID of the user to check
            
        Returns:
            dict: Dictionary containing new badges awarded, if any
        """
        user = User.query.get(user_id)
        if not user:
            return {"new_badges": []}
        
        # Get counts of various activities
        view_count = UserActivity.query.filter_by(
            user_id=user_id, 
            activity_type='view'
        ).count()
        
        search_count = UserActivity.query.filter_by(
            user_id=user_id, 
            activity_type='search'
        ).count()
        
        upload_count = UserActivity.query.filter_by(
            user_id=user_id, 
            activity_type='upload'
        ).count()
        
        summarize_count = UserActivity.query.filter_by(
            user_id=user_id, 
            activity_type='summarize'
        ).count()
        
        # Get all badges the user doesn't already have
        user_badge_ids = [badge.id for badge in user.badges]
        available_badges = Badge.query.filter(~Badge.id.in_(user_badge_ids)).all()
        
        new_badges = []
        
        # Check each badge to see if the user qualifies
        for badge in available_badges:
            qualifies = False
            
            if badge.type == Badge.TYPE_READER and view_count >= badge.criteria_count:
                qualifies = True
            elif badge.type == Badge.TYPE_SEARCHER and search_count >= badge.criteria_count:
                qualifies = True
            elif badge.type == Badge.TYPE_CONTRIBUTOR and upload_count >= badge.criteria_count:
                qualifies = True
            elif badge.type == Badge.TYPE_SUMMARIZER and summarize_count >= badge.criteria_count:
                qualifies = True
            
            if qualifies:
                # Award the badge
                user.badges.append(badge)
                new_badges.append(badge.to_dict())
        
        if new_badges:
            db.session.commit()
            
        return {"new_badges": new_badges}
    
    @staticmethod
    def get_user_badges(user_id):
        """
        Get all badges for a user
        
        Args:
            user_id: ID of the user
            
        Returns:
            list: List of badge dictionaries
        """
        user = User.query.get(user_id)
        if not user:
            return []
        
        return [badge.to_dict() for badge in user.badges]
    
    @staticmethod
    def get_user_progress(user_id):
        """
        Get badge progress for a user
        
        Args:
            user_id: ID of the user
            
        Returns:
            dict: Dictionary containing badge progress information
        """
        user = User.query.get(user_id)
        if not user:
            return {}
        
        # Get activity counts
        view_count = UserActivity.query.filter_by(
            user_id=user_id, 
            activity_type='view'
        ).count()
        
        search_count = UserActivity.query.filter_by(
            user_id=user_id, 
            activity_type='search'
        ).count()
        
        upload_count = UserActivity.query.filter_by(
            user_id=user_id, 
            activity_type='upload'
        ).count()
        
        summarize_count = UserActivity.query.filter_by(
            user_id=user_id, 
            activity_type='summarize'
        ).count()
        
        # Get next level badges
        user_badges = user.badges  # user.badges is already a list, no need to call .all()
        user_badge_types = {}
        
        for badge in user_badges:
            if badge.type not in user_badge_types or badge.criteria_count > user_badge_types[badge.type].criteria_count:
                user_badge_types[badge.type] = badge
        
        next_badges = {}
        for badge_type in Badge.BADGE_TYPES:
            # Find the next badge for this type that the user doesn't have
            current_level = None
            if badge_type in user_badge_types:
                current_level = user_badge_types[badge_type].level
            
            # Find the lowest level badge of this type if user has none
            if current_level is None:
                entry_badge = Badge.query.filter_by(type=badge_type, level=Badge.LEVEL_BRONZE).first()
                if entry_badge:
                    next_badges[badge_type] = entry_badge.to_dict()
                continue
            
            # If user has a badge, find the next level
            next_level_index = Badge.BADGE_LEVELS.index(current_level) + 1
            if next_level_index < len(Badge.BADGE_LEVELS):
                next_level = Badge.BADGE_LEVELS[next_level_index]
                next_badge = Badge.query.filter_by(type=badge_type, level=next_level).first()
                if next_badge:
                    next_badges[badge_type] = next_badge.to_dict()
        
        # Build the progress data
        progress = {
            "reader": {
                "current_count": view_count,
                "next_badge": next_badges.get(Badge.TYPE_READER)
            },
            "searcher": {
                "current_count": search_count,
                "next_badge": next_badges.get(Badge.TYPE_SEARCHER)
            },
            "contributor": {
                "current_count": upload_count,
                "next_badge": next_badges.get(Badge.TYPE_CONTRIBUTOR)
            },
            "summarizer": {
                "current_count": summarize_count,
                "next_badge": next_badges.get(Badge.TYPE_SUMMARIZER)
            }
        }
        
        return progress