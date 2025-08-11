import logging
from datetime import date
from collections import defaultdict
from django.db import connection
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from withdrawal_app.serializers import WithdrawalRequestSerializer, WithdrawalSerializer, WithdrawalListSerializer, DaAssignSerializer
from withdrawal_app.models import WithdrawalInfo
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiTypes
from .utils import paginate, mtnr_unit_price

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
        
        mio = data.get('mio_id')
        
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
        
        if not result:
            logger.error("No depot code found for the given partner ID. %s", data['partner_id'])
            return Response({'success':False,"detail": "No depot code found for the given partner ID"}, status=status.HTTP_400_BAD_REQUEST)
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
        status_filter = request.query_params.get('status')  # request_pending, request_approved
        
        # Validate inputs 
        if not any([mio_id, rm_id, depot_id, da_id]):
            return Response({"success":False,"message": "Please provide at least one ID (mio_id, rm_id, depot_id, or da_id)."}, status=status.HTTP_400_BAD_REQUEST)
        if status_filter not in ['all', 'request_pending', 'request_approved', 'withdrawal_pending', 'withdrawal_approval', 'withdrawal_approved']:
            return Response({"success":False,"message": "Please provide a valid status.[all, request_pending, request_approved, withdrawal_pending]"}, status=status.HTTP_400_BAD_REQUEST)
               
        # filter based on mio, rm, depot , da id
        params = []
        filters = []
        if mio_id:
            filters.append("wi.mio_id = %s")
            params.append(mio_id)
        if rm_id:
            filters.append("wi.rm_id = %s")
            params.append(rm_id)
        if depot_id:
            filters.append("wi.depot_id = %s")
            params.append(depot_id)
        if da_id:
            filters.append("wi.da_id = %s")
            params.append(da_id)
        
        # Filtering based on status
        if status_filter == 'request_pending':
            filters.append("wi.last_status = 'request_pending'")
        elif status_filter == 'request_approved':
            filters.append("wi.last_status = 'request_approved'")
        elif status_filter == 'withdrawal_pending':
            filters.append("wi.last_status= 'withdrawal_pending'")
        elif status_filter == 'withdrawal_approval':
            filters.append("wi.last_status= 'withdrawal_approval'")
        elif status_filter == 'withdrawal_approved':
            filters.append("wi.last_status= 'withdrawal_approved'")
            
        # Verify if filters are present
        if not filters:
            return Response({"success":False,"message": "At least one filter is required."}, status=status.HTTP_400_BAD_REQUEST)
        # where  clause
        where_clause = " AND ".join(filters)
        
        # WithdrawalInfo query
        main_info_query = f"""
            SELECT
                wi.id, wi.invoice_no, wi.mio_id, wi.rm_id, wi.da_id, wi.depot_id, wi.route_id, wi.partner_id, wi.request_approval, wi.withdrawal_confirmation, wi.replacement_order, wi.order_approval, wi.order_delivery, wi.request_date, wi.request_approval_date, wi.withdrawal_date, wi.withdrawal_approval_date, wi.order_date, wi.order_approval_date, wi.delivery_date, wi.last_status, wi.invoice_type, 
                mio.`name` AS mio_name,
                mio.mobile_number AS mio_mobile,
                rm.`name` AS rm_name,
                rm.mobile_number AS rm_mobile,
                CONCAT(COALESCE(c.name1, ''), ' ', COALESCE(c.name2, '')) AS partner_name,
                c.contact_person AS customer_name, 
                c.mobile_no AS customer_number,
                CONCAT(
                    COALESCE(c.street, ''), ' ', COALESCE(c.street1, ''), ' ', COALESCE(c.street2, ''), ' ', COALESCE(c.street3, ''), ' ', COALESCE(c.post_code, ''), ' ', COALESCE(c.district, '')
                ) AS customer_address,
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
            WHERE {where_clause}
            ORDER BY wi.id DESC
            LIMIT 200;
        """
        print(
            f"main_info_query: {main_info_query}",
        )       
        # Execute the query
        try:
            with connection.cursor() as cursor:
                cursor.execute(main_info_query, params)
                columns = [col[0] for col in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return Response({"success":False,"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if not rows:
            return Response({"success": True,"message":"No Items Found!", "data": []})
        
        # Get all invoice IDs to fetch material list
        invoice_ids = [row['id'] for row in rows]     
        
        # Fetching material list query
        material_list_query = """
        SELECT rl.id AS list_id, rl.invoice_id_id AS invoice_id, rl.matnr, rl.batch, rl.pack_qty, rl.strip_qty, rl.unit_qty, rl.net_val, rl.expire_date, m.material_name, m.producer_company, m.unit_tp, m.unit_vat , m.pack_size 
        FROM expr_request_list AS rl 
        INNER JOIN rpl_material AS m ON rl.matnr = m.matnr
        WHERE rl.invoice_id_id IN %s;
        """
        
        if invoice_ids:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(material_list_query,[tuple(invoice_ids)])
                    material_rows = cursor.fetchall()
                    material_columns = [col[0] for col in cursor.description]
                    materials = [dict(zip(material_columns, row)) for row in material_rows]   
            except Exception as e:
                logger.error(f"Error executing query: {e}")
                return Response({"success":False,"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        # Group materials by invoice_id
        material_map = defaultdict(list)
        for mat in materials:
            material_map[mat['invoice_id']].append({
                "list_id": mat['list_id'],
                "matnr": mat['matnr'],
                "material_name": mat['material_name'],
                "producer_company": mat['producer_company'],
                "batch": mat['batch'],
                "pack_qty": mat['pack_qty'],
                "strip_qty": mat['strip_qty'],
                "unit_qty": mat['unit_qty'],
                "net_val": mat['net_val'],
                "unit_tp": mat['unit_tp'],
                "unit_vat": mat['unit_vat'],
                "expire_date": mat['expire_date'],
                "pack_price": mat['unit_tp']+mat['unit_vat'],
                "unit_price": mtnr_unit_price(mat['pack_size'], mat['unit_tp'], mat['unit_vat'])
            })
                                    
        # Attach materials to each row
        for row in rows:
            row['request_list'] = material_map.get(row['id'], [])
            
        # pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('per_page', 10))
        if page <= 0 or page_size <= 0:
            return Response({
                "success": False,
                "message": "Invalid 'page' or 'per_page'. Must be positive integers."
            }, status=status.HTTP_400_BAD_REQUEST)
            
        paginate_results= paginate(rows,page=page,per_page=page_size)
        logger.info(f"Fetched {len(rows)} withdrawal requests")
        return Response(paginate_results, status=status.HTTP_200_OK)
    
    
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
    def put(self, request):
        """
        Assign a delivery agent to a withdrawal request.
        
        Args:
            request (Request): The HTTP request object.
            invoice_no (str): The invoice no of the withdrawal request to be assigned.
        
        Returns:
            Response: A response object containing the assignment status.
        """
        invoice_no = request.data.get('invoice_no')
        withdrawal_request = get_object_or_404(WithdrawalInfo, invoice_no=invoice_no)
        serializer = DaAssignSerializer(withdrawal_request, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(last_status=WithdrawalInfo.Status.WITHDRAWAL_PENDING) 
            logger.info(f"Delivery agent assigned to withdrawal request {invoice_no}")
            return Response({"success":True,"message": "Delivery agent assigned successfully.", "data": serializer.data}, status=status.HTTP_200_OK)
        logger.error(f"Error assigning delivery agent to withdrawal request {invoice_no}: {serializer.errors}")
        return Response({"success":False,"message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    
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
            return Response({"success":False,"message": "Withdrawal request does not exist"}, status=status.HTTP_404_NOT_FOUND)
        # Get DA id for logging
        da_id = info.da_id
        # Update the withdrawal_date and save
        info.withdrawal_date = date.today()
        info.last_status = info.Status.WITHDRAWAL_APPROVAL
        
        # Get the withdrawal items
        data = request.data
        
        # Validate and save
        serializer = WithdrawalListSerializer(data=data, many=True, context={'invoice_no': info.invoice_no})
        if serializer.is_valid():
            info.save()
            serializer.save()
            logger.info("Withdrawal successfully created for DA %s", da_id)
            return Response({"success":True,"message":"Items Save Successfully.","data":serializer.data}, status=status.HTTP_201_CREATED)
        logger.error(f"Error creating withdrawal {da_id} : {serializer.errors}")
        return Response({"success":False, "message":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
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
            return Response({"success":False,"message": "Please provide at least one ID (mio_id, rm_id, depot_id, or da_id)."}, status=status.HTTP_400_BAD_REQUEST)
        if not stat:
            return Response({"success":False,"message": "Please provide a valid status."}, status=status.HTTP_404_NOT_FOUND)

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
            return Response({"success":False,"message": "Please provide a valid status."}, status=status.HTTP_404_NOT_FOUND)           

        # Ensure we return a meaningful response
        if not queryset.exists():
            logger.error(f"No matching records found. {mio_id}, {rm_id}, {depot_id}, {da_id}, {status}")
            return Response({"success":False,"message": "No matching records found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Serialize the queryset and return it as a response
        serializer = WithdrawalSerializer(queryset, many=True)
        logger.info(f"Approval list fetched successfully for {mio_id}, {rm_id}, {depot_id}, {da_id}, {status}")
        return Response({"success":True,"message": "Approval list fetched successfully.","data":serializer.data}, status=status.HTTP_200_OK)    
    
class WithdrawalConfirmationView(APIView):
    """
    View to confirm a withdrawal request.
    """
    schema = None  # Disable schema generation
    def put(self, request):
        """
        Confirm a withdrawal request.
        
        Args:
            request (Request): The HTTP request object.
            invoice_no (str): The invoice no of the withdrawal request to be confirmed.
        
        Returns:
            Response: A response object containing the confirmation status.
        """
        invoice_no = request.data.get('invoice_no')
        withdrawal_request = get_object_or_404(WithdrawalInfo, invoice_no=invoice_no)
        withdrawal_request.withdrawal_confirmation = True
        withdrawal_request.withdrawal_approval_date = date.today()
        withdrawal_request.last_status = 'withdrawal_approved'
        withdrawal_request.save()
        return Response({"success":True,"message": "Withdrawal request confirmed successfully.","data":{"invoice_no": invoice_no}}, status=status.HTTP_200_OK)
    
class WithdrawalRequestUpdateView(APIView):
    @extend_schema(request=WithdrawalRequestSerializer) # for drf-spectacular documentation
    def put(self, request):
        """
        Update an existing withdrawal request.
        Allows modifying the list: add , update or remove items.
        
        Args:
            request (Request): The HTTP request object.
            invoice_no (str): The invoice number of the withdrawal request to update.
        Returns:
            Response: A response object containing the updated withdrawal request data.
        """
        
        data = request.data.copy()
        invoice_no = data.get('invoice_no')
        
        instance = get_object_or_404(WithdrawalInfo, invoice_no=invoice_no)
        
        
        # Ensure invoice type is valid
        if data['invoice_type'] in ['EXP', 'Expired']:
            data['invoice_type'] = 'EXP'
        elif data['invoice_type'] in ['GEN', 'General']:
            data['invoice_type'] = 'GEN'
        else:
            logger.error("Invalid invoice type provided. %s", invoice_no)
            return Response({'success':False,"detail": "Invalid invoice type"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = WithdrawalRequestSerializer(instance, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info("Withdrawal request updated successfully for MIO %s", invoice_no)
            return Response({'success':True,'detail':'Withdrawal request updated successfully','data':serializer.data}, status=status.HTTP_200_OK)
        logger.error(f"Error updating withdrawal request {invoice_no} : {serializer.errors}")
        return Response({'success':False,"detail": serializer.errors}, status=status.HTTP_400_BAD_REQUEST) 
    

class WithdrawalInfoFinalListView(APIView):
    def get(self, request):
        mio_id = request.query_params.get('mio_id')
        rm_id = request.query_params.get('rm_id')
        depot_id = request.query_params.get('depot_id')
        da_id = request.query_params.get('da_id')
    
        # Validate inputs 
        if not any([mio_id, rm_id, depot_id, da_id]):
            return Response({"success":False,"message": "Please provide at least one ID (mio_id, rm_id, depot_id, or da_id)."}, status=status.HTTP_400_BAD_REQUEST)
        stat = request.GET.get('status', 'withdrawal_pending')
        if stat not in['withdrawal_approval', 'withdrawal_approved']:
            return Response({"success":False,"message": "Please provide a valid status (withdrawal_approval or withdrawal_approved)."}, status=status.HTTP_400_BAD_REQUEST)
        params = []
        filters = []
        if mio_id:
            filters.append("wi.mio_id = %s")
            params.append(mio_id)
        if rm_id:
            filters.append("wi.rm_id = %s")
            params.append(rm_id)
        if depot_id:
            filters.append("wi.depot_id = %s")
            params.append(depot_id)
        if da_id:
            filters.append("wi.da_id = %s")
            params.append(da_id)
        
        if stat == 'withdrawal_approval':
            filters.append("wi.last_status = 'withdrawal_pending'")
        elif stat == 'withdrawal_approved':
            filters.append("wi.last_status = 'withdrawal_approved'")
        
        where_clause = " AND ".join(filters)

        sql = f"""
        SELECT 
            wi.invoice_no,
            wi.mio_id,
            wi.rm_id,
            wi.da_id,
            ul.full_name AS da_name,
            ul.mobile_number AS da_mobile_no,
            wi.depot_id,
            wi.route_id,
            wi.partner_id,
            CONCAT(c.name1, c.name2) AS partner_name,
            CONCAT(c.street, c.street1, c.street2, c.upazilla, c.district) AS partner_address,
            c.mobile_no AS partner_mobile_no,
            c.contact_person,
            wi.request_approval,
            wi.withdrawal_confirmation,
            wi.replacement_order,
            wi.order_approval,
            wi.order_delivery,
            wi.request_date,
            wi.request_approval_date,
            wi.withdrawal_date,
            wi.withdrawal_approval_date,
            wi.order_date,
            wi.order_approval_date,
            wi.delivery_date,
            wi.last_status,

            rl.matnr AS matnr,
            m.material_name,
            rl.batch AS batch,
            rl.pack_qty AS request_pack_qty,
            rl.unit_qty AS request_unit_qty,
            rl.net_val AS request_net_val,
            rl.expire_date AS expire_date,

            wl.pack_qty AS withdrawal_pack_qty,
            wl.unit_qty AS withdrawal_unit_qty,
            wl.net_val AS withdrawal_net_val

        FROM expr_withdrawal_info wi
        INNER JOIN expr_request_list rl ON wi.id = rl.invoice_id_id
        LEFT JOIN expr_withdrawal_list wl ON wi.id = wl.invoice_id_id AND rl.matnr = wl.matnr
        INNER JOIN rpl_material m ON rl.matnr = m.matnr
        INNER JOIN rpl_customer c ON wi.partner_id = c.partner
        INNER JOIN rdl_users_list ul ON wi.da_id = ul.sap_id
        WHERE {where_clause}
        ORDER BY wi.id DESC
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            if cursor.description is None:
                return Response({"success":True,"message": "No data found.", "data":[] }, status=status.HTTP_200_OK)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        # Column mapping
        material_cols = ["matnr", "material_name", "batch", "request_pack_qty", "request_unit_qty",
                "request_net_val", "expire_date", "withdrawal_pack_qty", "withdrawal_unit_qty",
                "withdrawal_net_val"]

        data_map = defaultdict(lambda: {
            **{col: None for col in columns if col not in material_cols},
            "materials": []
        })
        
        if not rows:
            return Response({"success":True,"message": "No data found.", "data":[] }, status=status.HTTP_200_OK)

        for row in rows:
            row_dict = dict(zip(columns, row))
            invoice_no = row_dict["invoice_no"]

            # Only set general invoice info once
            if not data_map[invoice_no]["invoice_no"]:
                for col in columns:
                    if col not in ["matnr", "material_name", "batch", "request_pack_qty", "request_unit_qty", 
                                   "request_net_val", "expire_date", "withdrawal_pack_qty", 
                                   "withdrawal_unit_qty", "withdrawal_net_val"]:
                        data_map[invoice_no][col] = row_dict[col]

            # Append material info
            data_map[invoice_no]["materials"].append({
                "matnr": row_dict["matnr"],
                "material_name": row_dict["material_name"],
                "batch": row_dict["batch"],
                "request_pack_qty": row_dict["request_pack_qty"],
                "request_unit_qty": row_dict["request_unit_qty"],
                "request_net_val": row_dict["request_net_val"],
                "expire_date": row_dict["expire_date"],
                "withdrawal_pack_qty": row_dict["withdrawal_pack_qty"],
                "withdrawal_unit_qty": row_dict["withdrawal_unit_qty"],
                "withdrawal_net_val": row_dict["withdrawal_net_val"]
            })

        # Convert to list
        data_list = list(data_map.values())

        # pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('per_page', 10))
        if page <= 0 or page_size <= 0:
            return Response({
                "success": False,
                "message": "Invalid 'page' or 'per_page'. Must be positive integers."
            }, status=status.HTTP_400_BAD_REQUEST)
        paginate_results= paginate(data_list,page=page,per_page=page_size)
        logger.info(f"Fetched {len(data_list)} withdrawal requests")
        return Response(paginate_results, status=status.HTTP_200_OK)
