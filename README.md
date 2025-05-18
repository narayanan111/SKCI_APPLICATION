# Customer Management System

A comprehensive customer management system built with Flask, featuring customer management, credit management, payment processing, and reporting capabilities.

## Features

- Customer Management
  - Add, edit, and view customer details
  - Track customer credit limits and balances
  - View customer transaction history

- Credit Management
  - Set and manage credit limits
  - Track credit utilization
  - Monitor payment history

- Payment Processing
  - Record payments and credits
  - Generate payment receipts
  - Track payment status

- Reporting
  - Generate transaction reports
  - View payment statistics
  - Export data to various formats

- Role-based Access Control
  - Admin and Staff roles
  - Different permissions for each role
  - Secure authentication

- Responsive UI
  - Modern and clean interface
  - Mobile-friendly design
  - Interactive data tables

## Login Credentials

- Admin User:
  - Username: Krishna
  - Password: Krishna@123

- Staff User:
  - Username: Raja
  - Password: Raja@123

## Development Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd customer-management-system
   ```

2. Run the setup script:
   ```bash
   python setup_dev.py
   ```
   This will:
   - Create a virtual environment
   - Install dependencies
   - Create necessary directories
   - Create a .env file

3. Activate the virtual environment:
   ```bash
   # Windows
   venv\Scripts\activate

   # Linux/Mac
   source venv/bin/activate
   ```

4. Run the application:
   ```bash
   python app.py
   ```

5. Access the application:
   Open your web browser and navigate to `http://localhost:5000`

## Testing

Run the test suite with coverage reporting:
```bash
python run_tests.py
```

This will:
- Run all tests
- Generate a coverage report
- Create an HTML coverage report in the `coverage_html` directory

## Production Deployment

1. Set up a production environment:
   ```bash
   # Create a production .env file
   cp .env.example .env
   # Edit .env with production values
   ```

2. Install production dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run with Gunicorn:
   ```bash
   gunicorn -c gunicorn_config.py wsgi:app
   ```

4. For systemd service (Linux):
   Create `/etc/systemd/system/cms.service`:
   ```ini
   [Unit]
   Description=Customer Management System
   After=network.target

   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/path/to/cms
   Environment="PATH=/path/to/cms/venv/bin"
   ExecStart=/path/to/cms/venv/bin/gunicorn -c gunicorn_config.py wsgi:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Then:
   ```bash
   sudo systemctl enable cms
   sudo systemctl start cms
   ```

5. For Nginx configuration:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## Technologies Used

### Backend
- Flask - Web framework
- SQLAlchemy - ORM
- SQLite - Database
- Gunicorn - WSGI server

### Frontend
- HTML5
- CSS3
- JavaScript
- Bootstrap 5
- Font Awesome
- DataTables
- jQuery

## Project Structure

```
customer-management-system/
├── app.py              # Main application file
├── config.py           # Configuration settings
├── wsgi.py            # WSGI entry point
├── gunicorn_config.py # Gunicorn configuration
├── setup_dev.py       # Development setup script
├── run_tests.py       # Test runner
├── requirements.txt    # Python dependencies
├── .env               # Environment variables
├── .gitignore         # Git ignore file
├── database/          # Database directory
├── logs/             # Log files directory
├── static/           # Static files
│   ├── css/         # CSS files
│   ├── js/          # JavaScript files
│   └── uploads/     # Uploaded files
├── templates/        # HTML templates
│   ├── base.html    # Base template
│   ├── login.html   # Login page
│   ├── dashboard.html  # Dashboard
│   └── ...          # Other templates
└── tests/           # Test files
    └── test_app.py  # Application tests
```

## Security Features

- Password hashing using Werkzeug
- Session-based authentication
- Role-based access control
- SQL injection prevention
- XSS protection
- CSRF protection
- Secure password storage
- Environment variable configuration
- Production-ready WSGI server
- SSL/TLS support

## Development

### Running Tests
```bash
python run_tests.py
```

### Code Style
The project follows PEP 8 style guidelines. Use a linter to check your code:
```bash
flake8 .
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

# Customer Management System

A comprehensive customer management system built with Flask, featuring customer management, credit management, payment processing, and reporting capabilities.

## Features

- Customer Management
  - Add, edit, and view customer details
  - Track customer credit limits and balances
  - View customer transaction history

- Credit Management
  - Set and manage credit limits
  - Track credit utilization
  - Monitor payment history

- Payment Processing
  - Record payments and credits
  - Generate payment receipts
  - Track payment status

- Reporting
  - Generate transaction reports
  - View payment statistics
  - Export data to various formats

- Role-based Access Control
  - Admin and Staff roles
  - Different permissions for each role
  - Secure authentication

- Responsive UI
  - Modern and clean interface
  - Mobile-friendly design
  - Interactive data tables

## Login Credentials

- Admin User:
  - Username: Krishna
  - Password: Krishna@123

- Staff User:
  - Username: Raja
  - Password: Raja@123

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd customer-management-system
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the project root with the following variables:
   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-here
   PASSWORD_SALT=your-password-salt-here
   DATABASE_URL=sqlite:///database/cms.db
   ```
   Replace `your-secret-key-here` and `your-password-salt-here` with secure random strings.

5. Initialize the database:
   ```bash
   python app.py
   ```
   This will create the database and add default users.

6. Run the application:
   ```bash
   python app.py
   ```

7. Access the application:
   Open your web browser and navigate to `http://localhost:5000`

## Technologies Used

### Backend
- Flask - Web framework
- SQLAlchemy - ORM
- SQLite - Database

### Frontend
- HTML5
- CSS3
- JavaScript
- Bootstrap 5
- Font Awesome
- DataTables
- jQuery

## Project Structure

```
customer-management-system/
├── app.py              # Main application file
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (create from .env.example)
├── .gitignore         # Git ignore file
├── database/          # Database directory
├── logs/             # Log files directory
├── static/           # Static files
│   ├── css/         # CSS files
│   ├── js/          # JavaScript files
│   └── uploads/     # Uploaded files
└── templates/        # HTML templates
    ├── base.html    # Base template
    ├── login.html   # Login page
    ├── dashboard.html  # Dashboard
    └── ...          # Other templates
```

## Security Features

- Password hashing using Werkzeug
- Session-based authentication
- Role-based access control
- SQL injection prevention
- XSS protection
- CSRF protection
- Secure password storage
- Environment variable configuration

## Development

### Running Tests
```bash
python -m pytest
```

### Code Style
The project follows PEP 8 style guidelines. Use a linter to check your code:
```bash
flake8 .
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 