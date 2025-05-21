# blueprints/customers.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from sqlalchemy.exc import SQLAlchemyError

# Imports from main app (db, models) and other blueprints (admin_required)
# These will be imported within functions to avoid circular dependencies at load time
# and to ensure app context is available.

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')

@customers_bp.route('/')
def list_customers(): # Renamed from 'customers' to avoid conflict with blueprint name
    from app import db, Customer, login_required
    @login_required
    def actual_list_customers():
        customers_data = Customer.query.all()
        return render_template('customers.html', customers=customers_data)
    return actual_list_customers()

@customers_bp.route('/add', methods=['GET', 'POST']) # Changed from /add_customer
def add_customer():
    from app import db, Customer, login_required
    @login_required
    def actual_add_customer():
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            address = request.form.get('address')
            gstin = request.form.get('gstin')
            credit_limit = float(request.form.get('credit_limit', 0))
            if Customer.query.filter_by(email=email).first():
                flash('Email already exists.', 'danger')
                return redirect(url_for('customers.add_customer'))
            
            customer = Customer(name=name, email=email, phone=phone, address=address, gstin=gstin, credit_limit=credit_limit)
            try:
                db.session.add(customer)
                db.session.commit()
                flash('Customer added successfully.', 'success')
                return redirect(url_for('customers.list_customers'))
            except SQLAlchemyError as e:
                db.session.rollback()
                current_app.logger.error(f"Database error in {request.endpoint} for customer {name}: {str(e)}")
                flash('Error: Could not add customer due to a database issue. Please try again.', 'danger')
                # Re-render the form with existing data if possible
                return render_template('add_customer.html', name=name, email=email, phone=phone, address=address, gstin=gstin, credit_limit=credit_limit)
        
        return render_template('add_customer.html')
    return actual_add_customer()

@customers_bp.route('/edit/<int:id>', methods=['GET', 'POST']) 
def edit_customer(id):
    from app import db, Customer, login_required
    from .auth import admin_required 
    @login_required
    @admin_required
    def actual_edit_customer(customer_id): # Pass id as customer_id
        customer = Customer.query.get_or_404(customer_id)
        original_name = customer.name # For logging
        if request.method == 'POST':
            try:
                customer.name = request.form.get('name')
                customer.email = request.form.get('email')
                customer.phone = request.form.get('phone')
                customer.address = request.form.get('address')
                customer.gstin = request.form.get('gstin')
                customer.credit_limit = float(request.form.get('credit_limit', 0))
                db.session.commit()
                flash('Customer updated successfully.', 'success')
                return redirect(url_for('customers.list_customers'))
            except SQLAlchemyError as e:
                db.session.rollback()
                current_app.logger.error(f"Database error in {request.endpoint} for customer {original_name} (ID: {customer_id}): {str(e)}")
                flash('Error: Could not update customer due to a database issue. Please try again.', 'danger')
                # Re-render form with existing data
                return render_template('edit_customer.html', customer=customer) 
        
        return render_template('edit_customer.html', customer=customer)
    return actual_edit_customer(id) # Pass id to inner function


@customers_bp.route('/view/<int:id>') 
def view_customer(id):
    from app import db, Customer, Invoice, Transaction, login_required
    @login_required
    def actual_view_customer(customer_id): # Pass id as customer_id
        customer = Customer.query.get_or_404(customer_id)
        invoices_data = Invoice.query.filter_by(customer_id=customer_id).all()
        payments_data = Transaction.query.filter_by(customer_id=customer_id, type='payment').all()
        return render_template('view_customer.html', customer=customer, invoices=invoices_data, payments=payments_data)
    return actual_view_customer(id) # Pass id to inner function


@customers_bp.route('/delete/<int:id>', methods=['POST']) 
def delete_customer(id):
    from app import db, Customer, Invoice, login_required
    from .auth import admin_required
    @login_required
    @admin_required
    def actual_delete_customer(customer_id): # Pass id as customer_id
        customer = Customer.query.get_or_404(customer_id)
        customer_name_to_delete = customer.name # For logging
        if customer.outstanding_balance > 0 or Invoice.query.filter_by(customer_id=customer_id).count() > 0:
            flash('Cannot delete customer with outstanding balance or invoices.', 'danger')
            return redirect(url_for('customers.list_customers'))
        
        try:
            db.session.delete(customer)
            db.session.commit()
            flash('Customer deleted successfully.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in {request.endpoint} attempting to delete customer {customer_name_to_delete} (ID: {customer_id}): {str(e)}")
            flash('Error: Could not delete customer due to a database issue. Please try again.', 'danger')
            
        return redirect(url_for('customers.list_customers'))
    return actual_delete_customer(id) # Pass id to inner function
