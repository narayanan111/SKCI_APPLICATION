import unittest
from app import app, db, User, Customer, Transaction
from config import config
import os

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'

class TestApp(unittest.TestCase):
    def setUp(self):
        app.config.from_object(TestConfig)
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test user
        test_user = User(
            username='testuser',
            password='testpass',
            role='staff'
        )
        db.session.add(test_user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_login_page(self):
        response = self.app.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Customer Management System', response.data)

    def test_login_success(self):
        response = self.app.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Dashboard', response.data)

    def test_login_failure(self):
        response = self.app.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpass'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid username or password', response.data)

    def test_customer_creation(self):
        # Login first
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        })

        # Create a customer
        response = self.app.post('/customers/add', data={
            'name': 'Test Customer',
            'email': 'test@example.com',
            'phone': '1234567890',
            'credit_limit': 1000,
            'address': 'Test Address'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        customer = Customer.query.filter_by(name='Test Customer').first()
        self.assertIsNotNone(customer)
        self.assertEqual(customer.email, 'test@example.com')

    def test_transaction_creation(self):
        # Login first
        self.app.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        })

        # Create a customer
        customer = Customer(
            name='Test Customer',
            email='test@example.com',
            phone='1234567890',
            credit_limit=1000,
            address='Test Address'
        )
        db.session.add(customer)
        db.session.commit()

        # Create a transaction
        response = self.app.post('/transactions/add', data={
            'customer_id': customer.id,
            'type': 'credit',
            'amount': 500,
            'description': 'Test transaction'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        transaction = Transaction.query.filter_by(customer_id=customer.id).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, 500)

if __name__ == '__main__':
    unittest.main() 