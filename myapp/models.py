from django.utils import timezone
from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=100, default='')
    brand = models.CharField(max_length=100, default='')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    protected_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    platform = models.CharField(max_length=50, default='')
    condition = models.CharField(max_length=50, default='')
    payment_options = models.CharField(max_length=200, default='')
    views = models.IntegerField(default=0)
    uploaded_date = models.DateTimeField(default=timezone.now) 
    currency_sign = models.CharField(max_length=5, default='')
    rating = models.FloatField(default=0.0)
    total_rating = models.IntegerField(default=0)
    description = models.TextField(default='')
    p_id = models.CharField(max_length=100, unique=True, default='')  # Added unique string field

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image_url = models.URLField()
