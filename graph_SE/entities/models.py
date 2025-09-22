'''
Ok so this is the model/structure for the entity. An Entity is the aggregated and summarised information created from a web-search.
Entity is going to be the core-unit of the project, representing all aggregated data from a web-search as a single 
summarised information capsule.
'''

from django.db import models

# Create your models here.
class Entity(models.Model):
    title = models.CharField(max_length=255)
    summary = models.TextField() # A summary of all relevant articles retrieved through a search.
    image_url = models.URLField(null=True, blank=True) # Image most relevant to the search to visually represent the entity.
    sources = models.JSONField(default=list) # Store references, articles, sites and pages (search sources).
    created_at = models.DateTimeField(auto_now_add=True) # I might order entities chronologically in the search-history section

    def __str__(self):
        return self.title

'''
Notes: 
python3 manage.py makemigrations
python3 manage.py migrate
once done with the models.
'''
