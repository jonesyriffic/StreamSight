"""
Fixed version of the upload_document function to replace in app.py
"""

def fixed_upload_document():
    """Handle document upload for different content types (PDF, web links, YouTube videos)"""
    # Check if user has upload permission
    if not current_user.can_upload and not current_user.is_admin:
        flash('You do not have permission to upload documents. Please contact an administrator.', 'danger')
        return redirect(url_for('index'))
    
    # Import content processor functions
    from utils.content_processor import (
        process_pdf_upload, 
        process_weblink, 
        process_youtube_video
    )
    
    # Get the content type from the form
    content_type = request.form.get('content_type', Document.TYPE_PDF)
    category = request.form.get('category', 'Uncategorized')
    successful_uploads = 0
    failed_uploads = 0
    earned_badges = set()
    
    # Process based on content type
    if content_type == Document.TYPE_WEBLINK:
        # Process web link
        url = request.form.get('url', '')
        if not url:
            flash('Please enter a valid URL', 'danger')
            return redirect(url_for('upload_page'))
            
        try:
            logger.info(f"Processing web link: {url}")
            document, message, status_code = process_weblink(
                url=url,
                category=category,
                user_id=current_user.id,
                db=db,
                Document=Document
            )
            
            if document and status_code == 200:
                # Process document (generate relevance, summary, track badges)
                _process_uploaded_document(document, current_user.id, earned_badges)
                successful_uploads += 1
                flash(message, 'success')
            else:
                failed_uploads += 1
                flash(message, 'danger')
                
        except Exception as e:
            logger.error(f"Error processing web link: {str(e)}")
            failed_uploads += 1
            flash(f"Error processing web link: {str(e)}", 'danger')
            
    elif content_type == Document.TYPE_YOUTUBE:
        # Process YouTube video
        url = request.form.get('url', '')
        if not url:
            flash('Please enter a valid YouTube URL', 'danger')
            return redirect(url_for('upload_page'))
            
        try:
            logger.info(f"Processing YouTube video: {url}")
            document, message, status_code = process_youtube_video(
                url=url,
                category=category,
                user_id=current_user.id,
                db=db,
                Document=Document
            )
            
            if document and status_code == 200:
                # Process document (generate relevance, summary, track badges)
                _process_uploaded_document(document, current_user.id, earned_badges)
                successful_uploads += 1
                flash(message, 'success')
            else:
                failed_uploads += 1
                flash(message, 'danger')
                
        except Exception as e:
            logger.error(f"Error processing YouTube video: {str(e)}")
            failed_uploads += 1
            flash(f"Error processing YouTube video: {str(e)}", 'danger')
            
    elif content_type == Document.TYPE_PDF:
        # Process PDF uploads
        if 'files' not in request.files:
            flash('No files selected', 'danger')
            return redirect(url_for('upload_page'))
            
        try:
            files = request.files.getlist('files')
        except Exception as e:
            logger.error(f"Error accessing uploaded files: {str(e)}")
            flash('Error processing upload request. The server might have timed out due to large file size.', 'danger')
            return redirect(url_for('upload_page'))
            
        if len(files) == 0 or all(file.filename == '' for file in files):
            flash('No selected file(s)', 'danger')
            return redirect(url_for('upload_page'))
            
        # Process each PDF file
        large_file_warning_shown = False
        
        for file in files:
            if file and file.filename != '' and allowed_file(file.filename):
                # Check file size and show warning if needed
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)  # Reset file position
                
                size_mb = file_size / (1024 * 1024)
                if size_mb > 50 and not large_file_warning_shown:
                    flash(f"Processing large file ({size_mb:.1f} MB). This may take several minutes. Please be patient.", "warning")
                    large_file_warning_shown = True
                
                # Process the PDF file
                try:
                    logger.info(f"Processing PDF file: {file.filename}")
                    document, message, status_code = process_pdf_upload(
                        uploaded_file=file,
                        filename=secure_filename(file.filename),
                        category=category,
                        user_id=current_user.id,
                        db=db,
                        Document=Document
                    )
                    
                    if document and status_code == 200:
                        # Process document (generate relevance, summary, track badges)
                        _process_uploaded_document(document, current_user.id, earned_badges)
                        successful_uploads += 1
                    else:
                        failed_uploads += 1
                        flash(message, 'warning')
                        
                except Exception as e:
                    logger.error(f"Error processing PDF file '{file.filename}': {str(e)}")
                    failed_uploads += 1
                    
                    # Check if it's an OpenAI API error
                    if "OpenAI API" in str(e):
                        logger.error(f"OpenAI API error detected during upload: {str(e)}")
                        flash("There was an issue with the AI service. Document was uploaded but without AI processing.", "warning")
                    else:
                        flash(f"Error processing file '{file.filename}': {str(e)}", 'danger')
            else:
                # Skip invalid files
                if file and file.filename != '':
                    failed_uploads += 1
                    flash(f"Invalid file type: {file.filename}. Only PDF files are allowed.", 'warning')
    else:
        # Invalid content type
        flash('Invalid content type', 'danger')
        return redirect(url_for('upload_page'))
    
    # Show badge notifications
    for badge_name, badge_level in earned_badges:
        flash(f"Congratulations! You've earned the {badge_name} badge ({badge_level})!", 'success')
    
    # Show upload results
    if successful_uploads > 0:
        if successful_uploads == 1:
            flash(f'1 document was uploaded successfully!', 'success')
        else:
            flash(f'{successful_uploads} documents were uploaded successfully!', 'success')
    
    if failed_uploads > 0:
        if failed_uploads == 1:
            flash(f'1 document failed to upload. Please check the file and try again.', 'warning')
        else:
            flash(f'{failed_uploads} documents failed to upload. Please check the files and try again.', 'warning')
    
    if successful_uploads == 0 and failed_uploads == 0:
        flash('No valid files were selected for upload.', 'warning')
        return redirect(url_for('upload_page'))
    
    return redirect(url_for('library'))


