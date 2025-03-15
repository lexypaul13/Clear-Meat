from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import credentials, auth
import os

# Firebase Authentication setup
# Note: In production, use environment variables for the service account path
# cred = credentials.Certificate(os.environ.get("FIREBASE_CREDENTIALS_PATH"))
# firebase_admin.initialize_app(cred)

# For development, we'll comment out the Firebase initialization
# Uncomment and configure with your Firebase credentials when ready
security = HTTPBearer()

# Authentication dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {e}"
        ) 