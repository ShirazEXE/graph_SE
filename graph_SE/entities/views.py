'''
Views are functions which take HTTP Requests and based on the requests provides HTTP Responses (like HTML page, JSON object, etc).
ViewSets are special DRF views that handles all CRUD actions for a model.
'''

from django.shortcuts import render
from rest_framework import viewsets
from .models import Entity
from .serializers import EntitySerializer

# Create your views here.
class EntityViewSet(viewsets.ModelViewSet): # This class handles all HTTP Requests related to Entity
    queryset = Entity.objects.all() # Retrieves all Entity Objects from database
    serializer_class = EntitySerializer # Transform Entity Objects into JSON and vice versa
