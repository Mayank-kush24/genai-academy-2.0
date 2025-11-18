"""
Flask Web Application for GenAI Academy 2.0 Records Management
Main application file with routes and views
"""
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session as flask_session, flash
from werkzeug.utils import secure_filename
from datetime import datetime
import pandas as pd
import io
import os
import sys
import uuid

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import db_manager, UserPII, Course, SkillboostProfile, MasterClass
from app.queries import (
    get_user_complete_profile,
    search_users,
    get_verification_statistics,
    get_pending_verifications,
    get_failed_verifications,
    get_course_statistics,
    get_masterclass_statistics,
    get_recent_changes,
    export_all_data,
    get_demographic_statistics,
    get_dashboard_statistics,
    get_badge_statistics_breakdown,
    get_certificate_eligible_users
)
from app.csv_import import CSVImporter, get_table_columns
from app.auth import (
    SystemUser,
    get_current_user,
    login_required,
    permission_required,
    admin_required,
    authenticate_user,
    create_user,
    update_user,
    delete_user,
    get_all_users,
    get_user_by_id,
    DEFAULT_ROLE_PERMISSIONS
)
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.FLASK_SECRET_KEY
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db_manager.initialize()

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================
# Authentication Routes
# ============================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    # If already logged in, redirect to home
    if 'user_id' in flask_session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember_me = request.form.get('remember_me') == 'on'
        
        if not username or not password:
            flash('Please provide both username and password.', 'warning')
            return render_template('login.html')
        
        user = authenticate_user(username, password)
        
        if user:
            flask_session['user_id'] = user.user_id
            flask_session['username'] = user.username
            flask_session['role'] = user.role
            flask_session['permissions'] = user.get_permissions()
            
            if remember_me:
                flask_session.permanent = True
            
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            
            # Redirect to next page or home
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout user"""
    flask_session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))


# ============================================
# User Management Routes (Admin Only)
# ============================================

@app.route('/admin/users')
@login_required
@admin_required
def manage_users():
    """User management page"""
    users = get_all_users()
    return render_template('admin_users.html', users=users, roles=DEFAULT_ROLE_PERMISSIONS)


@app.route('/api/users', methods=['GET'])
@login_required
@admin_required
def get_users_api():
    """Get all users API"""
    users = get_all_users()
    return jsonify({
        'success': True,
        'users': [user.to_dict() for user in users]
    })


@app.route('/api/users/create', methods=['POST'])
@login_required
@admin_required
def create_user_api():
    """Create new user API"""
    data = request.json
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip()
    full_name = data.get('full_name', '').strip()
    role = data.get('role', 'viewer')
    permissions = data.get('permissions')
    
    if not username or not password or not email:
        return jsonify({'success': False, 'error': 'Username, password, and email are required'}), 400
    
    user, error = create_user(username, password, email, full_name, role, permissions)
    
    if error:
        return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'message': f'User {username} created successfully'
    })


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user_api(user_id):
    """Update user API"""
    data = request.json
    
    user, error = update_user(user_id, **data)
    
    if error:
        return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'message': 'User updated successfully'
    })


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user_api(user_id):
    """Delete user API"""
    # Prevent self-deletion
    if user_id == flask_session.get('user_id'):
        return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
    
    success, error = delete_user(user_id)
    
    if not success:
        return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({
        'success': True,
        'message': 'User deleted successfully'
    })


@app.route('/api/current-user')
@login_required
def get_current_user_api():
    """Get current logged-in user info"""
    user = get_current_user()
    if user:
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
    return jsonify({'success': False, 'error': 'Not logged in'}), 401


# ============================================
# Main Application Routes (with permission checks)
# ============================================

@app.route('/')
@login_required
def index():
    """Home page with search"""
    user = get_current_user()
    return render_template('index.html', user=user)


@app.route('/search')
@login_required
@permission_required('view_profiles')
def search():
    """Search users"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return render_template('search_results.html', users=[], query='')
    
    session = db_manager.get_session()
    try:
        # Search in multiple fields
        users = session.query(UserPII).filter(
            (UserPII.name.ilike(f'%{query}%')) |
            (UserPII.email.ilike(f'%{query}%')) |
            (UserPII.phone_number.ilike(f'%{query}%')) |
            (UserPII.city.ilike(f'%{query}%')) |
            (UserPII.state.ilike(f'%{query}%'))
        ).order_by(UserPII.name).limit(50).all()
        
        return render_template('search_results.html', users=users, query=query)
    finally:
        db_manager.close_session(session)


