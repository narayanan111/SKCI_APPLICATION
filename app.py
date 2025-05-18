from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import os
from sqlalchemy import func, and_
from config import config
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config.from_object(config['development'])

# Get the absolute path to the database directory
basedir = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.join(basedir, 'database')
db_path = os.path.join(db_dir, 'cms.db')

# Create database directory if it doesn't exist
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
# socketio = SocketIO(app, cors_allowed_origins="*")
# socketio = SocketIO(app, cors_allowed_origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='staff')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __init__(self, username, password, role='staff'):
        self.username = username
        self.password = password
        self.role = role
        self.created_at = datetime.utcnow()

# Product Model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    hsn = db.Column(db.String(20), nullable=False)
    gst_percent = db.Column(db.Float, nullable=False, default=0.0)
    price = db.Column(db.Float, nullable=False, default=0.0)
    invoice_items = db.relationship('InvoiceItem', backref='product', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'hsn': self.hsn,
            'gst_percent': self.gst_percent,
            'price': self.price
        }

# Invoice Model
class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.Integer, unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    payment_mode = db.Column(db.String(50), nullable=False)
    transport_charges = db.Column(db.Float, nullable=False, default=0.0)
    round_off = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade="all, delete-orphan")
    vehicle_no = db.Column(db.String(50), nullable=True)
    delivery_date = db.Column(db.Date, nullable=True)
    destination = db.Column(db.String(100), nullable=True)

# InvoiceItem Model
class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1.0)
    rate = db.Column(db.Float, nullable=False, default=0.0)
    discount_percent = db.Column(db.Float, nullable=False, default=0.0)
    hsn = db.Column(db.String(20), nullable=False)
    gst_percent = db.Column(db.Float, nullable=False, default=0.0)
    amount = db.Column(db.Float, nullable=False, default=0.0)

# Update Customer Model
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    gstin = db.Column(db.String(20), nullable=True)
    credit_limit = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    transactions = db.relationship('Transaction', backref='customer', lazy=True)
    invoices = db.relationship('Invoice', backref='customer', lazy=True)

    @property
    def outstanding_balance(self):
        total_invoices = sum(inv.total_amount for inv in self.invoices)
        total_credits = sum(tx.amount for tx in self.transactions if tx.type == 'credit')
        total_payments = sum(tx.amount for tx in self.transactions if tx.type == 'payment')
        return total_invoices + total_credits - total_payments

    def get_balance(self):
        return self.outstanding_balance

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'gstin': self.gstin,
            'credit_limit': self.credit_limit,
            'outstanding_balance': self.outstanding_balance,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }

# Update Transaction/Payment Model
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'credit' or 'payment'
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    payment_mode = db.Column(db.String(50), nullable=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'type': self.type,
            'amount': self.amount,
            'description': self.description,
            'date': self.date.strftime('%Y-%m-%d %H:%M:%S'),
            'payment_mode': self.payment_mode,
            'invoice_id': self.invoice_id
        }

