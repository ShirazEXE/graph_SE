'''
Ok so we are using the serializers from Django Rest Framework(DRF) which converts Django models (which are Python Object) 
into JSON and vice-versa to establish proper communication between frontend(reads JSON) and backend(Python Objects). 
'''

from rest_framework import serializers
from .models import Entity

class EntitySerializer(serializers.ModelSerializer):
    class Meta: # Defines Metadata for serializer
        model = Entity  # Selects which model to be serialised.
        fields = '__all__' # includes all fields in the Entity Model
    