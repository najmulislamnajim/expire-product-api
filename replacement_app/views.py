from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from withdrawal_app.models import WithdrawalInfo
from .serializers import AvailableReplacementListSerializer
from withdrawal_app.utils import paginate

# Create your views here.
class AvailableReplacementListView(APIView):
    def get(self, request):
        mio_id = request.query_params.get('mio_id')
        if not mio_id:
            return Response({"success":False,"message": "Please provide MIO ID."}, status=status.HTTP_400_BAD_REQUEST)
        
        withdrawal_info = (
            WithdrawalInfo.objects
            .filter(last_status='withdrawal_approved', mio_id=mio_id)
            .annotate(total_amount=Sum('withdrawal_list__net_val'))
            .order_by('-withdrawal_date')
        )
        if withdrawal_info.exists():
            serializer = AvailableReplacementListSerializer(withdrawal_info, many=True)
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 10))
            if page <= 0 or per_page <= 0:
                return Response({"success":False,"message": "Invalid page or per_page parameters."}, status=status.HTTP_400_BAD_REQUEST)
            results = paginate(serializer.data, page=page, per_page=per_page)
            return Response(results, status=status.HTTP_200_OK)
        else:
            return Response(paginate([], message="No available replacements found."), status=status.HTTP_404_NOT_FOUND)
