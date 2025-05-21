# blueprints/reports.py
from flask import Blueprint, render_template, request, session
from datetime import datetime, timedelta

# Imports from main app (db, models) and other blueprints (admin_required)
# These will be imported within functions to avoid circular dependencies at load time
# and to ensure app context is available.

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/') # Path: /reports/
def generate_report(): # Renamed from 'reports' to be more descriptive
    from app import db, Customer, Transaction, login_required
    @login_required
    def actual_generate_report():
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        customer_id_str = request.args.get('customer_id')

        query = Transaction.query
        filters_applied = {}

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                query = query.filter(Transaction.date >= start_date)
                filters_applied['start_date'] = start_date_str
            except ValueError:
                pass # Or flash a message for invalid date
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                query = query.filter(Transaction.date <= end_date + timedelta(days=1)) # include whole end day
                filters_applied['end_date'] = end_date_str
            except ValueError:
                pass

        if customer_id_str and customer_id_str.isdigit():
            customer_id = int(customer_id_str)
            query = query.filter(Transaction.customer_id == customer_id)
            filters_applied['customer_id'] = customer_id
        
        transactions_data = query.order_by(Transaction.date.desc()).all()
        customers_data = Customer.query.all()

        total_payments = sum(t.amount for t in transactions_data if t.type == 'payment')
        total_credits = sum(t.amount for t in transactions_data if t.type == 'credit')
        net_balance = total_credits - total_payments

        return render_template('reports.html',
                             transactions=transactions_data,
                             customers=customers_data,
                             total_payments=total_payments,
                             total_credits=total_credits,
                             net_balance=net_balance,
                             filters_applied=filters_applied) # Pass filters for display
    return actual_generate_report()

@reports_bp.route('/credit') # Path: /reports/credit
def credit_report():
    from app import db, Customer, login_required
    from .auth import admin_required # Assuming auth.py has admin_required
    @login_required
    @admin_required
    def actual_credit_report():
        # customers_data = Customer.query.order_by(Customer.outstanding_balance.desc()).all()
        # outstanding_balance is a property, may not work directly in order_by with all DBs
        # Fetch all and sort in Python if direct DB sort is problematic
        all_customers = Customer.query.all()
        # Sort customers by outstanding_balance in descending order
        customers_data = sorted(all_customers, key=lambda c: c.outstanding_balance, reverse=True)
        return render_template('credit_report.html', customers=customers_data)
    return actual_credit_report()