def _process_uploaded_document(document, user_id, earned_badges):
    """
    Helper function to process an uploaded document:
    - Generate relevance reasons
    - Generate summary and key points
    - Track badge activity
    
    Args:
        document: Document object
        user_id: ID of the current user
        earned_badges: Set to add earned badges to
    """
    # Generate relevance reasons
    try:
        from utils.relevance_generator import generate_relevance_reasons
        relevance_reasons = generate_relevance_reasons(document)
        document.relevance_reasons = relevance_reasons
        db.session.commit()
        logger.info(f"Generated relevance reasons for document {document.id}")
    except Exception as e:
        logger.error(f"Error generating relevance reasons: {str(e)}")
    
    # Generate summary
    try:
        if document.content_type == Document.TYPE_PDF:
            # Use document_ai for PDFs
            from utils.document_ai import generate_document_summary
            summary_result = generate_document_summary(document.id)
            if summary_result and summary_result.get('success'):
                logger.info(f"Generated summary for document {document.id}")
        else:
            # Use content_processor for web links and YouTube videos
            from utils.content_processor import generate_content_summary
            summary_result = generate_content_summary(document, db)
            if summary_result:
                logger.info(f"Generated summary for document {document.id}")
    except Exception as e:
        logger.error(f"Error generating document summary: {str(e)}")
    
    # Track badge activity
    try:
        from utils.badge_service import BadgeService
        new_badges = BadgeService.track_activity(
            user_id=user_id,
            activity_type='upload',
            document_id=document.id
        )
        
        # Add earned badges to the set
        if new_badges and new_badges.get('new_badges'):
            for badge in new_badges.get('new_badges'):
                earned_badges.add((badge['name'], badge['level']))
    except Exception as e:
        logger.error(f"Error tracking badge activity: {str(e)}")