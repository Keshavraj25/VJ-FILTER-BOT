import os
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Handle missing packages gracefully
try:
    from flask import Flask, render_template, jsonify, request, flash, redirect, url_for, session
    from flask_sqlalchemy import SQLAlchemy
except ImportError:
    logger.error("Flask or SQLAlchemy is not installed. Please install them with 'pip install flask flask-sqlalchemy'")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv is not installed. Using environment variables directly.")

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure the PostgreSQL database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_recycle': 280}

# Initialize the database
db = SQLAlchemy(app)

# Define models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(100))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    is_banned = db.Column(db.Boolean, default=False)
    joined_date = db.Column(db.DateTime, default=datetime.utcnow)
    ban_reason = db.Column(db.String(255))

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(255))
    is_banned = db.Column(db.Boolean, default=False)
    joined_date = db.Column(db.DateTime, default=datetime.utcnow)
    ban_reason = db.Column(db.String(255))

class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String(255), unique=True, nullable=False)
    file_name = db.Column(db.String(255))
    file_size = db.Column(db.BigInteger)
    file_type = db.Column(db.String(50))
    caption = db.Column(db.Text)
    added_date = db.Column(db.DateTime, default=datetime.utcnow)
    
# Create the database tables
try:
    with app.app_context():
        db.create_all()
        logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Error creating database tables: {e}")
    logger.info("The application will continue but database functionality may be limited")

# Import configuration with graceful fallbacks
try:
    from info import API_ID, API_HASH, BOT_TOKEN, DATABASE_URI
except ImportError:
    logger.warning("Could not import from info.py. Using environment variables directly.")
    API_ID = os.environ.get('API_ID')
    API_HASH = os.environ.get('API_HASH')
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    DATABASE_URI = os.environ.get('DATABASE_URI')

@app.route('/')
def index():
    """Main index route - shows the status page"""
    return render_template('index.html')

@app.route('/api/status')
def status():
    """API endpoint for checking bot status"""
    # Check if required configurations are available
    configs = {
        "API_ID": bool(API_ID),
        "API_HASH": bool(API_HASH) and len(API_HASH) > 0,
        "BOT_TOKEN": bool(BOT_TOKEN) and len(BOT_TOKEN) > 0,
        "DATABASE_URI": bool(DATABASE_URI) and len(DATABASE_URI) > 0
    }
    
    missing_configs = [key for key, value in configs.items() if not value]
    
    # Check database status
    db_status = "connected"
    try:
        # Simple database query to check connection
        db.session.execute(db.select(User).limit(1))
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        db_status = f"error: {str(e)}"
    
    # Get basic stats
    stats = {
        "users_count": 0,
        "chats_count": 0,
        "files_count": 0
    }
    
    try:
        stats["users_count"] = db.session.query(User).count()
        stats["chats_count"] = db.session.query(Chat).count()
        stats["files_count"] = db.session.query(File).count()
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
    
    return jsonify({
        "status": "running",
        "server_type": "Flask",
        "missing_configurations": missing_configs,
        "bot_operational": len(missing_configs) == 0,
        "database_status": db_status,
        "stats": stats
    })

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})

@app.route('/api/telegram/webhook', methods=['POST'])
def telegram_webhook():
    """Endpoint for Telegram webhook (future implementation)"""
    return jsonify({"status": "not_implemented"})

@app.route('/dashboard')
def dashboard():
    """Admin dashboard"""
    try:
        users = User.query.all()
        chats = Chat.query.all()
        files = File.query.limit(100).all()
        user_count = len(users)
        chat_count = len(chats)
        file_count = File.query.count()
    except Exception as e:
        logger.error(f"Error fetching data for dashboard: {e}")
        users = []
        chats = []
        files = []
        user_count = 0
        chat_count = 0
        file_count = 0
        flash("Database connection error. Some features may be unavailable.", "danger")
    
    return render_template('dashboard.html', 
                           users=users, 
                           chats=chats, 
                           files=files,
                           user_count=user_count,
                           chat_count=chat_count,
                           file_count=file_count,
                           db_error=True if len(users) == 0 and len(chats) == 0 and len(files) == 0 else False)

@app.route('/api/get-started')
def get_started():
    """Information about getting started with the bot"""
    return jsonify({
        "status": "success",
        "instructions": [
            "Get API_ID and API_HASH from https://my.telegram.org",
            "Create a bot with @BotFather to get BOT_TOKEN",
            "Set up MongoDB and get DATABASE_URI",
            "Set these as environment variables in your Replit settings"
        ],
        "help_link": "https://github.com/VJBots/VJ-FILTER-BOT"
    })

if __name__ == "__main__":
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Create the static directory if it doesn't exist
    os.makedirs('static', exist_ok=True)
    
    logger.info("Starting Flask web server on port 5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
