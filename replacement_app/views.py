from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from withdrawal_app.models import WithdrawalInfo
from .serializers import AvailableReplacementListSerializer, ReplacementListSerializer
from withdrawal_app.utils import paginate
from .models import ReplacementList
from datetime import date

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

class ReplacementListCreateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        invoice_no = request.data.get('invoice_no')
        materials = request.data.get('materials', [])

        if not invoice_no or not materials:
            return Response(
                {"success":False,"message": "Both 'invoice' and 'materials' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            invoice = WithdrawalInfo.objects.get(invoice_no=invoice_no)
        except WithdrawalInfo.DoesNotExist:
            return Response(
                {"success":False,"message": "Invoice not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ReplacementListSerializer(data=materials, many=True)
        if serializer.is_valid():
            replacement_objects = [
                ReplacementList(invoice=invoice, **item)
                for item in serializer.validated_data
            ]
            ReplacementList.objects.bulk_create(replacement_objects)
            invoice.last_status=invoice.Status.REPLACEMENT_APPROVAL
            invoice.replacement_order=True
            invoice.save()

            return Response(
                {"success":True,"message": "Replacement list created successfully","data":serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response({"success":False,"message":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
class ReplacementApproveView(APIView):
    def put(self, request):
        invoice_no = request.data.get("invoice_no")
        try:
            withdrawal_info = WithdrawalInfo.objects.get(invoice_no= invoice_no)
            withdrawal_info.order_approval = True
            withdrawal_info.last_status = withdrawal_info.Status.REPLACEMENT_APPROVED
            withdrawal_info.order_approval_date = date.today()
            withdrawal_info.save()
            return Response({"success":True, "message":"Successfully approved", "data":invoice_no}, status=status.HTTP_200_OK)
        except WithdrawalInfo.DoesNotExist:
            return Response({"success":False, "message":"invoice not found!"}, status=status.HTTP_404_NOT_FOUND)
