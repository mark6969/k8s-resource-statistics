from django.db import models


class Document(models.Model):
    imac_team = models.CharField(max_length=200)
    uploadedFile = models.FileField(upload_to="")
    cpu_size = models.FloatField()
    memory_size = models.FloatField()
    dateTimeOfUpload = models.DateTimeField(auto_now=True)
    name_type = models.CharField(max_length=200, primary_key=True)


class Capacity(models.Model):
    team = models.CharField(max_length=200, primary_key=True)
    cpu_size = models.FloatField()
    memory_size = models.FloatField()
