"""
Routes for handling document thumbnails
"""
import os
from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime

from models import db, Document
from utils.auth_decorators import admin_required
from utils.thumbnail_generator import (
    generate_document_thumbnail, 
    save_uploaded_thumbnail,
    generate_thumbnail_from_pdf,
    generate_thumbnail_from_url,
    generate_thumbnail_from_youtube
)

# Define the blueprint
thumbnail_bp = Blueprint('thumbnails', __name__)

@thumbnail_bp.route('/admin/document/<doc_id>/generate-thumbnail', methods=['POST'])
@login_required
@admin_required
def generate_thumbnail(doc_id):
    """Generate a thumbnail for a document"""
    # Get the document
    document = Document.query.get_or_404(doc_id)
    
    # Generate the thumbnail
    thumbnail_url = generate_document_thumbnail(document)
    
    if thumbnail_url:
        # Update the document
        document.thumbnail_url = thumbnail_url
        document.thumbnail_generated = True
        document.custom_thumbnail = False
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Thumbnail generated successfully',
            'thumbnail_url': thumbnail_url
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to generate thumbnail'
        }), 500


@thumbnail_bp.route('/admin/document/<doc_id>/upload-thumbnail', methods=['POST'])
@login_required
@admin_required
def upload_thumbnail(doc_id):
    """Upload a custom thumbnail for a document"""
    # Get the document
    document = Document.query.get_or_404(doc_id)
    
    # Check if a file was uploaded
    if 'thumbnail' not in request.files:
        return jsonify({
            'success': False,
            'message': 'No file uploaded'
        }), 400
        
    file = request.files['thumbnail']
    
    if file.filename == '':
        return jsonify({
            'success': False,
            'message': 'No file selected'
        }), 400
        
    # Check if the file is an image
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        return jsonify({
            'success': False,
            'message': 'Invalid file type - only images are allowed'
        }), 400
        
    # Save the uploaded thumbnail
    thumbnail_url = save_uploaded_thumbnail(file, document.id)
    
    if thumbnail_url:
        # Update the document
        document.thumbnail_url = thumbnail_url
        document.thumbnail_generated = False
        document.custom_thumbnail = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Thumbnail uploaded successfully',
            'thumbnail_url': thumbnail_url
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to save thumbnail'
        }), 500


@thumbnail_bp.route('/admin/document/<doc_id>/reset-thumbnail', methods=['POST'])
@login_required
@admin_required
def reset_thumbnail(doc_id):
    """Reset a document's thumbnail to the default for its content type"""
    # Get the document
    document = Document.query.get_or_404(doc_id)
    
    # Reset the thumbnail
    document.thumbnail_url = None
    document.thumbnail_generated = False
    document.custom_thumbnail = False
    db.session.commit()
    
    # Generate a new thumbnail
    thumbnail_url = generate_document_thumbnail(document)
    
    if thumbnail_url:
        # Update the document
        document.thumbnail_url = thumbnail_url
        document.thumbnail_generated = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Thumbnail reset successfully',
            'thumbnail_url': thumbnail_url
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to generate new thumbnail'
        }), 500


@thumbnail_bp.route('/admin/document/<doc_id>/thumbnail-management', methods=['GET'])
@login_required
@admin_required
def thumbnail_management(doc_id):
    """Page for managing a document's thumbnail"""
    # Get the document
    document = Document.query.get_or_404(doc_id)
    
    return render_template(
        'admin/thumbnail_management.html',
        document=document
    )