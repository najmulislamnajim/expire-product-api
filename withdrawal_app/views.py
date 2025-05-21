import logging
from datetime import date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404
from django.db import connection
from withdrawal_app.serializers import WithdrawalRequestSerializer, WithdrawalSerializer, WithdrawalListSerializer, DaAssignSerializer
from withdrawal_app.models import WithdrawalInfo
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiTypes

# Set logger
logger = logging.getLogger("withdrawal_app")
# Create your views here.
class WithdrawalRequestView(APIView):
    """
    View to create a new withdrawal request.
    
    Args:
        request (Request): The HTTP request object.
    
    Returns:
        Response: A response object containing the created withdrawal request data.
    """
    @extend_schema(request=WithdrawalRequestSerializer) # for drf-spectacular documentation
    def post(self, request):
        """
        Create a new withdrawal request.
        
        Args:
            request (Request): The HTTP request object.
        
        Returns:
            Response: A response object containing the created withdrawal request data.
        """ 
        # Make a copy of the request data to avoid modifying the original data
        data = request.data.copy()
        
        # Get Depot Code and Route Id
        sql_query = """
        SELECT depot_code, route_code
        FROM rpl_customer AS c 
        INNER JOIN rdl_route_wise_depot AS rd ON c.trans_p_zone=CONCAT('0000',rd.route_code)
        WHERE c.partner=%s;
        """
        with connection.cursor() as cursor:
            cursor.execute(sql_query, [data['partner_id']])
            result = cursor.fetchone()
        depot_code, route_code = result
        data['depot_id'] = depot_code
        data['route_id'] = route_code
        
        # Convert invoice type and validate invoice type
        if data['invoice_type'] == 'Expired':
            data['invoice_type'] = 'EXP'
        elif data['invoice_type'] == 'General':
            data['invoice_type'] = 'GEN'
        else:
            logger.error("Invalid invoice type provided. %s", mio)
            return Response({'success':False,"detail": "Invalid invoice type"}, status=status.HTTP_400_BAD_REQUEST)

        # Set default values
        data['request_approval'] = False
        data['withdrawal_confirmation'] = False
        data['replacement_order'] = False
        data['order_approval'] = False
        data['order_delivery'] = False
        data['last_status'] = 'request'
        data['request_date'] = date.today()
        mio = data.get('mio_id')
        # Validate and save
        serializer = WithdrawalRequestSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            logger.info("Withdrawal request created successfully for MIO %s", mio)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        logger.error(f"Error creating withdrawal request {mio} : {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class WithdrawalRequestListView(APIView):
    """
    Handles GET requests for retrieving approval list based on the parameters.
    
    Filters the data based on `mio_id`, `rm_id`, `depot_id`, `da_id`, and `status`.
    status should be: all, request_pending, request_approved
    """
    @extend_schema(
        parameters=[
            OpenApiParameter(name='mio_id', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name='rm_id', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name='depot_id', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(name='da_id', type=OpenApiTypes.STR, location=OpenApiParameter.QUERY, required=False),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Options: request_pending, request_approved, all"
            ),
        ],
        responses=WithdrawalRequestSerializer(many=True)
    )
    def get(self, request):
        """
        Handles GET requests for retrieving approval list based on the parameters.
        
        Filters the data based on `mio_id`, `rm_id`, `depot_id`, `da_id`, and `status`.
        status should be: all, request_pending, request_approved
        """
        mio_id = request.query_params.get('mio_id')
        rm_id = request.query_params.get('rm_id')
        depot_id = request.query_params.get('depot_id')
        da_id = request.query_params.get('da_id')
        stat = request.query_params.get('status')  # request_pending, request_approved
        try:
            queryset = WithdrawalInfo.objects.all()  # Default query
            
            if not any([mio_id, rm_id, depot_id, da_id]):
                return Response({"detail": "Please provide at least one ID (mio_id, rm_id, depot_id, or da_id)."}, status=status.HTTP_400_BAD_REQUEST)
            if not stat:
                return Response({"detail": "Please provide a valid status."}, status=status.HTTP_400_BAD_REQUEST)

            # Filtering based on provided parameters
            filters = {}
            if mio_id:
                filters['mio_id'] = mio_id
            if rm_id:
                filters['rm_id'] = rm_id
            if depot_id:
                filters['depot_id'] = depot_id
            if da_id:
                filters['da_id'] = da_id

            if filters:
                queryset = queryset.filter(**filters)
            
            # Filter based on the status parameter
            if stat == 'request_pending':
                queryset = queryset.filter(request_approval=False)
            elif stat == 'request_approved':
                queryset = queryset.filter(request_approval=True)
            elif stat == 'all':
                pass
            else:
                return Response({"detail": "Please provide a valid status."}, status=status.HTTP_400_BAD_REQUEST)           

            # If no records match the provided parameters, return a 404 response
            if not queryset.exists():
                logger.error(f"No matching records found. {mio_id}, {rm_id}, {depot_id}, {da_id}, {stat}")
                return Response({"detail": "No matching records found."}, status=status.HTTP_404_NOT_FOUND)
            
            # Serialize the queryset and return it as a response
            serializer = WithdrawalRequestSerializer(queryset, many=True)
            logger.info(f"Approval list fetched successfully for {mio_id}, {rm_id}, {depot_id}, {da_id}, {stat}")
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            return Response({"detail": "An error occurred while fetching data from database."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
class RequestApproveView(APIView):
    """
    View to approve a withdrawal request.
    """
    def put(self, request, invoice_no):
        """
        Approve a withdrawal request.
        
        Args:
            request (Request): The HTTP request object.
            invoice_no (str): The invoice no of the withdrawal request to be confirmed.
        
        Returns:
            Response: A response object containing the approval status.
        """
        withdrawal_request = get_object_or_404(WithdrawalInfo, invoice_no=invoice_no)
        withdrawal_request.request_approval = True
        withdrawal_request.request_approval_date = date.today()
        withdrawal_request.save()
        return Response({"detail": "Withdrawal request approved successfully."}, status=status.HTTP_200_OK)
       
    
class DaAssignView(APIView):
    """
    View to assign a delivery agent to a withdrawal request.
    """
    serializer_class = DaAssignSerializer
    @extend_schema(request=DaAssignSerializer)
    def put(self, request, invoice_no):
        """
        Assign a delivery agent to a withdrawal request.
        
        Args:
            request (Request): The HTTP request object.
            invoice_no (str): The invoice no of the withdrawal request to be assigned.
        
        Returns:
            Response: A response object containing the assignment status.
        """
        withdrawal_request = get_object_or_404(WithdrawalInfo, invoice_no=invoice_no)
        serializer = DaAssignSerializer(withdrawal_request, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Delivery agent assigned successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class WithdrawalSaveView(APIView):
    """
    View to save a withdrawal request.
    """
    @extend_schema(request=WithdrawalListSerializer(many=True)) # for drf-spectacular documentation
    def post(self, request, invoice_no):
        """
        Save a withdrawal request.
        
        Args:
            request (Request): The HTTP request object.
            invoice_no (str): The invoice no of the withdrawal request to be saved.
        
        Returns:
            Response: A response object containing the save status.
        """
        try:
            info = WithdrawalInfo.objects.get(invoice_no=invoice_no)
        except WithdrawalInfo.DoesNotExist:
            return Response({"detail": "Withdrawal request does not exist"}, status=status.HTTP_404_NOT_FOUND)
        # Get DA id for logging
        da_id = info.da_id
        # Update the withdrawal_date and save
        info.withdrawal_date = date.today()
        info.save()
        
        # Get the withdrawal items
        data = request.data
        
        # Validate and save
        serializer = WithdrawalListSerializer(data=data, many=True, context={'invoice_no': info.invoice_no})
        if serializer.is_valid():
            serializer.save()
            logger.info("Withdrawal successfully created for DA %s", da_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        logger.error(f"Error creating withdrawal {da_id} : {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class WithdrawalListView(APIView):
    """
    Handles GET requests for retrieving withdrawal list based on the parameters.
    
    Filters the data based on `mio_id`, `rm_id`, `depot_id`, `da_id`, and `status`.
    status should be: all, withdrawal_list, withdrawal_approved, order_pending, order_approved, order_delivered
    """
    @extend_schema(
        parameters=[
            OpenApiParameter(name='mio_id', description='Mio ID', required=False, type=str),
            OpenApiParameter(name='rm_id', description='RM ID', required=False, type=str),
            OpenApiParameter(name='depot_id', description='Depot ID', required=False, type=str),
            OpenApiParameter(name='da_id', description='Delivery Agent ID', required=False, type=str),
            OpenApiParameter(name='status', description='Filter status of the withdrawal request', required=True, type=str, enum=['all', 'withdrawal_list', 'withdrawal_approved', 'order_pending', 'order_approved', 'order_delivered'])
        ],
        responses={
            status.HTTP_200_OK: WithdrawalSerializer(many=True),
            status.HTTP_400_BAD_REQUEST: OpenApiResponse(description="Invalid request parameters"),
            status.HTTP_404_NOT_FOUND: OpenApiResponse(description="No matching records found"),
        }
    )
    def get(self, request):
        """
        Handles GET requests for retrieving withdrawal list based on the parameters.
    
        Filters the data based on `mio_id`, `rm_id`, `depot_id`, `da_id`, and `status`.
        status should be: all, withdrawal_list, withdrawal_approved, order_pending, order_approved, order_delivered
        """
        mio_id = request.query_params.get('mio_id')
        rm_id = request.query_params.get('rm_id')
        depot_id = request.query_params.get('depot_id')
        da_id = request.query_params.get('da_id')
        stat = request.query_params.get('status')  # request_pending, request_approved, withdrawal_list, withdrawal_approved, order_pending, order_approved, order_delivered

        queryset = WithdrawalInfo.objects.all()  # Default query
        serializer_class = WithdrawalSerializer # for  schema generation tools
         
        if not any([mio_id, rm_id, depot_id, da_id]):
            return Response({"detail": "Please provide at least one ID (mio_id, rm_id, depot_id, or da_id)."}, status=status.HTTP_400_BAD_REQUEST)
        if not stat:
            return Response({"detail": "Please provide a valid status."}, status=status.HTTP_404_NOT_FOUND)

        # Filtering based on provided parameters
        if mio_id:
            queryset = queryset.filter(mio_id=mio_id)
        if rm_id:
            queryset = queryset.filter(rm_id=rm_id)
        if depot_id:
            queryset = queryset.filter(depot_id=depot_id)
        if da_id:
            queryset = queryset.filter(da_id=da_id)
        
        # Filter based on the status parameter
        if stat == 'withdrawal_list':
            queryset = queryset.filter(request_approval=True, withdrawal_confirmation=False)
        elif stat == 'withdrawal_approved':
            queryset = queryset.filter(withdrawal_confirmation=True)
        elif stat == 'order_pending':
            queryset = queryset.filter(withdrawal_confirmation=True,order_approval=False)
        elif stat == 'order_approved':
            queryset = queryset.filter(order_approval=True)
        elif stat == 'order_delivered':
            queryset = queryset.filter(order_delivery=True)
        elif stat == 'all':
            queryset = queryset 
        else:
            return Response({"detail": "Please provide a valid status."}, status=status.HTTP_404_NOT_FOUND)           

        # Ensure we return a meaningful response
        if not queryset.exists():
            logger.error(f"No matching records found. {mio_id}, {rm_id}, {depot_id}, {da_id}, {status}")
            return Response({"detail": "No matching records found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Serialize the queryset and return it as a response
        serializer = WithdrawalSerializer(queryset, many=True)
        logger.info(f"Approval list fetched successfully for {mio_id}, {rm_id}, {depot_id}, {da_id}, {status}")
        return Response(serializer.data, status=status.HTTP_200_OK)    
    
class WithdrawalConfirmationView(APIView):
    """
    View to confirm a withdrawal request.
    """
    def put(self, request, invoice_no):
        """
        Confirm a withdrawal request.
        
        Args:
            request (Request): The HTTP request object.
            invoice_no (str): The invoice no of the withdrawal request to be confirmed.
        
        Returns:
            Response: A response object containing the confirmation status.
        """
        withdrawal_request = get_object_or_404(WithdrawalInfo, invoice_no=invoice_no)
        withdrawal_request.withdrawal_confirmation = True
        withdrawal_request.withdrawal_approval_date = date.today()
        withdrawal_request.save()
        return Response({"detail": "Withdrawal request confirmed successfully."}, status=status.HTTP_200_OK)