@app.route('/user/<email>')
@login_required
@permission_required('view_profiles')
def user_profile(email):
    """View user profile"""
    session = db_manager.get_session()
    try:
        profile = get_user_complete_profile(session, email)
        
        if not profile:
            return render_template('error.html', message='User not found'), 404
        
        return render_template('user_profile.html', profile=profile)
    finally:
        db_manager.close_session(session)


@app.route('/verification-queue')
@login_required
@permission_required('verification_queue')
def verification_queue():
    """View pending verifications"""
    session = db_manager.get_session()
    try:
        pending = get_pending_verifications(session, limit=200)
        failed = get_failed_verifications(session, limit=100)
        
        return render_template(
            'verification_queue.html',
            pending_profiles=pending['profiles'],
            pending_badges=pending['badges'],
            failed_profiles=failed['profiles'],
            failed_badges=failed['badges']
        )
    finally:
        db_manager.close_session(session)


@app.route('/reports')
@login_required
@permission_required('view_dashboard')
def reports():
    """View reports and statistics"""
    session = db_manager.get_session()
    try:
        stats = get_verification_statistics(session)
        course_stats = get_course_statistics(session)
        masterclass_stats = get_masterclass_statistics(session)
        recent_changes = get_recent_changes(session, limit=20)
        
        return render_template(
            'reports.html',
            stats=stats,
            course_stats=course_stats,
            masterclass_stats=masterclass_stats,
            recent_changes=recent_changes
        )
    finally:
        db_manager.close_session(session)


@app.route('/export')
@login_required
@permission_required('export_data')
def export_page():
    """Export page"""
    return render_template('export.html')


@app.route('/api/export/users')
@login_required
@permission_required('export_data')
def export_users():
    """Export all user data as CSV"""
    session = db_manager.get_session()
    try:
        data = export_all_data(session)
        
        # Convert to DataFrame
        # Normalize occupation: Convert SCHOOL_STUDENT to COLLEGE_STUDENT
        df = pd.DataFrame([{
            'Email': row.email,
            'Name': row.name,
            'Phone': row.phone_number,
            'Gender': row.gender,
            'Country': row.country,
            'State': row.state,
            'City': row.city,
            'Designation': row.designation,
            'Occupation': 'COLLEGE_STUDENT' if row.occupation == 'SCHOOL_STUDENT' else row.occupation,
            'Courses Completed': row.courses_completed,
            'Courses Verified': row.courses_verified,
            'Masterclasses Attended': row.masterclasses_attended
        } for row in data])
        
        # Create CSV in memory
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'academy_users_export_{timestamp}.csv'
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    finally:
        db_manager.close_session(session)


@app.route('/api/export/courses')
def export_courses():
    """Export all course data as CSV"""
    session = db_manager.get_session()
    try:
        courses = session.query(Course).all()
        
        df = pd.DataFrame([{
            'Email': c.email,
            'Problem Statement': c.problem_statement,
            'Badge Link': c.share_skill_badge_public_link,
            'Valid': c.valid,
            'Remarks': c.remarks,
            'Created At': c.created_at,
            'Updated At': c.updated_at
        } for c in courses])
        
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'academy_courses_export_{timestamp}.csv'
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    finally:
        db_manager.close_session(session)


@app.route('/api/export/masterclasses')
def export_masterclasses():
    """Export all masterclass attendance as CSV"""
    session = db_manager.get_session()
    try:
        masterclasses = session.query(MasterClass).all()
        
        df = pd.DataFrame([{
            'Email': mc.email,
            'Masterclass': mc.master_class_name,
            'Time Watched': mc.time_watched,
            'Valid': mc.valid,
            'Started At': mc.started_at,
            'Updated At': mc.updated_at
        } for mc in masterclasses])
        
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'academy_masterclasses_export_{timestamp}.csv'
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
    finally:
        db_manager.close_session(session)


