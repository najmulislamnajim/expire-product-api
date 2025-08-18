from rest_framework import serializers
from withdrawal_app.models import WithdrawalInfo, WithdrawalRequestList, WithdrawalList
from .models import ReplacementList
from datetime import date

class RequestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequestList
        fields = '__all__'
        
class WithdrawalListSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalList
        fields = '__all__'

class AvailableReplacementListSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    request_list = RequestListSerializer(many=True, read_only = True)
    withdrawal_list = WithdrawalListSerializer(many=True, read_only = True)
    partner_name = serializers.CharField(default="")
    customer_address = serializers.CharField(default="")
    mio_name = serializers.CharField(default="")
    class Meta:
        model = WithdrawalInfo
        fields = '__all__'
        read_only_fields = ['total_amount']  

class ReplacementListSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(max_length=150, default="")
    strip_qty = serializers.CharField(max_length=2, default=0)
    expire_date = serializers.DateField(default=date.today()) 
    batch = serializers.SerializerMethodField()
    class Meta:
        model = ReplacementList
        fields = ['matnr', 'batch', 'pack_qty', 'unit_qty', 'net_val', 'material_name', 'strip_qty', 'expire_date']
    def get_batch(self, obj):
        return ""

class ReplacementApprovalListSerializer(serializers.ModelSerializer):
    replacement_list = ReplacementListSerializer(many=True, read_only=True)
    partner_name = serializers.CharField(default="")
    customer_address = serializers.CharField(default="")
    mio_name = serializers.CharField(default="")
    class Meta:
        model = WithdrawalInfo
        fields = '__all__'