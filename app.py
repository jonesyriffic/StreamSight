import os
import logging
import uuid
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
import json

from utils.pdf_processor import extract_text_from_pdf
from utils.ai_search import search_documents, categorize_content
from models import db, Document

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Configure database
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    # Get all documents and categories for statistics
    documents = Document.query.order_by(Document.uploaded_at.desc()).all()
    categories = db.session.query(Document.category).distinct().all()
    categories = [category[0] for category in categories]
    
    # Get statistics for dashboard
    total_documents = Document.query.count()
    total_categories = len(categories)
    
    # Calculate uploads this month
    from datetime import datetime
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    upload_month = Document.query.filter(
        db.extract('month', Document.uploaded_at) == current_month,
        db.extract('year', Document.uploaded_at) == current_year
    ).count()
    
    # Get only recent documents for the dashboard
    recent_documents = Document.query.order_by(Document.uploaded_at.desc()).limit(5).all()
    
    return render_template('index.html', 
                          categories=categories,
                          total_documents=total_documents,
                          total_categories=total_categories,
                          upload_month=upload_month,
                          recent_documents=[doc.to_dict() for doc in recent_documents])

@app.route('/upload', methods=['GET'])
def upload_page():
    return render_template('upload.html')

@app.route('/library')
def library():
    # Get filter parameters
    category_filter = request.args.get('category', 'all')
    sort_by = request.args.get('sort', 'date_desc')
    
    # Query base
    query = Document.query
    
    # Apply category filter if not 'all'
    if category_filter != 'all':
        query = query.filter_by(category=category_filter)
    
    # Apply sorting
    if sort_by == 'date_desc':
        query = query.order_by(Document.uploaded_at.desc())
    elif sort_by == 'date_asc':
        query = query.order_by(Document.uploaded_at.asc())
    elif sort_by == 'name_asc':
        query = query.order_by(Document.filename.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(Document.filename.desc())
    
    # Execute query
    documents = query.all()
    
    # Get all categories for the filter dropdown
    categories = db.session.query(Document.category).distinct().all()
    categories = [category[0] for category in categories]
    
    return render_template('library.html',
                          documents=[doc.to_dict() for doc in documents],
                          categories=categories,
                          category_filter=category_filter,
                          sort_by=sort_by)

@app.route('/upload', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('upload_page'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('upload_page'))
    
    if file and allowed_file(file.filename):
        try:
            # Generate a unique filename
            original_filename = secure_filename(file.filename)
            filename = f"{uuid.uuid4()}_{original_filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Save the file
            file.save(filepath)
            
            # Extract text from PDF
            extracted_text = extract_text_from_pdf(filepath)
            
            # Categorize the content
            category = categorize_content(extracted_text)
            
            # Create new document in database
            new_document = Document(
                filename=original_filename,
                filepath=filepath,
                text=extracted_text,
                category=category
            )
            
            # Add to database
            db.session.add(new_document)
            db.session.commit()
            
            flash(f'Document "{original_filename}" uploaded successfully!', 'success')
            return redirect(url_for('library'))
        except Exception as e:
            logger.error(f"Error during file upload: {str(e)}")
            flash(f'Error processing document: {str(e)}', 'danger')
            return redirect(url_for('upload_page'))
    else:
        flash('Invalid file type. Only PDF files are allowed.', 'danger')
        return redirect(url_for('upload_page'))

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')
    category_filter = request.args.get('category', 'all')
    
    if not query:
        all_categories = db.session.query(Document.category).distinct().all()
        categories = [category[0] for category in all_categories]
        return render_template('search_results.html', results=[], query='', categories=categories)
    
    try:
        # Get document repository for search
        document_repository = {
            'get_all_documents': lambda: [doc.to_dict() for doc in Document.query.all()],
            'get_documents_by_category': lambda category: [
                doc.to_dict() for doc in Document.query.filter_by(category=category).all()
            ],
            'get_document': lambda doc_id: Document.query.get(doc_id).to_dict() if Document.query.get(doc_id) else None
        }
        
        results = search_documents(query, document_repository, category_filter)
        
        all_categories = db.session.query(Document.category).distinct().all()
        categories = [category[0] for category in all_categories]
        
        return render_template('search_results.html', 
                              results=results, 
                              query=query,
                              selected_category=category_filter,
                              categories=categories)
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        flash(f'Error during search: {str(e)}', 'danger')
        all_categories = db.session.query(Document.category).distinct().all()
        categories = [category[0] for category in all_categories]
        return render_template('search_results.html', results=[], query=query, error=str(e), categories=categories)

@app.route('/document/<doc_id>')
def view_document(doc_id):
    document = Document.query.get(doc_id)
    if document:
        return render_template('document_viewer.html', document=document.to_dict())
    else:
        flash('Document not found', 'danger')
        return redirect(url_for('index'))

@app.route('/api/documents')
def get_documents():
    documents = Document.query.all()
    return jsonify([doc.to_dict() for doc in documents])

@app.route('/api/documents/<doc_id>')
def get_document(doc_id):
    document = Document.query.get(doc_id)
    if document:
        return jsonify(document.to_dict())
    else:
        return jsonify({'error': 'Document not found'}), 404

@app.route('/api/categories')
def get_categories():
    categories = db.session.query(Document.category).distinct().all()
    return jsonify([category[0] for category in categories])

@app.route('/document/delete/<doc_id>', methods=['POST'])
def delete_document(doc_id):
    document = Document.query.get(doc_id)
    if document:
        try:
            # Delete physical file if it exists
            if os.path.exists(document.filepath):
                os.remove(document.filepath)
            
            # Delete from database
            db.session.delete(document)
            db.session.commit()
            
            flash(f'Document "{document.filename}" deleted successfully', 'success')
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            flash(f'Error deleting document: {str(e)}', 'danger')
    else:
        flash('Document not found', 'danger')
    
    # Redirect back to library instead of index
    return redirect(url_for('library'))

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('index.html', error='Server error occurred'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
