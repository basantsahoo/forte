"""market URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from market import views
from website.views import OrderView, TradeDates
from django.conf.urls import include

#from django.conf.urls import url

from django.contrib.auth.hashers import make_password
print("Hashed password is:", make_password("BMW*112"))

urlpatterns = [
    #re_path(r'^admin/', include('admin_honeypot.urls', namespace='admin_honeypot')),
    #path('admin/', admin.site.urls),
    #path('option_chain', views.OptionDataView.as_view()),
    path('order', OrderView.as_view()),
    path('trade_date', TradeDates.as_view(), name="trade_date"),
    path("auth/", include("website.urls")),
    #url(r'^option_chain', views.OptionDataView.as_view(), name='option_chain'),
]
