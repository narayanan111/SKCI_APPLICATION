from app import app
from config import config

# Load production configuration
app.config.from_object(config['production'])

if __name__ == '__main__':
    app.run() 