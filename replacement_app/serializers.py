from rest_framework import serializers
from withdrawal_app.models import WithdrawalInfo

class AvailableReplacementListSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    class Meta:
        model = WithdrawalInfo
        fields = '__all__'
        read_only_fields = ['total_amount']