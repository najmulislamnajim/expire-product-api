from django.db import models
from withdrawal_app.models import WithdrawalInfo

# Create your models here.            
class ReplacementList(models.Model):
    invoice = models.ForeignKey(WithdrawalInfo, on_delete=models.CASCADE, related_name='replacement_list')
    matnr = models.CharField(max_length=40)
    batch = models.CharField(max_length=40, null=True, blank=True)
    pack_qty = models.IntegerField(default=0)
    unit_qty = models.IntegerField(default=0) # TAB/CAP/AMP
    net_val = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.invoice} replacement list'
    
    class Meta:
        db_table = 'expr_replacement_list'
        verbose_name = 'Replacement List'
        verbose_name_plural = 'Replacement List'