@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for statistics"""
    session = db_manager.get_session()
    try:
        stats = get_verification_statistics(session)
        return jsonify(stats)
    finally:
        db_manager.close_session(session)


@app.route('/import')
@login_required
@permission_required('import_data')
def import_page():
    """CSV import interface"""
    return render_template('import.html')


@app.route('/view-data')
@login_required
@permission_required('view_data')
def view_data_page():
    """Data viewing interface"""
    return render_template('view_data.html')


@app.route('/profiles')
@login_required
@permission_required('view_profiles')
def profiles_page():
    """User profiles interface"""
    return render_template('profiles.html')


@app.route('/api/all-users')
@login_required
@permission_required('view_profiles')
def get_all_users_api():
    """Get all users (basic info only for listing)"""
    session = db_manager.get_session()
    try:
        # Get all users ordered by name
        users = session.query(UserPII).order_by(UserPII.name).all()
        
        results = [{
            'email': u.email,
            'name': u.name,
            'phone_number': u.phone_number,
            'city': u.city,
            'state': u.state,
            'country': u.country
        } for u in users]
        
        return jsonify({'success': True, 'users': results})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_manager.close_session(session)


@app.route('/api/search-users')
@login_required
@permission_required('view_profiles')
def search_users_api():
    """Search users with advanced filters"""
    session = db_manager.get_session()
    try:
        # Build base query
        query = session.query(UserPII)
        
        # Basic search term
        search_term = request.args.get('q', '').strip()
        if search_term:
            query = query.filter(
                (UserPII.name.ilike(f'%{search_term}%')) |
                (UserPII.email.ilike(f'%{search_term}%')) |
                (UserPII.phone_number.ilike(f'%{search_term}%')) |
                (UserPII.city.ilike(f'%{search_term}%')) |
                (UserPII.state.ilike(f'%{search_term}%'))
            )
        
        # Gender filter
        gender = request.args.get('gender', '').strip()
        if gender:
            query = query.filter(UserPII.gender == gender)
        
        # Occupation filter
        occupation = request.args.get('occupation', '').strip()
        if occupation:
            query = query.filter(UserPII.occupation == occupation)
        
        # Country filter
        country = request.args.get('country', '').strip()
        if country:
            query = query.filter(UserPII.country.ilike(f'%{country}%'))
        
        # State filter
        state = request.args.get('state', '').strip()
        if state:
            query = query.filter(UserPII.state.ilike(f'%{state}%'))
        
        # City filter
        city = request.args.get('city', '').strip()
        if city:
            query = query.filter(UserPII.city.ilike(f'%{city}%'))
        
        # Academy 1.0 participation filter
        academy1 = request.args.get('academy1', '').strip()
        if academy1:
            academy1_bool = academy1.lower() == 'true'
            query = query.filter(UserPII.participated_in_academy_1 == academy1_bool)
        
        # Get users
        users = query.order_by(UserPII.name).all()
        
        # Course status filter (requires join)
        course_status = request.args.get('course_status', '').strip()
        if course_status:
            user_emails = set()
            if course_status == 'completed':
                # Users with any completed courses
                courses = session.query(Course.email).distinct().all()
                user_emails = {c.email for c in courses}
            elif course_status == 'verified':
                # Users with verified badges
                courses = session.query(Course.email).filter(Course.valid == True).distinct().all()
                user_emails = {c.email for c in courses}
            elif course_status == 'failed':
                # Users with failed verification
                courses = session.query(Course.email).filter(Course.valid == False).distinct().all()
                user_emails = {c.email for c in courses}
            elif course_status == 'pending':
                # Users with pending verification
                courses = session.query(Course.email).filter(Course.valid == None).distinct().all()
                user_emails = {c.email for c in courses}
            
            users = [u for u in users if u.email in user_emails]
        
        # Skillboost profile status filter
        skillboost_status = request.args.get('skillboost_status', '').strip()
        if skillboost_status:
            user_emails = set()
            if skillboost_status == 'verified':
                profiles = session.query(SkillboostProfile.email).filter(SkillboostProfile.valid == True).distinct().all()
                user_emails = {p.email for p in profiles}
            elif skillboost_status == 'failed':
                profiles = session.query(SkillboostProfile.email).filter(SkillboostProfile.valid == False).distinct().all()
                user_emails = {p.email for p in profiles}
            elif skillboost_status == 'pending':
                profiles = session.query(SkillboostProfile.email).filter(SkillboostProfile.valid == None).distinct().all()
                user_emails = {p.email for p in profiles}
            elif skillboost_status == 'missing':
                # Users without skillboost profile
                all_user_emails = {u.email for u in users}
                profile_emails = {p.email for p in session.query(SkillboostProfile.email).distinct().all()}
                user_emails = all_user_emails - profile_emails
            
            users = [u for u in users if u.email in user_emails]
        
        # Format results
        results = [{
            'email': u.email,
            'name': u.name,
            'phone_number': u.phone_number,
            'city': u.city,
            'state': u.state,
            'country': u.country,
            'gender': u.gender,
            'occupation': u.occupation,
            'participated_in_academy_1': u.participated_in_academy_1
        } for u in users]
        
        return jsonify({'success': True, 'users': results})
        
    except Exception as e:
        print(f"[ERROR] Search users failed: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_manager.close_session(session)


@app.route('/api/user-profile/<email>')
@login_required
@permission_required('view_profiles')
def get_user_profile(email):
    """Get complete user profile with all related data"""
    session = db_manager.get_session()
    try:
        # Get user PII
        user = session.query(UserPII).filter_by(email=email).first()
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Get Skillboost profiles
        profiles = session.query(SkillboostProfile).filter_by(email=email).all()
        
        # Get course badges
        courses = session.query(Course).filter_by(email=email).all()
        
        # Get masterclass attendance
        masterclasses = session.query(MasterClass).filter_by(email=email).all()
        
        # Format data
        profile_data = {
            'success': True,
            'user': {
                'email': user.email,
                'name': user.name,
                'phone_number': user.phone_number,
                'gender': user.gender,
                'country': user.country,
                'state': user.state,
                'city': user.city,
                'date_of_birth': str(user.date_of_birth) if user.date_of_birth else None,
                'designation': user.designation,
                'class_stream': user.class_stream,
                'degree_passout_year': user.degree_passout_year,
                'occupation': user.occupation,
                'linkedin': user.linkedin,
                'participated_in_academy_1': user.participated_in_academy_1
            },
            'skillboost_profiles': [{
                'google_cloud_skills_boost_profile_link': p.google_cloud_skills_boost_profile_link,
                'valid': p.valid,
                'remarks': p.remarks
            } for p in profiles],
            'courses': [{
                'problem_statement': c.problem_statement,
                'share_skill_badge_public_link': c.share_skill_badge_public_link,
                'valid': c.valid,
                'remarks': c.remarks
            } for c in courses],
            'masterclasses': [{
                'master_class_name': m.master_class_name,
                'platform': m.platform,
                'link': m.link,
                'total_duration': m.total_duration,
                'watch_time': m.watch_time,
                'time_watched': m.time_watched,  # Legacy field
                'live': m.live,
                'recorded': m.recorded,
                'valid': m.valid,  # Legacy field
                'started_at': m.started_at,
                'updated_at': m.updated_at
            } for m in masterclasses]
        }
        
        return jsonify(profile_data)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_manager.close_session(session)


@app.route('/api/view/<table_name>')
@login_required
@permission_required('view_data')
def view_table_data(table_name):
    """API endpoint to fetch all data from a table"""
    session = db_manager.get_session()
    try:
        records = []
        stats = {'total': 0}
        
        if table_name == 'user_pii':
            users = session.query(UserPII).all()
            records = [{
                'email': u.email,
                'name': u.name,
                'phone_number': u.phone_number,
                'gender': u.gender,
                'country': u.country,
                'state': u.state,
                'city': u.city,
                'date_of_birth': str(u.date_of_birth) if u.date_of_birth else None,
                'designation': u.designation,
                'class_stream': u.class_stream,
                'degree_passout_year': u.degree_passout_year,
                'occupation': u.occupation,
                'linkedin': u.linkedin,
                'participated_in_academy_1': u.participated_in_academy_1,
                'created_at': str(u.created_at),
                'updated_at': str(u.updated_at)
            } for u in users]
            stats['total'] = len(records)
            
        elif table_name == 'courses':
            courses = session.query(Course).all()
            records = [{
                'email': c.email,
                'problem_statement': c.problem_statement,
                'share_skill_badge_public_link': c.share_skill_badge_public_link,
                'valid': c.valid,
                'remarks': c.remarks,
                'created_at': str(c.created_at),
                'updated_at': str(c.updated_at)
            } for c in courses]
            stats['total'] = len(records)
            stats['verified'] = sum(1 for c in courses if c.valid == True)
            stats['failed'] = sum(1 for c in courses if c.valid == False)
            stats['pending'] = sum(1 for c in courses if c.valid is None)
            
        elif table_name == 'skillboost_profile':
            profiles = session.query(SkillboostProfile).all()
            records = [{
                'email': p.email,
                'google_cloud_skills_boost_profile_link': p.google_cloud_skills_boost_profile_link,
                'valid': p.valid,
                'remarks': p.remarks,
                'created_at': str(p.created_at),
                'updated_at': str(p.updated_at)
            } for p in profiles]
            stats['total'] = len(records)
            stats['verified'] = sum(1 for p in profiles if p.valid == True)
            stats['failed'] = sum(1 for p in profiles if p.valid == False)
            stats['pending'] = sum(1 for p in profiles if p.valid is None)
            
        elif table_name == 'master_classes':
            masterclasses = session.query(MasterClass).all()
            records = [{
                'email': m.email,
                'master_class_name': m.master_class_name,
                'time_watched': m.time_watched,
                'valid': m.valid,
                'started_at': str(m.started_at),
                'updated_at': str(m.updated_at)
            } for m in masterclasses]
            stats['total'] = len(records)
            
        elif table_name == 'master_log':
            logs = session.query(MasterLog).order_by(MasterLog.changed_at.desc()).limit(1000).all()
            records = [{
                'log_id': log.log_id,
                'table_name': log.table_name,
                'record_identifier': log.record_identifier,
                'action': log.action,
                'changed_at': str(log.changed_at),
                'changed_by': log.changed_by
            } for log in logs]
            stats['total'] = len(records)
        else:
            return jsonify({'success': False, 'error': 'Invalid table name'}), 400
        
        return jsonify({
            'success': True,
            'records': records,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_manager.close_session(session)


@app.route('/api/export/<table_name>')
@login_required
@permission_required('export_data')
def export_table_data(table_name):
    """Export table data as CSV"""
    session = db_manager.get_session()
    try:
        if table_name == 'user_pii':
            users = session.query(UserPII).all()
            # Normalize occupation: Convert SCHOOL_STUDENT to COLLEGE_STUDENT
            df = pd.DataFrame([{
                'Email': u.email,
                'Name': u.name,
                'Phone': u.phone_number,
                'Gender': u.gender,
                'Country': u.country,
                'State': u.state,
                'City': u.city,
                'Date of Birth': u.date_of_birth,
                'Designation': u.designation,
                'Class/Stream': u.class_stream,
                'Degree/Passout Year': u.degree_passout_year,
                'Occupation': 'COLLEGE_STUDENT' if u.occupation == 'SCHOOL_STUDENT' else u.occupation,
                'LinkedIn': u.linkedin,
                'Participated in Academy 1.0': u.participated_in_academy_1,
                'Created At': u.created_at,
                'Updated At': u.updated_at
            } for u in users])
            
        elif table_name == 'courses':
            courses = session.query(Course).all()
            df = pd.DataFrame([{
                'Email': c.email,
                'Problem Statement': c.problem_statement,
                'Badge Link': c.share_skill_badge_public_link,
                'Valid': c.valid,
                'Remarks': c.remarks,
                'Created At': c.created_at,
                'Updated At': c.updated_at
            } for c in courses])
            
        elif table_name == 'skillboost_profile':
            profiles = session.query(SkillboostProfile).all()
            df = pd.DataFrame([{
                'Email': p.email,
                'Profile Link': p.google_cloud_skills_boost_profile_link,
                'Valid': p.valid,
                'Remarks': p.remarks,
                'Created At': p.created_at,
                'Updated At': p.updated_at
            } for p in profiles])
            
        elif table_name == 'master_classes':
            masterclasses = session.query(MasterClass).all()
            df = pd.DataFrame([{
                'Email': m.email,
                'Masterclass': m.master_class_name,
                'Time Watched': m.time_watched,
                'Valid': m.valid,
                'Started At': m.started_at,
                'Updated At': m.updated_at
            } for m in masterclasses])
            
        elif table_name == 'master_log':
            logs = session.query(MasterLog).order_by(MasterLog.changed_at.desc()).limit(10000).all()
            df = pd.DataFrame([{
                'Log ID': log.log_id,
                'Table': log.table_name,
                'Record': log.record_identifier,
                'Action': log.action,
                'Changed At': log.changed_at,
                'Changed By': log.changed_by
            } for log in logs])
        else:
            return jsonify({'error': 'Invalid table'}), 400
        
        output = io.BytesIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'academy_{table_name}_export_{timestamp}.csv'
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db_manager.close_session(session)


@app.route('/api/import/upload', methods=['POST'])
@login_required
@permission_required('import_data')
def upload_csv():
    """Upload CSV file"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Invalid file type. Please upload CSV or Excel file'}), 400
    
    filepath = None
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()
        saved_filename = f"{file_id}.{file_ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
        
        print(f"[DEBUG UPLOAD] Saving file: {filename}")
        print(f"[DEBUG UPLOAD] File ID: {file_id}")
        print(f"[DEBUG UPLOAD] Save path: {filepath}")
        
        file.save(filepath)
        
        print(f"[DEBUG UPLOAD] File saved successfully, size: {os.path.getsize(filepath)} bytes")
        
        # If Excel, detect sheets and return for selection
        if file_ext in ['xlsx', 'xls']:
            try:
                # Get all sheet names
                excel_file = pd.ExcelFile(filepath)
                sheet_names = excel_file.sheet_names
                
                print(f"[DEBUG UPLOAD] Excel file detected with {len(sheet_names)} sheets: {sheet_names}")
                
                # If multiple sheets, return sheet names for user selection
                if len(sheet_names) > 1:
                    return jsonify({
                        'success': True,
                        'requires_sheet_selection': True,
                        'file_id': file_id,
                        'filename': filename,
                        'sheets': sheet_names
                    })
                
                # If only one sheet, proceed with conversion
                df = pd.read_excel(filepath, sheet_name=sheet_names[0])
                csv_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}.csv")
                df.to_csv(csv_filepath, index=False, encoding='utf-8')
                filepath = csv_filepath
            except Exception as e:
                return jsonify({'success': False, 'error': f'Failed to read Excel file: {str(e)}'}), 400
        
        # Read CSV to get columns - try multiple encodings
        df = None
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        last_error = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(filepath, nrows=5, encoding=encoding)
                break
            except Exception as e:
                last_error = e
                continue
        
        if df is None:
            return jsonify({'success': False, 'error': f'Failed to read CSV. Please ensure file is valid CSV format. Error: {str(last_error)}'}), 400
        
        # Clean column names
        columns = [str(col).strip() for col in df.columns.tolist()]
        
        # Convert preview data to JSON-safe format (handle NaN, inf, etc.)
        preview_data = []
        for _, row in df.iterrows():
            row_dict = {}
            for col in columns:
                value = row[df.columns[columns.index(col)]]
                # Convert NaN, inf to None for JSON serialization
                if pd.isna(value) or value in [float('inf'), float('-inf')]:
                    row_dict[col] = None
                else:
                    row_dict[col] = str(value) if not isinstance(value, (int, float, bool)) else value
            preview_data.append(row_dict)
        
        # Get row count
        try:
            row_count = len(pd.read_csv(filepath, encoding=encoding))
        except:
            row_count = 0
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': filename,
            'columns': columns,
            'preview': preview_data,
            'row_count': row_count
        })
    
    except Exception as e:
        # Clean up file on error
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass
        
        return jsonify({'success': False, 'error': f'Upload error: {str(e)}'}), 500


