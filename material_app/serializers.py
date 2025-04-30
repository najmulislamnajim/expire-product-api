from rest_framework import serializers 
from material_app.models import RplMaterial

class RplMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = RplMaterial
        fields = '__all__'