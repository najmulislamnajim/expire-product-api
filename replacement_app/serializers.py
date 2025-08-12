from rest_framework.serializers import ModelSerializer
from withdrawal_app.models import WithdrawalInfo

class AvailableReplacementListSerializer(ModelSerializer):
    class Meta:
        model = WithdrawalInfo
        fields = '__all__'