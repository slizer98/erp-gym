from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class PingView(APIView):
    permission_classes = [IsAuthenticated]  # este sí requiere JWT
    def get(self, request):
        return Response({"message": "pong", "user": request.user.username})