@app.route('/api/import/select-sheet', methods=['POST'])
@login_required
@permission_required('import_data')
def select_excel_sheet():
    """Convert selected Excel sheet to CSV"""
    data = request.get_json()
    file_id = data.get('file_id')
    sheet_name = data.get('sheet_name')
    
    if not file_id or not sheet_name:
        return jsonify({'success': False, 'error': 'Missing file_id or sheet_name'}), 400
    
    try:
        # Find the Excel file
        xlsx_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}.xlsx")
        xls_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}.xls")
        
        filepath = None
        if os.path.exists(xlsx_filepath):
            filepath = xlsx_filepath
        elif os.path.exists(xls_filepath):
            filepath = xls_filepath
        else:
            return jsonify({'success': False, 'error': 'Excel file not found'}), 404
        
        print(f"[DEBUG SHEET SELECT] Converting sheet '{sheet_name}' from file: {filepath}")
        
        # Read the selected sheet
        df = pd.read_excel(filepath, sheet_name=sheet_name)
        
        # Save as CSV
        csv_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}.csv")
        df.to_csv(csv_filepath, index=False, encoding='utf-8')
        
        print(f"[DEBUG SHEET SELECT] CSV created with {len(df)} rows and {len(df.columns)} columns")
        
        # Clean column names
        columns = [str(col).strip() for col in df.columns.tolist()]
        
        # Convert preview data to JSON-safe format
        preview_data = []
        for _, row in df.head(5).iterrows():
            row_dict = {}
            for col in columns:
                value = row[df.columns[columns.index(col)]]
                if pd.isna(value) or value in [float('inf'), float('-inf')]:
                    row_dict[col] = None
                else:
                    row_dict[col] = str(value) if not isinstance(value, (int, float, bool)) else value
            preview_data.append(row_dict)
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'columns': columns,
            'preview': preview_data,
            'row_count': len(df)
        })
    
    except Exception as e:
        print(f"[DEBUG SHEET SELECT ERROR] {str(e)}")
        return jsonify({'success': False, 'error': f'Failed to process sheet: {str(e)}'}), 500


