from rest_framework import serializers
from withdrawal_app.models import WithdrawalList, WithdrawalRequestList, WithdrawalInfo

class WithdrawalRequestListSerializer(serializers.ModelSerializer):
    """
    Serializer for the WithdrawalRequestList model.
    
    This serializer is used to create a withdrawal request list.
    """
    expire_date = serializers.DateField(required=True)
    pack_qty = serializers.IntegerField(required=True, min_value=0)
    strip_qty = serializers.IntegerField(required=True, min_value=0)
    unit_qty = serializers.IntegerField(required=True, min_value=0)
    net_val = serializers.DecimalField(max_digits=10, decimal_places=2, required=True, min_value=0)

    class Meta:
        model = WithdrawalRequestList
        exclude = ['created_at', 'updated_at']
        extra_kwargs = {
            'invoice_id': {'read_only': True}
        }
       
class WithdrawalListSerializer(serializers.ModelSerializer):
    """
    Serializer for the WithdrawalList model.
    
    This serializer is used to create a withdrawal list.
    """
    class Meta:
        model = WithdrawalList
        fields = '__all__'
        read_only_fields = ['invoice_id'] 
        
    def create(self, validated_data):
        invoice_no = self.context.get('invoice_no')
        try:
            invoice_instance = WithdrawalInfo.objects.get(invoice_no=invoice_no)
        except WithdrawalInfo.DoesNotExist:
            raise serializers.ValidationError("Invalid invoice_no passed in context.")
        
        validated_data['invoice_id'] = invoice_instance
        return WithdrawalList.objects.create(**validated_data)


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for the WithdrawalInfo model.
    
    This serializer is used to create a withdrawal request.
    """
    # These fields are both readable and writable
    mio_id = serializers.CharField()
    rm_id = serializers.CharField()
    partner_id = serializers.CharField()
    invoice_type = serializers.ChoiceField(choices=WithdrawalInfo.InvoiceType.choices)
    depot_id = serializers.CharField()
    route_id = serializers.CharField()
    request_date = serializers.DateField()

    # Read-only fields
    invoice_no = serializers.CharField(read_only=True)
    da_id = serializers.CharField(read_only=True)
    request_approval = serializers.BooleanField(read_only=True)
    withdrawal_confirmation = serializers.BooleanField(read_only=True)
    replacement_order = serializers.BooleanField(read_only=True)
    order_approval = serializers.BooleanField(read_only=True)
    order_delivery = serializers.BooleanField(read_only=True)
    last_status = serializers.CharField(read_only=True)
    request_approval_date = serializers.DateField(read_only=True)
    withdrawal_date = serializers.DateField(read_only=True)
    withdrawal_approval_date = serializers.DateField(read_only=True)
    order_date = serializers.DateField(read_only=True)
    order_approval_date = serializers.DateField(read_only=True)
    delivery_date = serializers.DateField(read_only=True)
    # request list (withdrawal requested products)
    request_list = WithdrawalRequestListSerializer(many=True)
    class Meta:
        model = WithdrawalInfo
        fields = [
            'invoice_no','invoice_type', 'mio_id', 'rm_id', 'da_id', 'depot_id', 'route_id', 'partner_id',
            'request_approval', 'withdrawal_confirmation', 'replacement_order',
            'order_approval', 'order_delivery', 'last_status', 'request_date',
            'request_approval_date', 'withdrawal_date', 'withdrawal_approval_date',
            'order_date', 'order_approval_date', 'delivery_date', 'last_status', 'request_list'
        ]
    
    def create(self, validated_data):
        """
        Create a new withdrawal request.
        
        Args:
            validated_data (dict): A dictionary containing validated data for creating the withdrawal request.
        
        Returns:
            WithdrawalInfo: The created withdrawal request instance.
        """
        requests_data = validated_data.pop('request_list')
        info = WithdrawalInfo.objects.create(**validated_data)
        for request_data in requests_data:
            WithdrawalRequestList.objects.create(invoice_id=info, **request_data)
        return info
    
    def update(self, instance, validated_data):
        """
        Update an existing withdrawal request.

        Args:
            instance (WithdrawalInfo): The existing withdrawal request instance to update.
            validated_data (dict): A dictionary containing validated data for updating the withdrawal request.

        Returns:
            WithdrawalInfo: The updated withdrawal request instance.
        """
        requests_data = validated_data.pop('request_list',[])
        
        # request list update 
        # Get the existing items and create a dictionary for efficient lookup
        existing_items = WithdrawalRequestList.objects.filter(invoice_id=instance)
        existing_items_dict = {
            (item.expire_date, item.pack_qty, item.strip_qty, item.unit_qty, item.net_val): item
            for item in existing_items
        }
        
        # Update existing items and create new items
        new_items = set()
        for item in requests_data:
            key = (
                item['expire_date'],
                item['pack_qty'],
                item['strip_qty'],
                item['unit_qty'],
                item['net_val']
            )
            new_items.add(key)
            
            existing_item = existing_items_dict.get(key)
            if existing_item:
                for attr, value in item.items():
                    setattr(existing_item, attr, value)
                existing_item.save()
            else:
                WithdrawalRequestList.objects.create(invoice_id=instance, **item)
        
        # Delete removed items
        for key, item in existing_items_dict.items():
            if key not in new_items:
                item.delete()
        
        # Return the updated instance
        return instance
    
class WithdrawalSerializer(serializers.ModelSerializer):
    withdrawal_list = WithdrawalListSerializer(many=True, read_only=True)
    class Meta:
        model = WithdrawalInfo
        fields = '__all__'
        read_only_fields = ('withdrawal_list',)

class DaAssignSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalInfo
        fields = ['da_id']
    