from rest_framework import serializers
from withdrawal_app.models import WithdrawalInfo
from .models import ReplacementList

class AvailableReplacementListSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    class Meta:
        model = WithdrawalInfo
        fields = '__all__'
        read_only_fields = ['total_amount']

class ReplacementListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReplacementList
        fields = ['matnr', 'batch', 'pack_qty', 'unit_qty', 'net_val']

class ReplacementApprovalListSerializer(serializers.ModelSerializer):
    replacement_list = ReplacementListSerializer(many=True, read_only=True)
    class Meta:
        model = WithdrawalInfo
        fields = '__all__'