@app.route('/api/import/columns/<table_name>')
@login_required
@permission_required('import_data')
def get_table_columns_api(table_name):
    """Get available columns for a table"""
    columns = get_table_columns(table_name)
    return jsonify({'success': True, 'columns': columns})


@app.route('/api/import/execute', methods=['POST'])
@login_required
@permission_required('import_data')
def execute_import():
    """Execute the CSV import with mapping"""
    try:
        data = request.json
        file_id = data.get('file_id')
        table_name = data.get('table_name', 'user_pii')
        column_mapping = data.get('column_mapping', {})
        operation_mode = data.get('operation_mode', 'create_update')
        update_keys = data.get('update_keys', ['email'])
        master_class_name = data.get('master_class_name')  # For master classes
        
        print(f"[DEBUG] Import request received: file_id={file_id}, table={table_name}, mode={operation_mode}")
        print(f"[DEBUG] Column mapping: {column_mapping}")
        print(f"[DEBUG] Update keys: {update_keys}")
        
        if not file_id:
            return jsonify({'success': False, 'error': 'No file ID provided'}), 400
        
        # For master classes, master_class_name is required
        if table_name == 'master_classes' and not master_class_name:
            return jsonify({'success': False, 'error': 'Master class name is required for master class imports'}), 400
        
        # Get file path
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}.csv")
        
        print(f"[DEBUG] Looking for file at: {filepath}")
        print(f"[DEBUG] Upload folder: {app.config['UPLOAD_FOLDER']}")
        print(f"[DEBUG] Files in upload folder: {os.listdir(app.config['UPLOAD_FOLDER']) if os.path.exists(app.config['UPLOAD_FOLDER']) else 'folder does not exist'}")
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'error': f'File not found at {filepath}'}), 404
        
        # Prepare auto-inject columns (for master classes)
        auto_inject_columns = {}
        if table_name == 'master_classes' and master_class_name:
            auto_inject_columns['master_class_name'] = master_class_name
            print(f"[DEBUG] Auto-injecting master_class_name: {master_class_name}")
        
        # Create importer
        importer = CSVImporter(
            filepath,
            column_mapping,
            operation_mode,
            update_keys,
            auto_inject_columns
        )
        
        # Import data
        success = importer.import_data(table_name)
        stats = importer.get_stats()
        
        # Clean up file
        try:
            os.remove(filepath)
        except:
            pass
        
        return jsonify({
            'success': success,
            'stats': stats
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/dashboard')
@login_required
@permission_required('view_dashboard')
def dashboard():
    """Dashboard with reports and statistics"""
    return render_template('dashboard.html')


@app.route('/badge-statistics')
@login_required
@permission_required('view_badge_stats')
def badge_statistics():
    """Badge statistics breakdown dashboard"""
    session = db_manager.get_session()
    try:
        stats_data = get_badge_statistics_breakdown(session)
        return render_template(
            'badge_statistics.html',
            badge_data=stats_data['badge_data'],
            summary=stats_data['summary']
        )
    finally:
        db_manager.close_session(session)


@app.route('/certificates')
@login_required
@permission_required('view_dashboard')
def certificates():
    """Certificate eligibility page"""
    return render_template('certificates.html')


@app.route('/api/certificates/export')
@login_required
@permission_required('export_data')
def export_certificate_users():
    """Export certificate-eligible users for a track to CSV"""
    import csv
    import io
    from flask import Response, request
    from urllib.parse import unquote
    
    track_name = request.args.get('track')
    if not track_name:
        return jsonify({'success': False, 'error': 'Track parameter is required'}), 400
    
    # Decode URL-encoded track name
    track_name = unquote(track_name)
    session = db_manager.get_session()
    try:
        eligible_users = get_certificate_eligible_users(session, track_name)
        
        if not eligible_users:
            return jsonify({'success': False, 'error': 'No eligible users found'}), 404
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Name', 'Email', 'Phone Number', 'Gender', 'Country', 'State', 'City',
            'Occupation', 'LinkedIn', 'Courses Completed', 'Total Courses',
            'Master Class Type'
        ])
        
        # Write data
        for user in eligible_users:
            writer.writerow([
                user.get('name', ''),
                user.get('email', ''),
                user.get('phone_number', ''),
                user.get('gender', ''),
                user.get('country', ''),
                user.get('state', ''),
                user.get('city', ''),
                user.get('occupation', ''),
                user.get('linkedin', ''),
                user.get('courses_completed', 0),
                user.get('total_courses', 0),
                user.get('master_class_type', '')
            ])
        
        # Create response
        output.seek(0)
        # Sanitize track name for filename
        safe_track_name = track_name.replace(' ', '_').replace('/', '_')
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={safe_track_name}_certificate_eligible_users.csv'
            }
        )
        
        return response
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_manager.close_session(session)


