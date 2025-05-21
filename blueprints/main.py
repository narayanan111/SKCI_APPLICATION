# blueprints/main.py
from flask import Blueprint, render_template, session, redirect, url_for, flash
from sqlalchemy import func
from datetime import datetime

# login_required and models will be imported from app.py within the route
# to avoid circular dependencies and ensure app context is available.

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    from app import db, Customer, Transaction, login_required # Import here
    
    # Apply login_required decorator
    # This is a bit unconventional to apply it *inside* but ensures it has app context
    # A more common way is to apply it when registering the blueprint or on the whole blueprint
    
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('auth.login')) # Assuming auth_bp has a login route named 'login'

    # Get statistics
    total_customers = Customer.query.count()
    total_credit = sum(customer.get_balance() for customer in Customer.query.all()) # get_balance might need adjustment if it relies on app context not available this way
    today = datetime.utcnow().date()
    
    today_payments = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.type == 'payment',
        func.date(Transaction.date) == today
    ).scalar() or 0
    
    pending_payments = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.type == 'credit' # This should ideally be outstanding invoices not just credit transactions
    ).scalar() or 0

    # Get recent transactions
    recent_transactions = Transaction.query.order_by(Transaction.date.desc()).limit(10).all()

    return render_template('dashboard.html',
                         total_customers=total_customers,
                         total_credit=total_credit,
                         today_payments=today_payments,
                         pending_payments=pending_payments,
                         recent_transactions=recent_transactions)
