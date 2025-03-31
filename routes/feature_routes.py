from datetime import datetime
from flask import jsonify
from flask_login import login_required, current_user
import logging

from app import app, db
from models import Document
from app import admin_required

logger = logging.getLogger(__name__)

@app.route('/api/document/<doc_id>/toggle-featured', methods=['POST'])
@login_required
@admin_required
def toggle_featured_status(doc_id):
    """API endpoint to toggle a document's featured status"""
    try:
        document = Document.query.get_or_404(doc_id)
        
        # Toggle featured status
        document.is_featured = not document.is_featured
        
        # Update featured_at timestamp if now featured
        if document.is_featured:
            document.featured_at = datetime.utcnow()
            message = f"Document marked as featured"
        else:
            document.featured_at = None
            message = f"Document removed from featured"
            
        db.session.commit()
        logger.info(f"{message}: {doc_id} - {document.friendly_name or document.filename}")
        
        return jsonify({
            'success': True,
            'is_featured': document.is_featured,
            'message': message
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling featured status for document {doc_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f"Error: {str(e)}"
        }), 500