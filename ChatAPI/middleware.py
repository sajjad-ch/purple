from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from jwt import decode as jwt_decode, exceptions as jwt_exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import AccessToken
from urllib.parse import parse_qs

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
    

# class JWTAuthMiddleware(BaseMiddleware):
    
#     async def __call__(self, scope, receive, send):
    
#         token = self.get_token_from_scope(scope)
        
#         if token != None:
#             user_id = await self.get_user_from_token(token) 
#             if user_id:
#                 scope['user_id'] = user_id

#             else:
#                 scope['error'] = 'Invalid token'

#         if token == None:
#             scope['error'] = 'provide an auth token'    
    
                
#         return await super().__call__(scope, receive, send)

#     def get_token_from_scope(self, scope):
#         headers = dict(scope.get("headers", []))
        
#         auth_header = headers.get(b'authorization', b'').decode('utf-8')
        
#         if auth_header.startswith('Bearer '):
#             return auth_header.split(' ')[1]
        
#         else:
#             return None
        
#     @database_sync_to_async
#     def get_user_from_token(self, token):
#             try:
#                 access_token = AccessToken(token)
#                 return access_token['user_id']
#             except:
#                 return None


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        token = self.get_token_from_scope(scope)

        if token is not None:
            user_id = await self.get_user_from_token(token)
            if user_id:
                scope['user_id'] = user_id
            else:
                scope['error'] = 'Invalid token'
        else:
            scope['error'] = 'Provide an auth token'

        return await super().__call__(scope, receive, send)

    def get_token_from_scope(self, scope):
        # Check query string first (for PWA case)
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)

        if 'token' in query_params:
            return query_params['token'][0]

        # Fallback to Authorization header (for non-PWA clients)
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b'authorization', b'').decode('utf-8')
        if auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]

        return None

    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            access_token = AccessToken(token)
            return access_token['user_id']
        except Exception:
            return None