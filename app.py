from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash # Keep for init_db and User model methods if any
from datetime import datetime, timedelta
from functools import wraps
import os
from sqlalchemy import func # Keep for models or specific queries remaining in app.py
from config import config
from flask_socketio import SocketIO, emit
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config.from_object(config['development'])
csrf = CSRFProtect(app) # Initialize CSRF protection

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
        self.password = password # Store hashed password if hashing is done before this model
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
        # Ensure calculations handle None or empty values gracefully
        total_invoices = sum(inv.total_amount for inv in self.invoices if inv.total_amount)
        total_credits = sum(tx.amount for tx in self.transactions if tx.type == 'credit' and tx.amount)
        total_payments = sum(tx.amount for tx in self.transactions if tx.type == 'payment' and tx.amount)
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
            'outstanding_balance': self.outstanding_balance, # This will call the property
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

# Authentication middleware (login_required remains here as it's broadly used)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            # Adjusted to redirect to auth.login as login route is now in auth_bp
            return redirect(url_for('auth.login')) 
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# admin_required has been moved to blueprints/auth.py

# Import Blueprints
from blueprints.main import main_bp
from blueprints.auth import auth_bp
from blueprints.customers import customers_bp
from blueprints.products import products_bp
from blueprints.invoices import invoices_bp
from blueprints.transactions import transactions_bp
from blueprints.reports import reports_bp

# Register Blueprints
app.register_blueprint(main_bp)
app.register_blueprint(auth_bp) # No prefix for login/logout, settings might be /settings
app.register_blueprint(customers_bp, url_prefix='/customers')
app.register_blueprint(products_bp, url_prefix='/products')
app.register_blueprint(invoices_bp, url_prefix='/invoices')
app.register_blueprint(transactions_bp, url_prefix='/transactions') # e.g. /transactions/add, /transactions/payments
app.register_blueprint(reports_bp, url_prefix='/reports')

# Custom Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    db.session.rollback() # Ensure the session is clean
    return render_template('errors/500.html'), 500

# Socket.IO event handlers (remain in app.py)
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

# get_next_invoice_number has been moved to blueprints/invoices.py

# Initialize database and create default users (remains in app.py)
def init_db():
    with app.app_context():
        os.makedirs(db_dir, exist_ok=True) # Ensure db_dir exists
        # db.drop_all() # This line is removed to prevent data loss
        db.create_all() # Creates tables if they don't exist

        admin_username = app.config['ADMIN_USERNAME']
        admin_password = app.config['ADMIN_PASSWORD']
        staff_username = app.config['STAFF_USERNAME']
        staff_password = app.config['STAFF_PASSWORD']

        if admin_username and admin_password:
            if not User.query.filter_by(username=admin_username).first():
                admin = User(
                    username=admin_username,
                    password=generate_password_hash(admin_password), # Hashing here
                    role='admin'
                )
                db.session.add(admin)
                print(f"Admin user '{admin_username}' created.")
            else:
                print(f"Admin user '{admin_username}' already exists.")
        else:
            print("ADMIN_USERNAME or ADMIN_PASSWORD not set in environment variables. Admin user not created.")

        if staff_username and staff_password:
            if not User.query.filter_by(username=staff_username).first():
                staff = User(
                    username=staff_username,
                    password=generate_password_hash(staff_password), # Hashing here
                    role='staff'
                )
                db.session.add(staff)
                print(f"Staff user '{staff_username}' created.")
            else:
                print(f"Staff user '{staff_username}' already exists.")
        else:
            print("STAFF_USERNAME or STAFF_PASSWORD not set in environment variables. Staff user not created.")
            
        db.session.commit()

if __name__ == '__main__':
   # init_db()  # Uncomment and run once manually if you need to reset/initialize the database
    socketio.run(app, debug=True)
