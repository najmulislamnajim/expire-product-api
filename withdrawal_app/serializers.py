from rest_framework import serializers
from withdrawal_app.models import WithdrawalList, WithdrawalRequestList, WithdrawalInfo

class WithdrawalRequestListSerializer(serializers.ModelSerializer):
    """
    Serializer for the WithdrawalRequestList model.
    
    This serializer is used to create a withdrawal request list.
    """
    class Meta:
        model = WithdrawalRequestList
        fields = '__all__'
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
        extra_kwargs = {
            'invoice_id': {'read_only': True}
        }
        
class WithdrawalRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for the WithdrawalInfo model.
    
    This serializer is used to create a withdrawal request.
    """
    # These fields are both readable and writable
    mio_id = serializers.IntegerField()
    rm_id = serializers.IntegerField()
    da_id = serializers.IntegerField()
    depot_id = serializers.IntegerField()
    route_id = serializers.IntegerField()
    partner_id = serializers.IntegerField()

    # Read-only fields
    request_date = serializers.DateField(read_only=True)
    request_approval = serializers.BooleanField(read_only=True)
    withdrawal_confirmation = serializers.BooleanField(read_only=True)
    replacement_order = serializers.BooleanField(read_only=True)
    order_approval = serializers.BooleanField(read_only=True)
    order_delivery = serializers.BooleanField(read_only=True)
    last_status = serializers.CharField(read_only=True)
    request_date = serializers.DateField(read_only=True)
    request_approval_date = serializers.DateField(read_only=True)
    withdrawal_date = serializers.DateField(read_only=True)
    withdrawal_approval_date = serializers.DateField(read_only=True)
    order_date = serializers.DateField(read_only=True)
    order_approval_date = serializers.DateField(read_only=True)
    delivery_date = serializers.DateField(read_only=True)
    last_status = serializers.CharField(read_only=True)
    # request list (withdrawal requested products)
    request_list = WithdrawalRequestListSerializer(many=True)
    class Meta:
        model = WithdrawalInfo
        fields = [
            'mio_id', 'rm_id', 'da_id', 'depot_id', 'route_id', 'partner_id',
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