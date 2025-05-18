import os
import subprocess
import sys
from pathlib import Path

def create_virtual_environment():
    print("Creating virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", "venv"])

def install_requirements():
    print("Installing requirements...")
    if os.name == 'nt':  # Windows
        subprocess.run(["venv\\Scripts\\pip", "install", "-r", "requirements.txt"])
    else:  # Linux/Mac
        subprocess.run(["venv/bin/pip", "install", "-r", "requirements.txt"])

def create_directories():
    print("Creating necessary directories...")
    directories = [
        'database',
        'logs',
        'static/uploads',
        'coverage_html'
    ]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def create_env_file():
    print("Creating .env file...")
    env_content = """FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=dev-secret-key-here
PASSWORD_SALT=dev-password-salt-here
DATABASE_URL=sqlite:///database/cms.db
"""
    with open('.env', 'w') as f:
        f.write(env_content)

def main():
    print("Setting up development environment...")
    
    # Create virtual environment
    create_virtual_environment()
    
    # Install requirements
    install_requirements()
    
    # Create necessary directories
    create_directories()
    
    # Create .env file
    create_env_file()
    
    print("\nDevelopment environment setup complete!")
    print("\nTo activate the virtual environment:")
    if os.name == 'nt':  # Windows
        print("venv\\Scripts\\activate")
    else:  # Linux/Mac
        print("source venv/bin/activate")
    
    print("\nTo run the application:")
    print("python app.py")
    
    print("\nTo run tests:")
    print("python run_tests.py")

if __name__ == '__main__':
    main() 