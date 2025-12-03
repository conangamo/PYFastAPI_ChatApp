"""
SQLAlchemy Base model
Separated from database.py to avoid engine creation during imports
"""
from sqlalchemy.orm import declarative_base

# Create declarative base for all models
Base = declarative_base()

