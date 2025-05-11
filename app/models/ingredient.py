"""Additive information model for the MeatWise API.

This file previously contained ingredient models that were connected to the 
ingredients table in the database. That table has been removed, and now this
file only contains the AdditiveInfo model which is used for structured responses.

The AdditiveInfo model is now imported from app.api.v1.models to ensure
consistency across the application and avoid validation errors.
"""

# Import the AdditiveInfo model from the central models file
from app.api.v1.models import AdditiveInfo

# Re-export the model
__all__ = ['AdditiveInfo'] 