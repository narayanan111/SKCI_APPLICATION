# blueprints/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError

# Imports from main app (adjust path if necessary, e.g. if app.py is in a specific package)
# For now, we'll define placeholders and assume they are imported correctly in app.py
# from ..app import db, User, login_required # This needs to be handled in app.py by passing app context or using current_app

auth_bp = Blueprint('auth', __name__) # No url_prefix, login and logout are top-level

# login_required will be imported from app.py
# admin_required is defined here and used by routes in this blueprint and others

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.index')) # Assuming 'main.index' is the main dashboard
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    from app import db, User # Import here to avoid circular dependencies at load time
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            flash('Welcome back!', 'success')
            return redirect(url_for('main.index')) # Assuming 'main.index' for the main page
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login')) # Redirect to login page

# Settings Routes (Admin only, but user specific parts like change_password are here)
@auth_bp.route('/settings')
def settings(): # login_required will be applied in app.py or when registering blueprint
    from app import db, User, login_required # Import here
    @login_required
    @admin_required
    def actual_settings():
        users = User.query.all()
        return render_template('settings.html', users=users)
    return actual_settings()


@auth_bp.route('/add_user', methods=['POST'])
def add_user(): # login_required and admin_required applied
    from app import db, User, login_required
    @login_required
    @admin_required
    def actual_add_user():
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('auth.settings'))

        user = User(
            username=username,
            password=generate_password_hash(password),
            role=role
        )
        try:
            db.session.add(user)
            db.session.commit()
            flash('User added successfully.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in {request.endpoint} for user {username}: {str(e)}")
            flash('Error: Could not add user due to a database issue. Please try again.', 'danger')
        
        return redirect(url_for('auth.settings'))
    return actual_add_user()

@auth_bp.route('/edit_user/<int:id>', methods=['POST'])
def edit_user(id): # login_required and admin_required applied
    from app import db, User, login_required
    @login_required
    @admin_required
    def actual_edit_user(user_id): # Pass id as user_id
        user = User.query.get_or_404(user_id)
        original_username = user.username # For logging
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            role = request.form.get('role')

            if User.query.filter(User.username == username, User.id != user_id).first():
                flash('Username already exists.', 'danger')
                return redirect(url_for('auth.settings'))

            user.username = username
            if password:
                user.password = generate_password_hash(password)
            user.role = role

            db.session.commit()
            flash('User updated successfully.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in {request.endpoint} for user {original_username} (ID: {user_id}): {str(e)}")
            flash('Error: Could not update user due to a database issue. Please try again.', 'danger')
        
        return redirect(url_for('auth.settings'))
    return actual_edit_user(id) # Pass id to the inner function


@auth_bp.route('/delete_user/<int:id>')
def delete_user(id): # login_required and admin_required applied
    from app import db, User, login_required
    @login_required
    @admin_required
    def actual_delete_user(user_id): # Pass id as user_id
        user = User.query.get_or_404(user_id)
        username_to_delete = user.username # For logging
        if user.id == session['user_id']:
            flash('You cannot delete your own account.', 'danger')
            return redirect(url_for('auth.settings'))
        try:
            db.session.delete(user)
            db.session.commit()
            flash('User deleted successfully.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in {request.endpoint} attempting to delete user {username_to_delete} (ID: {user_id}): {str(e)}")
            flash('Error: Could not delete user due to a database issue. Please try again.', 'danger')

        return redirect(url_for('auth.settings'))
    return actual_delete_user(id) # Pass id to the inner function


@auth_bp.route('/change_password', methods=['POST'])
def change_password(): # login_required applied
    from app import db, User, login_required
    @login_required
    def actual_change_password():
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        user = User.query.get(session['user_id'])
        username_for_log = user.username # For logging

        if not check_password_hash(user.password, current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('auth.settings'))

        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('auth.settings'))

        try:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            flash('Password updated successfully.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in {request.endpoint} for user {username_for_log}: {str(e)}")
            flash('Error: Could not change password due to a database issue. Please try again.', 'danger')
            
        return redirect(url_for('auth.settings'))
    return actual_change_password()
