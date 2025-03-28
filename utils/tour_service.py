"""
Tour service utility for managing the onboarding tour
"""
import json
from models import db, User
from flask_login import current_user
import logging

# Set up logger
logger = logging.getLogger(__name__)

class TourService:
    """Service for managing the onboarding tour"""
    
    # Define tour steps
    TOUR_STEPS = {
        'welcome': {
            'title': 'Welcome to NextGen Insight Spark!',
            'content': 'This quick tour will help you understand how to get the most from our platform. Ready to explore?'
        },
        'dashboard': {
            'title': 'Your Dashboard',
            'content': 'This is your personalized dashboard with document recommendations tailored to your team\'s needs.'
        },
        'search': {
            'title': 'Powerful Search',
            'content': 'Use natural language to search across all documents. Try asking specific questions!'
        },
        'library': {
            'title': 'Document Library',
            'content': 'Browse all documents or filter by category to find exactly what you need.'
        },
        'document_view': {
            'title': 'Document Viewer',
            'content': 'Read documents, generate summaries, and see why they\'re relevant to your team.'
        },
        'upload': {
            'title': 'Document Upload',
            'content': 'Share knowledge by uploading documents that will be processed by our AI.'
        },
        'badges': {
            'title': 'Earn Badges',
            'content': 'Track your progress and earn badges as you engage with documents and use platform features.'
        },
        'complete': {
            'title': 'Tour Complete!',
            'content': 'You\'re all set to start exploring insights. Remember you can restart this tour anytime from the help menu.'
        }
    }
    
    @staticmethod
    def get_tour_config():
        """
        Get the tour configuration based on user state
        
        Returns:
            dict: Tour configuration including steps and user progress
        """
        # Default tour state for anonymous users
        if not current_user.is_authenticated:
            return {
                'steps': TourService.TOUR_STEPS,
                'is_complete': False,
                'current_step': 'welcome',
                'steps_completed': {}
            }
        
        # Get user's tour progress
        steps_completed = current_user.tour_steps_completed or {}
        
        # Determine current step based on completion
        current_step = 'welcome'
        for step in TourService.TOUR_STEPS.keys():
            if step not in steps_completed:
                current_step = step
                break
        
        return {
            'steps': TourService.TOUR_STEPS,
            'is_complete': current_user.tour_completed,
            'current_step': current_step,
            'steps_completed': steps_completed
        }
    
    @staticmethod
    def update_tour_progress(step_id, completed=True):
        """
        Update a user's progress on the tour
        
        Args:
            step_id: ID of the step that was completed
            completed: Whether the step was completed (True) or reset (False)
            
        Returns:
            dict: Updated tour configuration
        """
        if not current_user.is_authenticated:
            # Can't update progress for anonymous users
            return TourService.get_tour_config()
        
        try:
            # Get current steps completion
            steps_completed = current_user.tour_steps_completed or {}
            
            # Update the completed step
            if completed:
                steps_completed[step_id] = True
            elif step_id in steps_completed:
                del steps_completed[step_id]
            
            # Check if all steps are complete
            all_steps_complete = all(step in steps_completed for step in TourService.TOUR_STEPS.keys())
            
            # Update user record
            current_user.tour_steps_completed = steps_completed
            current_user.tour_completed = all_steps_complete
            
            db.session.commit()
            
            # Return updated config
            return TourService.get_tour_config()
            
        except Exception as e:
            logger.error(f"Error updating tour progress: {str(e)}")
            db.session.rollback()
            return TourService.get_tour_config()
    
    @staticmethod
    def reset_tour():
        """
        Reset a user's tour progress
        
        Returns:
            dict: Updated tour configuration with progress reset
        """
        if not current_user.is_authenticated:
            # Can't reset progress for anonymous users
            return TourService.get_tour_config()
        
        try:
            # Reset tour progress
            current_user.tour_steps_completed = {}
            current_user.tour_completed = False
            
            db.session.commit()
            
            return TourService.get_tour_config()
            
        except Exception as e:
            logger.error(f"Error resetting tour: {str(e)}")
            db.session.rollback()
            return TourService.get_tour_config()