# Authentication middleware
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Routes
@app.route('/')
@login_required
def index():
    # Get statistics
    total_customers = Customer.query.count()
    total_credit = sum(customer.get_balance() for customer in Customer.query.all())
    today = datetime.utcnow().date()
    today_payments = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.type == 'payment',
        func.date(Transaction.date) == today
    ).scalar() or 0
    pending_payments = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.type == 'credit'
    ).scalar() or 0

    # Get recent transactions
    recent_transactions = Transaction.query.order_by(Transaction.date.desc()).limit(10).all()

    return render_template('dashboard.html',
                         total_customers=total_customers,
                         total_credit=total_credit,
                         today_payments=today_payments,
                         pending_payments=pending_payments,
                         recent_transactions=recent_transactions)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            flash('Welcome back!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Customer Management Routes
@app.route('/customers')
@login_required
def customers():
    customers = Customer.query.all()
    return render_template('customers.html', customers=customers)

@app.route('/add_customer', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        gstin = request.form.get('gstin')
        credit_limit = float(request.form.get('credit_limit', 0))
        if Customer.query.filter_by(email=email).first():
            flash('Email already exists.', 'danger')
            return redirect(url_for('add_customer'))
        customer = Customer(name=name, email=email, phone=phone, address=address, gstin=gstin, credit_limit=credit_limit)
        db.session.add(customer)
        db.session.commit()
        flash('Customer added successfully.', 'success')
        return redirect(url_for('customers'))
    return render_template('add_customer.html')

@app.route('/edit_customer/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    if request.method == 'POST':
        customer.name = request.form.get('name')
        customer.email = request.form.get('email')
        customer.phone = request.form.get('phone')
        customer.address = request.form.get('address')
        customer.gstin = request.form.get('gstin')
        customer.credit_limit = float(request.form.get('credit_limit', 0))
        db.session.commit()
        flash('Customer updated successfully.', 'success')
        return redirect(url_for('customers'))
    return render_template('edit_customer.html', customer=customer)

@app.route('/view_customer/<int:id>')
@login_required
def view_customer(id):
    customer = Customer.query.get_or_404(id)
    invoices = Invoice.query.filter_by(customer_id=id).all()
    payments = Transaction.query.filter_by(customer_id=id, type='payment').all()
    return render_template('view_customer.html', customer=customer, invoices=invoices, payments=payments)

@app.route('/delete_customer/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    if customer.outstanding_balance > 0 or Invoice.query.filter_by(customer_id=id).count() > 0:
        flash('Cannot delete customer with outstanding balance or invoices.', 'danger')
        return redirect(url_for('customers'))
    db.session.delete(customer)
    db.session.commit()
    flash('Customer deleted successfully.', 'success')
    return redirect(url_for('customers'))

# Transaction Routes
@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        type = request.form.get('type')
        amount = float(request.form.get('amount'))
        description = request.form.get('description')
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%dT%H:%M')

        customer = Customer.query.get_or_404(customer_id)
        if type == 'credit' and customer.get_balance() + amount > customer.credit_limit:
            flash('Transaction would exceed credit limit.', 'danger')
            return redirect(url_for('add_transaction'))

        transaction = Transaction(
            customer_id=customer_id,
            type=type,
            amount=amount,
            description=description,
            date=date
        )
        db.session.add(transaction)
        db.session.commit()

        # Emit real-time updates
        socketio.emit('transaction_added', transaction.to_dict())
        socketio.emit('customer_updated', customer.to_dict())

        flash('Transaction added successfully.', 'success')
        return redirect(url_for('view_customer', id=customer_id))

    customers = Customer.query.all()
    return render_template('add_transaction.html', customers=customers, now=datetime.utcnow())

# Reports Routes
@app.route('/reports')
@login_required
def reports():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    customer_id = request.args.get('customer_id')

    query = Transaction.query

    if start_date:
        query = query.filter(Transaction.date >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Transaction.date <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
    if customer_id:
        query = query.filter(Transaction.customer_id == customer_id)

    transactions = query.order_by(Transaction.date.desc()).all()
    customers = Customer.query.all()

    total_payments = sum(t.amount for t in transactions if t.type == 'payment')
    total_credits = sum(t.amount for t in transactions if t.type == 'credit')
    net_balance = total_credits - total_payments

    return render_template('reports.html',
                         transactions=transactions,
                         customers=customers,
                         total_payments=total_payments,
                         total_credits=total_credits,
                         net_balance=net_balance)

# Settings Routes (Admin only)
@app.route('/settings')
@login_required
@admin_required
def settings():
    users = User.query.all()
    return render_template('settings.html', users=users)

@app.route('/add_user', methods=['POST'])
@login_required
@admin_required
def add_user():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')

    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'danger')
        return redirect(url_for('settings'))

    user = User(
        username=username,
        password=generate_password_hash(password),
        role=role
    )
    db.session.add(user)
    db.session.commit()

    flash('User added successfully.', 'success')
    return redirect(url_for('settings'))

@app.route('/edit_user/<int:id>', methods=['POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')

    if User.query.filter(User.username == username, User.id != id).first():
        flash('Username already exists.', 'danger')
        return redirect(url_for('settings'))

    user.username = username
    if password:
        user.password = generate_password_hash(password)
    user.role = role

    db.session.commit()
    flash('User updated successfully.', 'success')
    return redirect(url_for('settings'))

@app.route('/delete_user/<int:id>')
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    if user.id == session['user_id']:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('settings'))

    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('settings'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    user = User.query.get(session['user_id'])
    if not check_password_hash(user.password, current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('settings'))

    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('settings'))

    user.password = generate_password_hash(new_password)
    db.session.commit()
    flash('Password updated successfully.', 'success')
    return redirect(url_for('settings'))

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    if 'user_id' in session:
        emit('connection_response', {'data': 'Connected'})

@socketio.on('get_customers')
def handle_get_customers():
    customers = Customer.query.all()
    emit('customers_data', {'customers': [customer.to_dict() for customer in customers]})

@socketio.on('get_transactions')
def handle_get_transactions(data):
    customer_id = data.get('customer_id')
    if customer_id:
        transactions = Transaction.query.filter_by(customer_id=customer_id).order_by(Transaction.date.desc()).all()
    else:
        transactions = Transaction.query.order_by(Transaction.date.desc()).all()
    emit('transactions_data', {'transactions': [t.to_dict() for t in transactions]})

# Helper to get next invoice number
def get_next_invoice_number():
    last_invoice = Invoice.query.order_by(Invoice.invoice_number.desc()).first()
    return (last_invoice.invoice_number + 1) if last_invoice else 1

# Initialize database and create default users
def init_db():
    with app.app_context():
        # Create database directory if it doesn't exist
        os.makedirs('database', exist_ok=True)
        
        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()

        # Create default users if they don't exist
        if not User.query.filter_by(username=app.config['ADMIN_USERNAME']).first():
            admin = User(
                username=app.config['ADMIN_USERNAME'],
                password=generate_password_hash(app.config['ADMIN_PASSWORD']),
                role='admin'
            )
            db.session.add(admin)
            
        if not User.query.filter_by(username=app.config['STAFF_USERNAME']).first():
            staff = User(
                username=app.config['STAFF_USERNAME'],
                password=generate_password_hash(app.config['STAFF_PASSWORD']),
                role='staff'
            )
            db.session.add(staff)
            
        db.session.commit()

@app.route('/create_invoice', methods=['GET', 'POST'])
@login_required
def create_invoice():
    if request.method == 'POST':
        data = request.form
        customer_id = data.get('customer_id')
        date = datetime.strptime(data.get('date'), '%Y-%m-%d')
        payment_mode = data.get('payment_mode')
        transport_charges = float(data.get('transport_charges', 0))
        round_off = float(data.get('round_off', 0))
        vehicle_no = data.get('vehicle_no')
        delivery_date = datetime.strptime(data.get('delivery_date'), '%Y-%m-%d') if data.get('delivery_date') else None
        destination = data.get('destination')
        items = []
        # Expecting items as JSON string (from JS form)
        import json
        if 'items' in data:
            items = json.loads(data.get('items'))

        # Calculate totals
        subtotal = 0
        total_taxable = 0
        total_cgst = 0
        total_sgst = 0
        grand_total = 0
        invoice_items = []
        for item in items:
            product = Product.query.get(item['product_id'])
            qty = float(item['quantity'])
            rate = float(item['rate'])
            discount_percent = float(item.get('discount_percent', 0))
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
            invoice_items.append({
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
        invoice = Invoice(
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
        db.session.add(invoice)
        db.session.flush()  # Get invoice.id

        # Add Invoice Items
        for item in invoice_items:
            invoice_item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                rate=item['rate'],
                discount_percent=item['discount_percent'],
                hsn=item['hsn'],
                gst_percent=item['gst_percent'],
                amount=item['amount']
            )
            db.session.add(invoice_item)

        db.session.commit()
        flash('Invoice created successfully.', 'success')
        return redirect(url_for('view_invoice', invoice_id=invoice.id))

    # GET: Render invoice creation form
    customers = Customer.query.all()
    products = [p.to_dict() for p in Product.query.all()]
    return render_template('create_invoice.html',
                           customers=customers,
                           products=products,
                           next_invoice_number=get_next_invoice_number())

@app.route('/invoice/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    customer = Customer.query.get(invoice.customer_id)
    items = InvoiceItem.query.filter_by(invoice_id=invoice.id).all()
    return render_template('view_invoice.html', invoice=invoice, customer=customer, items=items)

@app.route('/invoice/<int:invoice_id>/print_receipt')
@login_required
def print_receipt(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    customer = Customer.query.get(invoice.customer_id)
    items = InvoiceItem.query.filter_by(invoice_id=invoice.id).all()
    return render_template('print_receipt.html', invoice=invoice, customer=customer, items=items)

@app.route('/invoice/<int:invoice_id>/print_a4')
@login_required
def print_invoice_a4(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    customer = Customer.query.get(invoice.customer_id)
    items = InvoiceItem.query.filter_by(invoice_id=invoice.id).all()
    return render_template('print_invoice_a4.html', invoice=invoice, customer=customer, items=items)

@app.route('/products')
@login_required
@admin_required
def products():
    products = Product.query.all()
    return render_template('products.html', products=products)

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        hsn = request.form.get('hsn')
        gst_percent = float(request.form.get('gst_percent', 0))
        price = float(request.form.get('price', 0))
        product = Product(name=name, hsn=hsn, gst_percent=gst_percent, price=price)
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully.', 'success')
        return redirect(url_for('products'))
    return render_template('add_product.html')

@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.hsn = request.form.get('hsn')
        product.gst_percent = float(request.form.get('gst_percent', 0))
        product.price = float(request.form.get('price', 0))
        db.session.commit()
        flash('Product updated successfully.', 'success')
        return redirect(url_for('products'))
    return render_template('edit_product.html', product=product)

@app.route('/delete_product/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully.', 'success')
    return redirect(url_for('products'))

@app.route('/invoices')
@login_required
def invoices():
    invoices = Invoice.query.order_by(Invoice.date.desc()).all()
    customers = {c.id: c for c in Customer.query.all()}
    return render_template('invoices.html', invoices=invoices, customers=customers)

@app.route('/delete_invoice/<int:id>', methods=['POST'])
@login_required
@admin_required
def delete_invoice(id):
    invoice = Invoice.query.get_or_404(id)
    db.session.delete(invoice)
    db.session.commit()
    flash('Invoice deleted successfully.', 'success')
    return redirect(url_for('invoices'))

@app.route('/payments')
@login_required
def payments():
    payments = Transaction.query.filter_by(type='payment').order_by(Transaction.date.desc()).all()
    customers = {c.id: c for c in Customer.query.all()}
    return render_template('payments.html', payments=payments, customers=customers)

@app.route('/add_payment', methods=['GET', 'POST'])
@login_required
def add_payment():
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        amount = float(request.form.get('amount', 0))
        payment_mode = request.form.get('payment_mode')
        notes = request.form.get('notes')
        date = request.form.get('date')
        payment = Transaction(
            customer_id=customer_id,
            type='payment',
            amount=amount,
            description=notes or '',
            date=date,
            payment_mode=payment_mode
        )
        db.session.add(payment)
        db.session.commit()
        flash('Payment recorded successfully.', 'success')
        return redirect(url_for('payments'))
    customers = Customer.query.all()
    return render_template('add_payment.html', customers=customers)

@app.route('/credit_report')
@login_required
@admin_required
def credit_report():
    customers = Customer.query.order_by(Customer.outstanding_balance.desc()).all()
    return render_template('credit_report.html', customers=customers)

if __name__ == '__main__':
   # init_db()  # Only run this manually if you want to reset the database!
    socketio.run(app, debug=True) 
