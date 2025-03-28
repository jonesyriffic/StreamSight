import os
import logging
import uuid
from functools import wraps
from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session, abort
from werkzeug.utils import secure_filename
import json
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from email_validator import validate_email, EmailNotValidError

from utils.pdf_processor import extract_text_from_pdf
from utils.ai_search import search_documents, categorize_content
from utils.document_ai import generate_document_summary
from models import db, Document, User

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

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()
    
    # Check if any admin users exist, if not create one
    admin_exists = User.query.filter_by(is_admin=True).first()
    if not admin_exists:
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@insights.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'adminpassword')
        admin_user = User(
            email=admin_email,
            name='System Administrator',
            is_active=True,
            is_approved=True,
            is_admin=True
        )
        admin_user.set_password(admin_password)
        db.session.add(admin_user)
        db.session.commit()
        logger.info(f"Created admin user: {admin_email}")

# Admin access decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required', 'danger')
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Access check for approved users
def approved_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_approved and not current_user.is_admin:
            flash('Your account is pending approval', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

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

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If already logged in, redirect to index
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # Handle login form submission
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        # Check if user exists and password is correct
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash('Login successful!', 'success')
            
            # Redirect to requested page or index
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # If already logged in, redirect to index
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # Handle registration form submission
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        name = request.form.get('name', '')
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        # Validate email
        try:
            valid = validate_email(email)
            email = valid.email
        except EmailNotValidError as e:
            flash(f'Invalid email: {str(e)}', 'danger')
            return render_template('register.html')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('register.html')
        
        # Create new user
        new_user = User(email=email, name=name)
        new_user.set_password(password)
        
        # Add to database
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/upload', methods=['GET'])
@login_required
@approved_required
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
@login_required
@approved_required
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
            
            # Create new document in database with current user as uploader
            new_document = Document(
                filename=original_filename,
                filepath=filepath,
                text=extracted_text,
                category=category,
                user_id=current_user.id
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
        return render_template('document_viewer.html', document=document)
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

@app.route('/api/generate-summary/<doc_id>', methods=['POST'])
@login_required
@approved_required
def generate_document_summary_api(doc_id):
    """API endpoint to generate a summary for a document"""
    try:
        # Check if document exists
        document = Document.query.get(doc_id)
        if not document:
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        # Check if user owns the document or is admin
        if document.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
        # Generate summary using our AI utility
        result = generate_document_summary(doc_id)
        
        # Format the timestamp if present
        if result.get('success') and document.summary_generated_at:
            result['generated_at'] = document.summary_generated_at.isoformat()
            
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/document/delete/<doc_id>', methods=['POST'])
@login_required
@approved_required
def delete_document(doc_id):
    document = Document.query.get(doc_id)
    if not document:
        flash('Document not found', 'danger')
        return redirect(url_for('library'))
    
    # Check if user owns the document
    if document.user_id is not None and document.user_id != current_user.id:
        flash('You do not have permission to delete this document', 'danger')
        return redirect(url_for('library'))
    
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
    
    # Redirect back to library
    return redirect(url_for('library'))

# Admin Dashboard Routes
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    # Get statistics for admin dashboard
    total_users = User.query.count()
    pending_users = User.query.filter_by(is_approved=False).count()
    admin_users = User.query.filter_by(is_admin=True).count()
    total_documents = Document.query.count()
    
    # Recent user registrations
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    # Pending approval users
    pending_approval = User.query.filter_by(is_approved=False).order_by(User.created_at.desc()).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         pending_users=pending_users,
                         admin_users=admin_users,
                         total_documents=total_documents,
                         recent_users=recent_users,
                         pending_approval=pending_approval)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    # Get all users
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/user/<int:user_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin_users'))
    
    user.approve()
    db.session.commit()
    
    flash(f'User {user.email} has been approved', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin_users'))
    
    # Don't allow removing admin status from the last admin
    if user.is_admin and User.query.filter_by(is_admin=True).count() <= 1:
        flash('Cannot remove admin status from the last admin user', 'danger')
        return redirect(url_for('admin_users'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    action = 'granted' if user.is_admin else 'revoked'
    flash(f'Admin privileges {action} for user {user.email}', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/toggle_active', methods=['POST'])
@login_required
@admin_required
def toggle_active(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin_users'))
    
    # Don't allow deactivating the last admin
    if user.is_admin and user.is_active and User.query.filter_by(is_admin=True, is_active=True).count() <= 1:
        flash('Cannot deactivate the last active admin user', 'danger')
        return redirect(url_for('admin_users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.email} has been {status}', 'success')
    return redirect(url_for('admin_users'))

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('index.html', error='Server error occurred'), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('index.html', error='Access forbidden'), 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
