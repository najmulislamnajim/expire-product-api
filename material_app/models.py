from django.db import models

# Create your models here.
class RplMaterial(models.Model):
    id = models.BigAutoField(primary_key=True)
    matnr = models.CharField(max_length=40)
    plant = models.CharField(max_length=4)
    sales_org = models.CharField(max_length=4)
    dis_channel = models.CharField(max_length=2)
    material_name = models.CharField(max_length=40, blank=True, null=True)
    producer_company = models.CharField(max_length=3, blank=True, null=True)
    team1 = models.CharField(max_length=3, blank=True, null=True)
    pack_size = models.TextField(blank=True, null=True)
    unit_tp = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    unit_vat = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    brand_name = models.CharField(max_length=255, blank=True, null=True)
    brand_description = models.CharField(max_length=255, blank=True, null=True)
    active = models.CharField(max_length=1, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'rpl_material'
        unique_together = (('matnr', 'plant', 'sales_org', 'dis_channel'),)