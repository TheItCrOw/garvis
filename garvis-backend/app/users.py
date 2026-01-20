import uuid
from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, models
from fastapi_users.authentication import (AuthenticationBackend, BearerTransport, JWTStrategy)
from fastapi_users.db import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase

#<folder>/<folder>/<filename> import <class>,<context-specific helper function>
from app.database.sqlite_data_service import User, get_user_db

PUBLIC_SECRET = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDVLjRRZ5HuE6hKMtY6b5V1tqTSMkpxWor7XAG4gtf6R6Q4h/ReJurXLlRIlU59LeJ3RckQJN9PvcybEofsktdQCF3K+F1gxPsM1LR5ZS+/6zXRcgS44RRqP9FfEtzIsfzjlWPMfXC88fHxI0Nc5L0uw2b7gXdE8lj80/EmCiQFpwIDAQAB"
PRIVATE_SECRET = "MIICXQIBAAKBgQDVLjRRZ5HuE6hKMtY6b5V1tqTSMkpxWor7XAG4gtf6R6Q4h/ReJurXLlRIlU59LeJ3RckQJN9PvcybEofsktdQCF3K+F1gxPsM1LR5ZS+/6zXRcgS44RRqP9FfEtzIsfzjlWPMfXC88fHxI0Nc5L0uw2b7gXdE8lj80/EmCiQFpwIDAQABAoGAZDkLubXCgrZVKUULOH/bOXM7u+KO4wnZS2EvIerJ1U23JCiut1D+mVmboGApfWqEDOUPKPrczeWCeulUY+GJPae8sr5KcdsDdgQ8vh1RlEBCaaHTiRB8euqNHJhL8qMZZcYcC97vcsjfyIUy2qzxr6nJ2D4AgsA9LkoPbvqwDIECQQD9gBN7yai0VTskpazpNwnUk5mEaL6oWnX+eQK83bKVOheQIhXh6bMbjl+LwK/FBRpFX0CZYKOfihWtAvpbtonnAkEA10hYzO/6UsHxoQNBSaouSsHPIvdskweDP4I6JGOMNCyzcor0cPFRTm/aokrEluNWqLU3R/b7+2SJ4nojlnCuQQJBAKDrJnMUBhXDbPHMgcDhgUoCEBevbifslK5fHs/JY826vK5wFLf95AaAEELkpC9LF+wllRpH8FYcD7puA4Moks0CQQCFI+4fWG70zZM1JAE1oLUecLw9AM46JBRMq6pvpM0p21djiIJicyv4mX6ajikEtDZ9Ag3dSOdP8z6/PRBTUv7BAkB9f+5VU0cU+zWMqqYsixDZAEmScniya8K24CvR68tP88BEzzapgYDQE3gRbuAdTGldJsDdH1Qy48BhJuxZF4/q"

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = PRIVATE_SECRET
    verification_token_secret = PRIVATE_SECRET

    async def on_after_register(self, user: User, request:Optional[Request]=None):
        print(f"User {user.id} has registered")

    async def on_after_reset_password(self, user, request = None):
        #return await super().on_after_reset_password(user, request)
        print(f"User {user.id} has reset password")
    
    async def on_after_request_verify(self, user, token, request = None):
        #return await super().on_after_request_verify(user, token, request)
        print(f"User {user.id} has verified account")

async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

def get_jwt_strategy():
    return JWTStrategy(secret=PRIVATE_SECRET, lifetime_seconds=3600)

auth_backend = AuthenticationBackend(name="jwt"
                                     , transport=bearer_transport
                                     , get_strategy=get_jwt_strategy
                                     )

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, auth_backends=[auth_backend])
current_active_user = fastapi_users.current_user(active=True)