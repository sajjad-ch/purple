from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from jwt import decode as jwt_decode, exceptions as jwt_exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from channels.middleware import BaseMiddleware


@database_sync_to_async
def get_user_from_jwt(token):
    """
    Decode the JWT token and return the authenticated user.
    """
    try:
        # Decode the token
        validated_token = JWTAuthentication().get_validated_token(token)
        # Get the user from the token
        user = JWTAuthentication().get_user(validated_token)
        return user
    except jwt_exceptions.InvalidTokenError:
        return AnonymousUser()
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware to authenticate WebSocket connections using JWT.
    """

    async def __call__(self, scope, receive, send):
        headers = dict(scope['headers'])
        if b'authorization' in headers:
            try:
                # Extract the token from the "Authorization" header
                token_name, token_key = headers[b'authorization'].decode().split()
                if token_name.lower() == "bearer":  # Ensure the header uses "Bearer" scheme
                    scope['user'] = await get_user_from_jwt(token_key)
                else:
                    scope['user'] = AnonymousUser()
            except ValueError:
                scope['user'] = AnonymousUser()  # Handle improperly formatted headers
        else:
            scope['user'] = AnonymousUser()  # No auth header found

        return await super().__call__(scope, receive, send)
