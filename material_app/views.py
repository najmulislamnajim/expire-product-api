import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from material_app.models import RplMaterial
from material_app.serializers import RplMaterialSerializer

# Set logger
logger = logging.getLogger("material_app")

# Create your views here.
class RplMaterialListView(APIView):
    """
    View to list all materials.
    
    Methods:
        get(request): List all materials.
    """
    def get(self, request):
        """
        List all materials.
        
        Returns:
            Response: A response object containing the list of materials.
        """
        try:
            materials = RplMaterial.objects.all()
            serializer = RplMaterialSerializer(materials, many=True)
            logger.info("Material list fetched successfully")
            return Response({"success": True, "data": serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error fetching materials: {str(e)}", exc_info=True)
            return Response({"success": False, "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)