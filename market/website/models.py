from __future__ import unicode_literals
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from website.managers import UserManager
from django.db.models import JSONField
from django.contrib.auth.hashers import make_password, check_password

USER_TYPES = [("U1", "Paid User"), ("U2", "Test User")]
# Create your models here.

class User(AbstractUser):
    user_id = models.AutoField(primary_key=True)
    first_name = models.CharField(_("First Name"), max_length=50, null=True, blank=True)
    last_name = models.CharField(_("Last Name"), max_length=50, null=True, blank=True)
    email = models.EmailField(_("Email Address"), unique=True)
    phone_number = models.CharField(
        _("Phone Number"), max_length=13, blank=True, null=True
    )
    password = None
    username = models.CharField(_("Username"), max_length=500, null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    user_type = models.CharField(choices=USER_TYPES, max_length=200, null=True, blank=True)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        indexes = [models.Index(fields=["email"], name="user_email_idx")]

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        self.username = self.email
        super(User, self).save(*args, **kwargs)

    def __str__(self):
        return self.email

    class Meta:
        db_table = "user"




class UserPasswords(models.Model):
    user_id = models.IntegerField(null=True, blank=True)
    # user =  models.IntegerField(null=True, blank=True)
    start_date = models.DateTimeField(auto_now=True)
    end_date = models.DateTimeField(default=None, blank=True, null=True)
    password = models.CharField(max_length=200, null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    is_lock = models.BooleanField(default=False)
    last_active = models.BooleanField(default=True)

    def __str__(self):
        return self.password

    class Meta:
        unique_together = [["user_id", "start_date", "end_date"]]
        indexes = [models.Index(fields=["user_id"], name="user_password_idx")]

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def hash_password(self, raw_password):
        hash_password = make_password(raw_password)
        return hash_password

    def save(self, *args, **kwargs):
        super(UserPasswords, self).save(*args, **kwargs)

    class Meta:
        db_table = "user_password"


class Trades(models.Model):
    order_date = models.DateField()  # models.DateTimeField()
    order_time = models.DateTimeField()
    strat_id = models.CharField(max_length=20)
    signal_id = models.CharField(max_length=20)
    trigger_id =  models.IntegerField(null=True, blank=True)
    order_type = models.CharField(max_length=10)
    symbol = models.CharField(max_length=50)
    side = models.CharField(max_length=10)
    quantity = models.IntegerField()
    price = models.FloatField()
    product = models.CharField(max_length=10,null=True, blank=True)


    class Meta:
        indexes = [
            models.Index(fields=['order_date'])
        ]
