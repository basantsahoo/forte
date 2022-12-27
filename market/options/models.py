from django.db import models
from datetime import datetime

class Chain(models.Model):
    expiry_date = models.DateField() #models.DateTimeField()
    strike_price = models.IntegerField()
    ticker = models.CharField(max_length=50, null=True, blank=True)
    calls_oi = models.IntegerField()
    calls_change_oi = models.IntegerField()
    calls_iv = models.FloatField()
    calls_ltp = models.FloatField()
    calls_volume =  models.IntegerField()
    calls_buy_qty = models.IntegerField()
    calls_sell_qty = models.IntegerField()
    puts_oi = models.IntegerField()
    puts_change_oi = models.IntegerField()
    puts_iv = models.FloatField()
    puts_ltp = models.FloatField()
    puts_volume =  models.IntegerField()
    puts_buy_qty = models.IntegerField()
    puts_sell_qty = models.IntegerField()
    spot = models.FloatField()
    created_on = models.DateTimeField()
    
    class Meta:
        indexes = [
            models.Index(fields=['ticker', 'created_on'])
        ]

