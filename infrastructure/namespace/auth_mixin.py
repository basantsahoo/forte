import json
from config import allowed_apps, rest_api_url
import requests


class AuthMixin:
    def is_authenticated(self, auth):
        app_id = auth.get('internal_app_id', '')
        if app_id in allowed_apps:
            return True
        token = auth.get('token', '')
        token = token.replace('JWT ', '')
        headers = {'Content-Type': 'application/json'}
        data = json.dumps({"token": token})
        response = requests.post(rest_api_url + 'auth/verify-token', data=data, headers = headers)
        if response.status_code == 200:
            return True
        else:
            return False
