from rest_framework import serializers
from .models import Listing

class ListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing 
        fields = '__all__'  # includes all fields from the Listing model
