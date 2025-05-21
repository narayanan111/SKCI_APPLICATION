# blueprints/invoices.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
import json
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

# Imports from main app (db, models) and other blueprints (admin_required)
# These will be imported within functions to avoid circular dependencies at load time
# and to ensure app context is available.

invoices_bp = Blueprint('invoices', __name__, url_prefix='/invoices')

# Helper to get next invoice number (moved from app.py)
def get_next_invoice_number():
    from app import Invoice # Import here
    last_invoice = Invoice.query.order_by(Invoice.invoice_number.desc()).first()
    return (last_invoice.invoice_number + 1) if last_invoice else 1

@invoices_bp.route('/create', methods=['GET', 'POST']) # Changed from /create_invoice
def create_invoice():
    from app import db, Product, Invoice, InvoiceItem, Customer, login_required
    @login_required
    def actual_create_invoice():
        if request.method == 'POST':
            data = request.form
            customer_id = data.get('customer_id')
            date_str = data.get('date')
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
                # Rerender form with existing data if possible, or redirect
                # For simplicity, redirecting to GET
                customers = Customer.query.all()
                products = [p.to_dict() for p in Product.query.all()]
                return render_template('create_invoice.html',
                                       customers=customers,
                                       products=products,
                                       next_invoice_number=get_next_invoice_number())


            payment_mode = data.get('payment_mode')
            transport_charges = float(data.get('transport_charges', 0))
            round_off = float(data.get('round_off', 0))
            vehicle_no = data.get('vehicle_no')
            delivery_date_str = data.get('delivery_date')
            delivery_date = datetime.strptime(delivery_date_str, '%Y-%m-%d') if delivery_date_str else None
            destination = data.get('destination')
            items_json = data.get('items')
            
            items = []
            if items_json:
                try:
                    items = json.loads(items_json)
                except json.JSONDecodeError:
                    flash('Invalid items data.', 'danger')
                    # Rerender form
                    customers = Customer.query.all()
                    products = [p.to_dict() for p in Product.query.all()]
                    return render_template('create_invoice.html',
                                           customers=customers,
                                           products=products,
                                           next_invoice_number=get_next_invoice_number())


            # Calculate totals
            subtotal = 0
            total_taxable = 0
            total_cgst = 0
            total_sgst = 0
            grand_total = 0
            invoice_items_to_create = [] # Renamed to avoid confusion with model name
            for item_data in items: # Renamed item to item_data
                product = Product.query.get(item_data['product_id'])
                if not product:
                    flash(f"Product with ID {item_data['product_id']} not found.", 'danger')
                    # Rerender or handle error
                    customers = Customer.query.all()
                    products = [p.to_dict() for p in Product.query.all()]
                    return render_template('create_invoice.html',
                                           customers=customers,
                                           products=products,
                                           next_invoice_number=get_next_invoice_number())

                qty = float(item_data['quantity'])
                rate = float(item_data['rate'])
                discount_percent = float(item_data.get('discount_percent', 0))
                hsn = product.hsn
                gst_percent = product.gst_percent
                price = rate * qty
                discount = price * (discount_percent / 100)
                taxable = price - discount
                cgst = taxable * (gst_percent / 2) / 100
                sgst = taxable * (gst_percent / 2) / 100
                amount = taxable + cgst + sgst
                subtotal += price
                total_taxable += taxable
                total_cgst += cgst
                total_sgst += sgst
                grand_total += amount
                invoice_items_to_create.append({
                    'product_id': product.id,
                    'quantity': qty,
                    'rate': rate,
                    'discount_percent': discount_percent,
                    'hsn': hsn,
                    'gst_percent': gst_percent,
                    'amount': amount
                })
            grand_total += transport_charges + round_off

            # Create Invoice
            invoice_number = get_next_invoice_number()
            new_invoice = Invoice( # Renamed from invoice to new_invoice
                invoice_number=invoice_number,
                customer_id=customer_id,
                date=date,
                payment_mode=payment_mode,
                transport_charges=transport_charges,
                round_off=round_off,
                total_amount=grand_total,
                created_by=session['user_id'],
                vehicle_no=vehicle_no,
                delivery_date=delivery_date,
                destination=destination
            )
            db.session.add(new_invoice)
            db.session.flush()  # Get new_invoice.id

            # Add Invoice Items
            for item_to_create in invoice_items_to_create: # Renamed item to item_to_create
                invoice_item = InvoiceItem(
                    invoice_id=new_invoice.id,
                    product_id=item_to_create['product_id'],
                    quantity=item_to_create['quantity'],
                    rate=item_to_create['rate'],
                    discount_percent=item_to_create['discount_percent'],
                    hsn=item_to_create['hsn'],
                    gst_percent=item_to_create['gst_percent'],
                    amount=item_to_create['amount']
                )
                db.session.add(invoice_item)
        
        try:
            db.session.commit()
            flash('Invoice created successfully.', 'success')
            return redirect(url_for('invoices.view_invoice', invoice_id=new_invoice.id))
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in {request.endpoint} while creating invoice: {str(e)}")
            flash('Error: Could not create invoice due to a database issue. Please try again.', 'danger')
            # Re-render form with existing data by not redirecting, but rather falling through to the GET part
            # The form data is largely in `data` and `items` which are in scope for the GET render
    
    # GET: Render invoice creation form (also used as fallback on POST error)
        customers = Customer.query.all()
        products = [p.to_dict() for p in Product.query.all()]
        return render_template('create_invoice.html',
                               customers=customers,
                               products=products,
                               next_invoice_number=get_next_invoice_number())
    return actual_create_invoice()

