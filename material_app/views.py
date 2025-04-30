from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from material_app.models import RplMaterial
from material_app.serializers import RplMaterialSerializer

# Create your views here.
class RplMaterialListView(APIView):
    def get(self, request):
        materials = RplMaterial.objects.all()
        serializer = RplMaterialSerializer(materials, many=True)
        return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)