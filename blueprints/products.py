# blueprints/products.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from sqlalchemy.exc import SQLAlchemyError

# Imports from main app (db, models) and other blueprints (admin_required)
# These will be imported within functions to avoid circular dependencies at load time
# and to ensure app context is available.

products_bp = Blueprint('products', __name__, url_prefix='/products')

@products_bp.route('/')
def list_products(): # Renamed from 'products' to avoid conflict with blueprint name
    from app import db, Product, login_required
    from .auth import admin_required
    @login_required
    @admin_required
    def actual_list_products():
        products_data = Product.query.all()
        return render_template('products.html', products=products_data)
    return actual_list_products()

@products_bp.route('/add', methods=['GET', 'POST']) # Changed from /add_product
def add_product():
    from app import db, Product, login_required
    from .auth import admin_required
    @login_required
    @admin_required
    def actual_add_product():
        if request.method == 'POST':
            name = request.form.get('name')
            hsn = request.form.get('hsn')
            gst_percent = float(request.form.get('gst_percent', 0))
            price = float(request.form.get('price', 0))
            product = Product(name=name, hsn=hsn, gst_percent=gst_percent, price=price)
            try:
                db.session.add(product)
                db.session.commit()
                flash('Product added successfully.', 'success')
            except SQLAlchemyError as e:
                db.session.rollback()
                current_app.logger.error(f"Database error in {request.endpoint} for product {name}: {str(e)}")
                flash('Error: Could not add product due to a database issue. Please try again.', 'danger')
            return redirect(url_for('products.list_products'))
        return render_template('add_product.html')
    return actual_add_product()

@products_bp.route('/edit/<int:id>', methods=['GET', 'POST']) 
def edit_product(id):
    from app import db, Product, login_required
    from .auth import admin_required
    @login_required
    @admin_required
    def actual_edit_product(product_id): # Pass id as product_id
        product = Product.query.get_or_404(product_id)
        original_name = product.name # For logging
        if request.method == 'POST':
            try:
                product.name = request.form.get('name')
                product.hsn = request.form.get('hsn')
                product.gst_percent = float(request.form.get('gst_percent', 0))
                product.price = float(request.form.get('price', 0))
                db.session.commit()
                flash('Product updated successfully.', 'success')
            except SQLAlchemyError as e:
                db.session.rollback()
                current_app.logger.error(f"Database error in {request.endpoint} for product {original_name} (ID: {product_id}): {str(e)}")
                flash('Error: Could not update product due to a database issue. Please try again.', 'danger')
            return redirect(url_for('products.list_products'))
        return render_template('edit_product.html', product=product)
    return actual_edit_product(id) # Pass id to inner function

@products_bp.route('/delete/<int:id>', methods=['POST']) 
def delete_product(id):
    from app import db, Product, login_required
    from .auth import admin_required
    @login_required
    @admin_required
    def actual_delete_product(product_id): # Pass id as product_id
        product = Product.query.get_or_404(product_id)
        product_name_to_delete = product.name # For logging
        try:
            db.session.delete(product)
            db.session.commit()
            flash('Product deleted successfully.', 'success')
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error in {request.endpoint} attempting to delete product {product_name_to_delete} (ID: {product_id}): {str(e)}")
            flash('Error: Could not delete product due to a database issue. Please try again.', 'danger')
        return redirect(url_for('products.list_products'))
    return actual_delete_product(id) # Pass id to inner function
