from rest_framework import serializers
from website.models import Trades


class TradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trades
        fields = "__all__"


class TradeDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trades
        fields = "__all__"
