from django.db import models

# Create your models here.
class WithdrawalInfo(models.Model):
    """
    Model representing withdrawal information for a specific process.

    This model stores details about withdrawal requests, approvals, and delivery statuses,
    including identifiers for related entities (e.g., depot, route, partner) and key dates
    for the withdrawal process. It also generates a unique invoice number based on the
    instance ID.
    """
    class Status(models.TextChoices):
        REQUEST = 'request', 'Request'
        WITHDRAWAL = 'withdrawal', 'Withdrawal'
        DELIVERY = 'delivery', 'Delivery'
    class InvoiceType(models.TextChoices):
        WITHDRAWAL = 'EXP', 'Expired'
        REPLACEMENT = 'GEN', 'General'
    id = models.BigAutoField(primary_key=True)
    invoice_no = models.CharField(max_length=12, unique=True, blank=True, null=True)
    invoice_type = models.CharField(max_length=12, choices=InvoiceType.choices, default=InvoiceType.WITHDRAWAL)
    mio_id = models.CharField(max_length=40)
    rm_id = models.CharField(max_length=40)
    da_id = models.CharField(max_length=40, null=True, blank=True)
    depot_id = models.CharField(max_length=40, null=True, blank=True)
    route_id = models.CharField(max_length=40, null=True, blank=True)
    partner_id = models.CharField(max_length=40)
    request_approval = models.BooleanField(default=False)
    withdrawal_confirmation = models.BooleanField(default=False)
    replacement_order = models.BooleanField(default=False)
    order_approval = models.BooleanField(default=False)
    order_delivery = models.BooleanField(default=False)
    request_date = models.DateField(null=True, blank=True)
    request_approval_date = models.DateField(null=True, blank=True)
    withdrawal_date = models.DateField(null=True, blank=True)
    withdrawal_approval_date = models.DateField(null=True, blank=True)
    order_date = models.DateField(null=True, blank=True) 
    order_approval_date = models.DateField(null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    last_status = models.CharField(max_length=40, choices=Status.choices, default=Status.REQUEST)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        """
        Overrides the default save method to generate a unique invoice number.

        If the `invoice_no` field is not set, it generates an invoice number in the format
        '50' followed by the instance ID padded to 8 digits (e.g., '5000000001'). The
        generated invoice number is saved to the database.
        """
        super().save(*args, **kwargs)
        if not self.invoice_no:
            self.invoice_no = f'50{self.id:08d}'
            super().save(update_fields=['invoice_no'])
            
    def __str__(self):
        return f'{self.invoice_no}'
    
    class Meta:
        db_table = 'expr_withdrawal_info'
        verbose_name = 'Withdrawal Info'
        verbose_name_plural = 'Withdrawal Info'
        
        
class WithdrawalRequestList(models.Model):
    """
    Model representing a list of items in a withdrawal request.

    This model stores details about the items requested for withdrawal, including
    material number, batch, quantities (pack, strip, unit), and net value. It is linked
    to the `WithdrawalInfo` model via a foreign key.
    """
    invoice_id = models.ForeignKey(WithdrawalInfo, on_delete=models.CASCADE, related_name='request_list')
    matnr = models.CharField(max_length=40)
    batch = models.CharField(max_length=40)
    pack_qty = models.IntegerField(default=0)
    strip_qty = models.IntegerField(default=0)
    unit_qty = models.IntegerField(default=0)
    net_val = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    expire_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.invoice_id} request list'
    
    class Meta:
        db_table = 'expr_request_list'
        verbose_name = 'Withdrawal Request List'
        verbose_name_plural = 'Withdrawal Request List'
        
        
class WithdrawalList(models.Model):
    """
    Model representing a list of items in a withdrawal.

    This model stores details about the items actually withdrawn, including material
    number, batch, quantities (pack, strip, unit), and net value. It is linked to the
    `WithdrawalInfo` model via a foreign key.
    """
    invoice_id = models.ForeignKey(WithdrawalInfo, on_delete=models.CASCADE, related_name='withdrawal_list')
    matnr = models.CharField(max_length=40)
    batch = models.CharField(max_length=40)
    pack_qty = models.IntegerField(default=0)
    strip_qty = models.IntegerField(default=0)
    unit_qty = models.IntegerField(default=0)
    net_val = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.invoice_id} request list'
    
    class Meta:
        db_table = 'expr_withdrawal_list'
        verbose_name = 'Withdrawal List'
        verbose_name_plural = 'Withdrawal List'
    
