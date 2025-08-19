from django.db.models import Sum
from django.db import connection
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from withdrawal_app.models import WithdrawalInfo
from .serializers import AvailableReplacementListSerializer, ReplacementListSerializer, ReplacementApprovalListSerializer
from withdrawal_app.utils import paginate
from .models import ReplacementList
from datetime import date
from collections import defaultdict
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
            invoice.order_date = date.today()
            invoice.save()

            return Response(
                {"success":True,"message": "Replacement list created successfully","data":serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response({"success":False,"message":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
class ReplacementApprovalListView(APIView):
    def get(self, request):
        rm_id = request.query_params.get("rm_id")
        if not rm_id:
            return Response({"success":False, "message":"You Must need to pass rm id."}, status=status.HTTP_400_BAD_REQUEST)
        
        withdrawal_info = WithdrawalInfo.objects.filter(rm_id=rm_id, last_status=WithdrawalInfo.Status.REPLACEMENT_APPROVAL)
        if withdrawal_info.exists():
            serializer = ReplacementApprovalListSerializer(withdrawal_info, many=True)
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 10))
            if page <= 0 or per_page <= 0:
                return Response({"success":False,"message": "Invalid page or per_page parameters."}, status=status.HTTP_400_BAD_REQUEST)
            results = paginate(serializer.data, page=page, per_page=per_page)
            return Response(results, status=status.HTTP_200_OK)
        else:
            return Response(paginate([], message="No available replacements found."), status=status.HTTP_404_NOT_FOUND)
        
        
    
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
        
class ReplacementOrderRequestList(APIView):
    def get(self, request):
        mio_id = request.query_params.get('mio_id')
        rm_id = request.query_params.get('rm_id')
        depot_id = request.query_params.get('depot_id')
        da_id = request.query_params.get('da_id')
        # Validate inputs 
        if not any([mio_id, rm_id, depot_id, da_id]):
            return Response({"success":False,"message": "Please provide at least one ID (mio_id, rm_id, depot_id, or da_id)."}, status=status.HTTP_400_BAD_REQUEST)
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
            
        where_clause = " AND ".join(filters)
        sql= f"""
        SELECT
            wi.invoice_no,
            wi.mio_id,
            wi.rm_id,
            wi.depot_id,
            wi.route_id,
            r.route_name,
            wi.partner_id,
            CONCAT(c.name1, c.name2) AS partner_name,
            CONCAT(c.street, c.street1, c.street2, c.upazilla, c.district) AS partner_address,
            c.mobile_no AS partner_mobile_no,
            c.contact_person,
            wi.order_date,
            wi.order_approval_date,
            wi.delivery_da_id,
            wi.last_status,
            rl.matnr,
            m.material_name,
            rl.pack_qty,
            rl.unit_qty,
            rl.net_val
        FROM expr_withdrawal_info wi 
        INNER JOIN expr_replacement_list rl ON wi.id = rl.invoice_id
        INNER JOIN rpl_customer c ON wi.partner_id = c.partner
        INNER JOIN rpl_material m ON rl.matnr = m.matnr
        INNER JOIN rdl_route_wise_depot r ON wi.route_id = r.route_code
        WHERE {where_clause} AND wi.last_status='replacement_approved' AND wi.delivery_da_id is NULL;
        """
        with connection.cursor() as cursor:
                cursor.execute(sql, params)
                if cursor.description is None:
                    return Response(paginate([],message="No data found.", page=1, per_page=10), status=status.HTTP_200_OK)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
        # Column mapping
        material_cols = ["matnr", "material_name", "batch", "pack_qty", "unit_qty","net_val"]
        data_map = defaultdict(lambda: {
            **{col: None for col in columns if col not in material_cols},
            "materials": []
        })
        if not rows:
            return Response(paginate([],message="No data found.", page=1, per_page=10), status=status.HTTP_200_OK)
        for row in rows:
            row_dict = dict(zip(columns, row))
            invoice_no = row_dict["invoice_no"]

            # Only set general invoice info once
            if not data_map[invoice_no]["invoice_no"]:
                for col in columns:
                    if col not in material_cols:
                        data_map[invoice_no][col] = row_dict[col]

            # Append material info
            data_map[invoice_no]["materials"].append({
                "matnr": row_dict["matnr"],
                "material_name": row_dict["material_name"],
                # "batch": row_dict["batch"],
                "pack_qty": row_dict["pack_qty"],
                "unit_qty": row_dict["unit_qty"],
                "net_val": row_dict["net_val"],
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
        return Response(paginate_results, status=status.HTTP_200_OK)

class AssignDeliveryDA(APIView):
    def put(self, request):
        invoice_no = request.data.get("invoice_no")
        delivery_da_id = request.data.get("delivery_da_id")
        if not invoice_no or not delivery_da_id:
            return Response({"success":False,"message": "Please provide invoice_no and delivery_da_id."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            info = WithdrawalInfo.objects.get(invoice_no=invoice_no)
        except WithdrawalInfo.DoesNotExist:
            return Response({"success":False,"message": "Withdrawal info does not exist"}, status=status.HTTP_404_NOT_FOUND)
        info.delivery_da_id = delivery_da_id
        info.last_status = info.Status.DELIVERY_PENDING
        info.save()
        return Response({"success":True,"message": "DA assigned successfully.", "data":{"invoice_no":invoice_no, "delivery_da_id":delivery_da_id}}, status=status.HTTP_200_OK)
    
class ReplacementDeliveryPendingList(APIView):
    def get(self, request):
        mio_id = request.query_params.get('mio_id')
        rm_id = request.query_params.get('rm_id')
        depot_id = request.query_params.get('depot_id')
        da_id = request.query_params.get('da_id')
        # Validate inputs 
        if not any([mio_id, rm_id, depot_id, da_id]):
            return Response({"success":False,"message": "Please provide at least one ID (mio_id, rm_id, depot_id, or da_id)."}, status=status.HTTP_400_BAD_REQUEST)
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
            
        where_clause = " AND ".join(filters)
        sql= f"""
        SELECT
            wi.invoice_no,
            wi.mio_id,
            wi.rm_id,
            wi.depot_id,
            wi.route_id,
            r.route_name,
            wi.partner_id,
            CONCAT(c.name1, c.name2) AS partner_name,
            CONCAT(c.street, c.street1, c.street2, c.upazilla, c.district) AS partner_address,
            c.mobile_no AS partner_mobile_no,
            c.contact_person,
            wi.order_date,
            wi.order_approval_date,
            wi.delivery_da_id,
            wi.last_status,
            rl.matnr,
            m.material_name,
            rl.pack_qty,
            rl.unit_qty,
            rl.net_val
        FROM expr_withdrawal_info wi 
        INNER JOIN expr_replacement_list rl ON wi.id = rl.invoice_id
        INNER JOIN rpl_customer c ON wi.partner_id = c.partner
        INNER JOIN rpl_material m ON rl.matnr = m.matnr
        INNER JOIN rdl_route_wise_depot r ON wi.route_id = r.route_code
        WHERE {where_clause} AND wi.last_status='delivery_pending';
        """
        with connection.cursor() as cursor:
                cursor.execute(sql, params)
                if cursor.description is None:
                    return Response(paginate([],message="No data found.", page=1, per_page=10), status=status.HTTP_200_OK)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
        # Column mapping
        material_cols = ["matnr", "material_name", "batch", "pack_qty", "unit_qty","net_val"]
        data_map = defaultdict(lambda: {
            **{col: None for col in columns if col not in material_cols},
            "materials": []
        })
        if not rows:
            return Response(paginate([],message="No data found.", page=1, per_page=10), status=status.HTTP_200_OK)
        for row in rows:
            row_dict = dict(zip(columns, row))
            invoice_no = row_dict["invoice_no"]

            # Only set general invoice info once
            if not data_map[invoice_no]["invoice_no"]:
                for col in columns:
                    if col not in material_cols:
                        data_map[invoice_no][col] = row_dict[col]

            # Append material info
            data_map[invoice_no]["materials"].append({
                "matnr": row_dict["matnr"],
                "material_name": row_dict["material_name"],
                # "batch": row_dict["batch"],
                "pack_qty": row_dict["pack_qty"],
                "unit_qty": row_dict["unit_qty"],
                "net_val": row_dict["net_val"],
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
        return Response(paginate_results, status=status.HTTP_200_OK)
    
    
class ReplacementDeliveredList(APIView):
    def get(self, request):
        mio_id = request.query_params.get('mio_id')
        rm_id = request.query_params.get('rm_id')
        depot_id = request.query_params.get('depot_id')
        da_id = request.query_params.get('da_id')
        delivery_da_id = request.query_params.get('delivery_da_id')
        # Validate inputs 
        if not any([mio_id, rm_id, depot_id, da_id, delivery_da_id]):
            return Response({"success":False,"message": "Please provide at least one ID (mio_id, rm_id, depot_id, da_id, or  delivery_Da_id)."}, status=status.HTTP_400_BAD_REQUEST)
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
        if delivery_da_id:
            filters.append("wi.delivery_da_id = %s")
            params.append(delivery_da_id)
            
        where_clause = " AND ".join(filters)
        sql= f"""
        SELECT
            wi.invoice_no,
            wi.mio_id,
            wi.rm_id,
            wi.depot_id,
            wi.route_id,
            r.route_name,
            wi.partner_id,
            CONCAT(c.name1, c.name2) AS partner_name,
            CONCAT(c.street, c.street1, c.street2, c.upazilla, c.district) AS partner_address,
            c.mobile_no AS partner_mobile_no,
            c.contact_person,
            wi.order_date,
            wi.order_approval_date,
            wi.delivery_da_id,
            wi.last_status,
            rl.matnr,
            m.material_name,
            rl.pack_qty,
            rl.unit_qty,
            rl.net_val
        FROM expr_withdrawal_info wi 
        INNER JOIN expr_replacement_list rl ON wi.id = rl.invoice_id
        INNER JOIN rpl_customer c ON wi.partner_id = c.partner
        INNER JOIN rpl_material m ON rl.matnr = m.matnr
        INNER JOIN rdl_route_wise_depot r ON wi.route_id = r.route_code
        WHERE {where_clause} AND wi.last_status='delivered';
        """
        with connection.cursor() as cursor:
                cursor.execute(sql, params)
                if cursor.description is None:
                    return Response(paginate([],message="No data found.", page=1, per_page=10), status=status.HTTP_200_OK)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
        # Column mapping
        material_cols = ["matnr", "material_name", "batch", "pack_qty", "unit_qty","net_val"]
        data_map = defaultdict(lambda: {
            **{col: None for col in columns if col not in material_cols},
            "materials": []
        })
        if not rows:
            return Response(paginate([],message="No data found.", page=1, per_page=10), status=status.HTTP_200_OK)
        for row in rows:
            row_dict = dict(zip(columns, row))
            invoice_no = row_dict["invoice_no"]

            # Only set general invoice info once
            if not data_map[invoice_no]["invoice_no"]:
                for col in columns:
                    if col not in material_cols:
                        data_map[invoice_no][col] = row_dict[col]

            # Append material info
            data_map[invoice_no]["materials"].append({
                "matnr": row_dict["matnr"],
                "material_name": row_dict["material_name"],
                # "batch": row_dict["batch"],
                "pack_qty": row_dict["pack_qty"],
                "unit_qty": row_dict["unit_qty"],
                "net_val": row_dict["net_val"],
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
        return Response(paginate_results, status=status.HTTP_200_OK)
    
class ReplacementDelivery(APIView):
    def put(self, request):
        invoice_no = request.data.get('invoice_no')
        if not invoice_no:
            return Response({"success":False,"message": "Please provide invoice_no."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            info = WithdrawalInfo.objects.get(invoice_no=invoice_no)
            info.delivery_date = date.today()
            info.last_status = info.Status.DELIVERED
            info.save()
            return Response({"success":True,"message": "Delivery data updated successfully.", "data":{"invoice_no":invoice_no}}, status=status.HTTP_200_OK)
        except WithdrawalInfo.DoesNotExist:
            return Response({"success":False,"message": "Withdrawal request does not exist"}, status=status.HTTP_404_NOT_FOUND)
        
class AvailableReplacementListView2(APIView):
    def get(self, request):
        mio_id = request.query_params.get('mio_id')
        rm_id = request.query_params.get('rm_id')
        depot_id = request.query_params.get('depot_id')
        da_id = request.query_params.get('da_id')
        # Validate inputs 
        if not any([mio_id, rm_id, depot_id, da_id]):
            return Response({"success":False,"message": "Please provide at least one ID (mio_id, rm_id, depot_id, or da_id)."}, status=status.HTTP_400_BAD_REQUEST)
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
            
        where_clause = " AND ".join(filters)
        sql= f"""
        SELECT
            wi.*,
            rl.*,
            wl.*,
            CONCAT(c.name1, c.name2) AS partner_name,
            CONCAT(c.street, c.street1, c.street2, c.upazilla, c.district) AS partner_address,
            c.mobile_no AS partner_mobile_no,
            c.contact_person,
            m.material_name
        FROM expr_withdrawal_info wi 
        INNER JOIN expr_request_list rl ON wi.id = rl.invoice_id_id
        LEFT JOIN expr_withdrawal_list wl ON wi.id = wl.invoice_id_id AND rl.matnr = wl.matnr
        INNER JOIN rpl_customer c ON wi.partner_id = c.partner
        INNER JOIN rpl_material m ON rl.matnr = m.matnr
        WHERE {where_clause} AND last_status='withdrawal_approved';
        """
        with connection.cursor() as cursor:
                cursor.execute(sql, params)
                if cursor.description is None:
                    return Response(paginate([],message="No data found.", page=1, per_page=10), status=status.HTTP_200_OK)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
        # Column mapping
        if not rows:
            return Response(paginate([],message="No data found.", page=1, per_page=10), status=status.HTTP_200_OK)

        grouped_data = {}
        for row in rows:
            if row[1] not in grouped_data:
                data = {
                    "id": row[0],
                    "total_amount": 0.0,
                    "partner_name": row[51],
                    "customer_address": row[52],
                    "customer_mobile": row[53],
                    "contact_person": row[54],
                    "invoice_no": row[1],
                    "invoice_type": row[23],
                    "mio_id": row[2],
                    "mio_name": "",
                    "rm_id": row[3],
                    "da_id": row[4],
                    "depot_id": row[5],
                    "route_id": row[6],
                    "partner_id": row[7],
                    "request_approval":True if row[8] else False,
                    "withdrawal_confirmation":True if row[9] else False,
                    "replacement_order":True if row[10] else False,
                    "order_approval":True if row[11] else False,
                    "order_delivery":True if row[12] else False,
                    "request_date": row[13],
                    "request_approval_date": row[14],
                    "withdrawal_date": row[15],
                    "withdrawal_approval_date": row[16],
                    "order_date": row[17],
                    "order_approval_date": row[18],
                    "delivery_da_id": row[24],
                    "delivery_date": row[19],
                    "last_status": row[20],
                    "created_at": row[21],
                    "updated_at": row[22],
                    "request_list": [],
                    "withdrawal_list": []
                }
                grouped_data[row[1]] = data
            request_list_data={
                "id": row[25],
                "matnr": row[26],
                "material_name": row[55],
                "batch": row[27],
                "pack_qty": row[28],
                "strip_qty": row[29],
                "unit_qty": row[30],
                "net_val": row[31],
                "expire_date": row[35],
                "rel_invoice_no": row[37],
                "rel_invoice_date": row[36],
                "rel_mio_name": row[38],
                "rel_mio_phone": row[39],
                "created_at": row[32],
                "updated_at": row[33],
                "invoice_id": row[34]
            }
            grouped_data[row[1]]['request_list'].append(request_list_data)
            
            withdrawal_list_data = {
                "id": row[40],
                "matnr": row[41],
                "material_name": row[55],
                "batch": row[42],
                "pack_qty": row[43],
                "strip_qty": row[44],
                "unit_qty": row[45],
                "net_val": row[46],
                "expire_date": row[50],
                "created_at": row[47],
                "updated_at": row[48],
                "invoice_id": row[49]
            }
            grouped_data[row[1]]['withdrawal_list'].append(withdrawal_list_data)
            grouped_data[row[1]]['total_amount'] += float(row[46])

        # Convert to list
        data_list = list(grouped_data.values())

        # pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('per_page', 10))
        if page <= 0 or page_size <= 0:
            return Response({
                "success": False,
                "message": "Invalid 'page' or 'per_page'. Must be positive integers."
            }, status=status.HTTP_400_BAD_REQUEST)
        paginate_results= paginate(data_list,page=page,per_page=page_size)
        return Response(paginate_results, status=status.HTTP_200_OK)