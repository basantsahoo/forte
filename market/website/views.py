from datetime import datetime
from rest_framework_simplejwt.tokens import RefreshToken
from website.models import User, UserPasswords
from website.serializers import TradeSerializer


from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.db.models import Max,F,Func, Value, CharField
from django.db.models import Q
from django.utils import timezone

from django.http import JsonResponse


import requests
import json
import pandas as pd
from lxml import etree,html
import numpy as np
from bs4 import BeautifulSoup
import time
from urllib.request import urlopen
from dateutil import parser
from datetime import datetime,date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy.types import  DATE
from options.models import Chain
from options.serializers import ChainDetailsSerializer
from helper.utils import get_nse_index_symbol
from db.db_engine import get_db_engine
from rest_framework.permissions import IsAuthenticated


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return "JWT " + str(refresh.access_token)


class UserLoginView(APIView):
    def post(self, request):
        if request.data:
            email = request.data.get("email", None)
            password = request.data.get("password", None)
            if email and password:
                user_obj = User.objects.filter(email__iexact=email)
                login_user_obj = user_obj.first()
                if not login_user_obj:
                    return JsonResponse(
                        {"message": "User Account doesn't exist", "status": False},
                        status=400,
                    )

                user_pass_obj = UserPasswords.objects.filter(
                    Q(user_id=login_user_obj.user_id)
                    & Q(start_date__lte=timezone.now())
                    & Q(end_date__gte=timezone.now())
                ).first()
                if user_pass_obj:
                    password_status = user_pass_obj.check_password(password)
                    print(password_status)
                    if password_status:
                        try:
                            # get_user_attr = ('user_id', 'email', 'first_name','username', 'last_name', 'phone_number', 'activated','is_superuser')
                            # For Free Trial
                            get_user_attr = (
                                "user_id",
                                "email",
                                "first_name",
                                "username",
                                "last_name",
                                "phone_number",
                                "is_active",
                                "is_superuser",
                                "created_on",
                            )
                            user_data = user_obj.values(*get_user_attr).first()

                        except Exception as e:
                            print(e)
                        meta_data = request.META if request else None
                        token = get_tokens_for_user(login_user_obj)
                        return JsonResponse(
                            {"user": user_data, "token": token, "status": True},
                            status=200,
                        )
                    else:
                        return JsonResponse(
                            {"message": "Incorrect user id / password", "status": False},
                            status=400,
                        )

                return JsonResponse(
                    {"message": "User Account doesn't exist", "status": False},
                    status=400,
                )
        return JsonResponse({"message": "Bad Request"}, status=400)


class OrderView(APIView):
    def post(self, request):
        print(request.data)
        if request.data:
            option_data = request.data
            #option_data['order_time'] = datetime.strptime(request.data['order_time'], '%Y-%m-%d %H:%M:%S')
            serializer = TradeSerializer(data=option_data)
            #print(serializer)
            print(serializer.is_valid())
            print(serializer.errors)
            try:
                serializer.save()
                return Response(serializer.data)
            except Exception as e:
                logging.exception(
                    f"exception in creating order, exception is {e}"
                )

class TradeDates(APIView):
    def get(self, request):
        def get_trade_dates(symbol):
            symbol = get_nse_index_symbol(symbol)
            engine = get_db_engine()
            conn = engine.connect()
            qry = "select distinct date as trade_dates from daily_profile".format(symbol)
            df = pd.read_sql_query(qry, con=conn)
            conn.close()
            df['trade_dates'] = df['trade_dates'].apply(lambda x: x.strftime('%Y-%m-%d'))
            return df['trade_dates'].to_list()
        ticker = request.GET.get("ticker", None)
        result = get_trade_dates(ticker)
        return Response(
            {"message": "Trade Dates", 'trade_dates': result, "status": True},
            status=status.HTTP_200_OK,
        )
