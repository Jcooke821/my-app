from flask import Flask
from flask_socketio import SocketIO

socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'

    # Register HTTP routes
    from .routes import register_routes
    register_routes(app)

    # Initialize SocketIO
    socketio.init_app(app)

    return app
