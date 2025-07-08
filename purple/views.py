import os
from django.http import FileResponse, Http404
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView


def get_permission(path: str):
    if path.startswith("Images/") or path.startswith("Images\\"):
        return AllowAny
    return IsAuthenticated


class ProtectMediaView(APIView):
    def get(self, request: Request, path: str):
        permission_type = get_permission(path)

        for perm in permission_type(),:
            if not perm.has_permission(request, None):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied()
        
        file_path = os.path.join(settings.MEDIA_ROOT, path)
        if os.path.exists(file_path):
            return FileResponse(open(file_path, 'rb'))
        return Http404("File Not Found")
    
        