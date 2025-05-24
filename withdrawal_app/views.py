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
    serializer_class = WithdrawalRequestSerializer
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
        
        # Get mio, rm, depot, da, route, customer information
        main_info_query = """
            SELECT
                wi.*,
                mio.`name` AS mio_name,
                mio.mobile_number AS mio_mobile,
                rm.`name` AS rm_name,
                rm.mobile_number AS rm_mobile,
                CONCAT(c.name1, ' ', c.name2) AS partner_name,
                c.contact_person AS customer_name, 
                c.mobile_no AS customer_number,
                CONCAT(c.street, ' ', c.street1, ' ', c.street2, ' ', c.street3, ' ', c.post_code, ' ', c.district) AS customer_address,
                depot.depot_name AS depot_name,
                depot.route_name AS route_name,
                da.full_name AS da_name,
                da.mobile_number AS da_mobile
            FROM expr_withdrawal_info AS wi 
            INNER JOIN rpl_user_list AS mio ON wi.mio_id = mio.work_area_t
            INNER JOIN rpl_user_list AS rm ON wi.rm_id = rm.work_area_t
            INNER JOIN rpl_customer AS c ON wi.partner_id = c.partner
            INNER JOIN rdl_route_wise_depot AS depot ON wi.depot_id = depot.depot_code AND wi.route_id = depot.route_code
            LEFT JOIN rdl_users_list AS da ON wi.da_id = da.sap_id 
            WHERE 
        """
        if not any([mio_id, rm_id, depot_id, da_id]):
            return Response({"detail": "Please provide at least one ID (mio_id, rm_id, depot_id, or da_id)."}, status=status.HTTP_400_BAD_REQUEST)
        if not stat:
            return Response({"detail": "Please provide a valid status."}, status=status.HTTP_400_BAD_REQUEST)
        
        # filter based on mio, rm, depot , da id
        filter1=""
        params = []
        filters = {}
        if mio_id:
            filters['mio_id'] = mio_id
        if rm_id:
            filters['rm_id'] = rm_id
        if depot_id:
            filters['depot_id'] = depot_id
        if da_id:
            filters['da_id'] = da_id
        for key, value in filters.items():
            filter1 += f" wi.{key} = %s AND"
            params.append(value)
        
        filter1 = filter1[:-4]  # Remove the last 'AND'
        
        main_info_query += filter1
        
        # Filtering based on status
        if stat == 'all':
            pass
        elif stat == 'request_pending':
            main_info_query += " AND wi.request_approval = 0"
        elif stat == 'request_approved':
            main_info_query += " AND wi.request_approval = 1"
        else:
            return Response({"detail": "Invalid status provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        main_info_query += ";"
        
        # Execute the query
        try:
            with connection.cursor() as cursor:
                cursor.execute(main_info_query, params)
                data = cursor.fetchall()
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        main_info = {
            "id": data[0][0],
            "invoice_no": data[0][1],
            "invoice_type": data[0][23],
            "mio_id": data[0][2],
            "mio_name": data[0][24],
            "mio_mobile": data[0][25],
            "rm_id": data[0][3],
            "rm_name": data[0][26],
            "rm_mobile": data[0][27],
            "da_id": data[0][4],
            "da_name": data[0][34],
            "da_mobile": data[0][35],
            "depot_id": data[0][5],
            "depot_name": data[0][32],
            "route_id": data[0][6],
            "route_name": data[0][33],
            "partner_id": data[0][7],
            "partner_name": data[0][28],
            "customer_name": data[0][29],
            "customer_number": data[0][30],
            "customer_address": data[0][31],
            "request_approval": data[0][8],
            "withdrawal_confirmation": data[0][9],
            "replacement_order": data[0][10],
            "order_approval": data[0][11],
            "order_delivery": data[0][12],
            "request_date": data[0][13],
            "request_approval_date": data[0][14],
            "withdrawal_date": data[0][15],
            "withdrawal_approval_date": data[0][16],
            "order_date": data[0][17],
            "order_approval_date": data[0][18],
            "delivery_date": data[0][19],
            "last_status": data[0][20],    
        }
        
        # Fetching material list
        material_list_query = """
        SELECT rl.*, m.material_name, m.producer_company, m.unit_tp, m.unit_vat 
        FROM expr_request_list AS rl 
        INNER JOIN rpl_material AS m ON rl.matnr = m.matnr
        WHERE rl.invoice_id_id = %s;
        """
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(material_list_query, [main_info['id']])
                material_list = cursor.fetchall()
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        request_list = []
        for material in material_list:
            request_list.append({
                "matnr": material[1],
                "material_name": material[11],
                "producer_company": material[12],
                "batch": material[2],
                "pack_qty": material[3],
                "strip_qty": material[4],
                "unit_qty": material[5],
                "net_val": material[6],
                "unit_tp": material[13],
                "unit_vat": material[14],
                "expire_date": material[10],
            })
        
        # merger main_info and request_list
        main_info['request_list'] = request_list
        
        logger.info(f"Approval list fetched successfully for {mio_id}, {rm_id}, {depot_id}, {da_id}, {stat}")
        return Response({"success":True, "data": main_info}, status=status.HTTP_200_OK)
    
    
class RequestApproveView(APIView):
    """
    View to approve a withdrawal request.
    """
    schema = None # Disable schema generation
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
        withdrawal_request.last_status = 'request_approved'
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
    serializer_class = WithdrawalListSerializer(many=True)
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
    schema = None  # Disable schema generation
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
    
    