@app.route('/api/certificates')
@login_required
@permission_required('view_dashboard')
def get_certificate_users():
    """Get certificate-eligible users for a track"""
    from urllib.parse import unquote
    from flask import request
    
    track_name = request.args.get('track')
    if not track_name:
        return jsonify({'success': False, 'error': 'Track parameter is required'}), 400
    
    # Decode URL-encoded track name
    track_name = unquote(track_name)
    session = db_manager.get_session()
    try:
        eligible_users = get_certificate_eligible_users(session, track_name)
        return jsonify({
            'success': True,
            'track': track_name,
            'users': eligible_users,
            'count': len(eligible_users)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_manager.close_session(session)


@app.route('/api/dashboard/stats')
@login_required
@permission_required('view_dashboard')
def get_dashboard_stats():
    """Get dashboard statistics"""
    session = db_manager.get_session()
    try:
        stats = get_dashboard_statistics(session)
        demographics = get_demographic_statistics(session)
        course_stats = get_course_statistics(session)
        masterclass_stats = get_masterclass_statistics(session)
        
        return jsonify({
            'success': True,
            'stats': stats,
            'demographics': demographics,
            'courses': [
                {
                    'problem_statement': c.problem_statement,
                    'total': c.total_submissions,
                    'verified': c.verified,
                    'failed': c.failed,
                    'pending': c.pending
                }
                for c in course_stats
            ],
            'masterclasses': [
                {
                    'name': m.master_class_name,
                    'total': m.total_attendees,
                    'live_valid': m.live_valid,
                    'live_invalid': m.live_invalid,
                    'recorded_valid': m.recorded_valid,
                    'recorded_invalid': m.recorded_invalid,
                    'pending': m.pending
                }
                for m in masterclass_stats
            ]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db_manager.close_session(session)


@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return render_template('error.html', message='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    """500 error handler"""
    return render_template('error.html', message='Internal server error'), 500


if __name__ == '__main__':
    print("="*60)
    print("GenAI Academy 2.0 Records Management System")
    print("="*60)
    print(f"Starting Flask server on port {Config.FLASK_PORT}...")
    print(f"Access the application at: http://localhost:{Config.FLASK_PORT}")
    print("="*60)
    
    app.run(
        host='0.0.0.0',  # Allow external connections
        port=Config.FLASK_PORT,
        debug=(Config.FLASK_ENV == 'development')
    )

