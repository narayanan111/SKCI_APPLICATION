# blueprints/transactions.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

# Imports from main app (db, models, socketio)
# These will be imported within functions to avoid circular dependencies at load time
# and to ensure app context is available.

transactions_bp = Blueprint('transactions', __name__) # No url_prefix here, will be added in app.py

@transactions_bp.route('/add', methods=['GET', 'POST']) # Path: /transactions/add
def add_transaction():
    from app import db, Customer, Transaction, login_required, socketio
    @login_required
    def actual_add_transaction():
        if request.method == 'POST':
            customer_id = request.form.get('customer_id')
            type = request.form.get('type')
            amount = float(request.form.get('amount'))
            description = request.form.get('description')
            date_str = request.form.get('date')
            
            try:
                date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid date format for transaction.', 'danger')
                customers = Customer.query.all()
                return render_template('add_transaction.html', customers=customers, now=datetime.utcnow())

            customer = Customer.query.get_or_404(customer_id)
            if type == 'credit' and customer.get_balance() + amount > customer.credit_limit:
                flash('Transaction would exceed credit limit.', 'danger')
                customers = Customer.query.all()
                return render_template('add_transaction.html', customers=customers, now=datetime.utcnow(), current_data=request.form)


            transaction = Transaction(
                customer_id=customer_id,
                type=type,
                amount=amount,
                description=description,
                date=date
            )
        try:
            db.session.add(transaction)
            db.session.commit()

            # Emit real-time updates
            socketio.emit('transaction_added', transaction.to_dict())
            socketio.emit('customer_updated', customer.to_dict())

            flash('Transaction added successfully.', 'success')
            return redirect(url_for('customers.view_customer', id=customer_id))
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in {request.endpoint} for customer {customer_id} while adding transaction: {str(e)}")
            flash('Error: Could not add transaction due to a database issue. Please try again.', 'danger')
            # Re-render form with existing data
            customers = Customer.query.all()
            return render_template('add_transaction.html', customers=customers, now=datetime.utcnow(), current_data=request.form)

    customers = Customer.query.all() # For GET request
        return render_template('add_transaction.html', customers=customers, now=datetime.utcnow())
    return actual_add_transaction()

@transactions_bp.route('/payments') # Path: /transactions/payments
def list_payments(): # Renamed from 'payments'
    from app import db, Transaction, Customer, login_required
    @login_required
    def actual_list_payments():
        payments_data = Transaction.query.filter_by(type='payment').order_by(Transaction.date.desc()).all()
        customers_data = {c.id: c for c in Customer.query.all()}
        return render_template('payments.html', payments=payments_data, customers=customers_data)
    return actual_list_payments()

@transactions_bp.route('/payments/add', methods=['GET', 'POST']) # Path: /transactions/payments/add
def add_payment():
    from app import db, Customer, Transaction, login_required
    @login_required
    def actual_add_payment():
        if request.method == 'POST':
            customer_id = request.form.get('customer_id')
            amount = float(request.form.get('amount', 0))
            payment_mode = request.form.get('payment_mode')
            notes = request.form.get('notes')
            date_str = request.form.get('date') # Assuming date comes as string from form
            
            try:
                # Attempt to parse date if it's a full datetime, or just date
                if 'T' in date_str:
                     date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
                else:
                     date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format for payment.', 'danger')
                customers = Customer.query.all()
                return render_template('add_payment.html', customers=customers)


            payment = Transaction(
                customer_id=customer_id,
                type='payment',
                amount=amount,
                description=notes or '',
                date=date,
                payment_mode=payment_mode
            )
        try:
            db.session.add(payment)
            db.session.commit()
            flash('Payment recorded successfully.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in {request.endpoint} for customer {customer_id} while adding payment: {str(e)}")
            flash('Error: Could not record payment due to a database issue. Please try again.', 'danger')
            # Re-render form, ideally with data
            customers = Customer.query.all()
            return render_template('add_payment.html', customers=customers, current_data=request.form)
            
            return redirect(url_for('transactions.list_payments'))

    customers = Customer.query.all() # For GET request
        return render_template('add_payment.html', customers=customers)
    return actual_add_payment()
