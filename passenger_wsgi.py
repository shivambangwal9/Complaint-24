import sys
import os

# Add your app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

# Import your Flask app
from app import app as application