@invoices_bp.route('/<int:invoice_id>') # Path changed from /invoice/<invoice_id>
def view_invoice(invoice_id):
    from app import db, Invoice, Customer, InvoiceItem, login_required
    @login_required
    def actual_view_invoice():
        invoice = Invoice.query.get_or_404(invoice_id)
        customer = Customer.query.get(invoice.customer_id)
        items = InvoiceItem.query.filter_by(invoice_id=invoice.id).all()
        return render_template('view_invoice.html', invoice=invoice, customer=customer, items=items)
    return actual_view_invoice(invoice_id)

@invoices_bp.route('/<int:invoice_id>/print_receipt')
def print_receipt(invoice_id):
    from app import db, Invoice, Customer, InvoiceItem, login_required
    @login_required
    def actual_print_receipt():
        invoice = Invoice.query.get_or_404(invoice_id)
        customer = Customer.query.get(invoice.customer_id)
        items = InvoiceItem.query.filter_by(invoice_id=invoice.id).all()
        return render_template('print_receipt.html', invoice=invoice, customer=customer, items=items)
    return actual_print_receipt(invoice_id)

@invoices_bp.route('/<int:invoice_id>/print_a4')
def print_invoice_a4(invoice_id):
    from app import db, Invoice, Customer, InvoiceItem, login_required
    @login_required
    def actual_print_invoice_a4():
        invoice = Invoice.query.get_or_404(invoice_id)
        customer = Customer.query.get(invoice.customer_id)
        items = InvoiceItem.query.filter_by(invoice_id=invoice.id).all()
        return render_template('print_invoice_a4.html', invoice=invoice, customer=customer, items=items)
    return actual_print_invoice_a4(invoice_id)

@invoices_bp.route('/') # Path changed from /invoices
def list_invoices(): # Renamed from 'invoices'
    from app import db, Invoice, Customer, login_required
    @login_required
    def actual_list_invoices():
        invoices_data = Invoice.query.order_by(Invoice.date.desc()).all()
        customers_data = {c.id: c for c in Customer.query.all()}
        return render_template('invoices.html', invoices=invoices_data, customers=customers_data)
    return actual_list_invoices()

@invoices_bp.route('/delete/<int:id>', methods=['POST']) # Path changed from /delete_invoice/<id>
def delete_invoice(id):
    from app import db, Invoice, login_required
    from .auth import admin_required
    @login_required
    @admin_required
    def actual_delete_invoice(invoice_id_to_delete): # Renamed id to avoid confusion
        invoice = Invoice.query.get_or_404(invoice_id_to_delete)
        invoice_number_to_delete = invoice.invoice_number # For logging
        try:
            db.session.delete(invoice)
            db.session.commit()
            flash(f'Invoice {invoice_number_to_delete} deleted successfully.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in {request.endpoint} attempting to delete invoice {invoice_number_to_delete} (ID: {invoice_id_to_delete}): {str(e)}")
            flash('Error: Could not delete invoice due to a database issue. Please try again.', 'danger')
        return redirect(url_for('invoices.list_invoices'))
    return actual_delete_invoice(id) # Pass original id to inner function
