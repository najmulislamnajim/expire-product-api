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
    request_list = WithdrawalRequestListSerializer(many=True)
    class Meta:
        model = WithdrawalInfo
        fields = '__all__'
    
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