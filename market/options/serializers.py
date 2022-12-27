from rest_framework import serializers
from options.models import Chain


class ChainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chain
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(ChainSerializer, self).__init__(*args, **kwargs)

    def create(self, validated_data):
        _instance = super().create(validated_data)
        return _instance


class ChainDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chain
        fields = "__all__"
