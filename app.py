import os
import logging
import uuid
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
import json

from utils.pdf_processor import extract_text_from_pdf
from utils.ai_search import search_documents, categorize_content
from utils.document_store import DocumentStore

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

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

# Initialize document store
document_store = DocumentStore()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    documents = document_store.get_all_documents()
    return render_template('index.html', documents=documents)

@app.route('/upload', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(request.url)
    
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
            
            # Store the document
            doc_id = document_store.add_document({
                'id': str(uuid.uuid4()),
                'filename': original_filename,
                'filepath': filepath,
                'text': extracted_text,
                'category': category,
                'uploaded_at': document_store.get_current_time()
            })
            
            flash(f'Document "{original_filename}" uploaded successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Error during file upload: {str(e)}")
            flash(f'Error processing document: {str(e)}', 'danger')
            return redirect(url_for('index'))
    else:
        flash('Invalid file type. Only PDF files are allowed.', 'danger')
        return redirect(url_for('index'))

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '')
    category_filter = request.args.get('category', 'all')
    
    if not query:
        return render_template('search_results.html', results=[], query='', categories=document_store.get_all_categories())
    
    try:
        results = search_documents(query, document_store, category_filter)
        return render_template('search_results.html', 
                              results=results, 
                              query=query,
                              selected_category=category_filter,
                              categories=document_store.get_all_categories())
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        flash(f'Error during search: {str(e)}', 'danger')
        return render_template('search_results.html', results=[], query=query, error=str(e), categories=document_store.get_all_categories())

@app.route('/document/<doc_id>')
def view_document(doc_id):
    document = document_store.get_document(doc_id)
    if document:
        return render_template('document_viewer.html', document=document)
    else:
        flash('Document not found', 'danger')
        return redirect(url_for('index'))

@app.route('/api/documents')
def get_documents():
    documents = document_store.get_all_documents()
    return jsonify(documents)

@app.route('/api/documents/<doc_id>')
def get_document(doc_id):
    document = document_store.get_document(doc_id)
    if document:
        return jsonify(document)
    else:
        return jsonify({'error': 'Document not found'}), 404

@app.route('/api/categories')
def get_categories():
    categories = document_store.get_all_categories()
    return jsonify(categories)

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('index.html', error='Server error occurred'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
