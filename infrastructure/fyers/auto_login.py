import os
from datetime import datetime
import json
import requests
from urllib import parse
import sys
from infrastructure.fyers.settings import (
    app_id,
    secret_key,
    redirect_uri,
    user_name,
    pin,
    totp_key
)
import pyotp
import hashlib
from servers.server_settings import token_dir
# https://github.com/FyersDev/fyers-api-sample-code/blob/sample_v3/v3/python/login/auto_login_totp.py

# Client Info (ENTER YOUR OWN INFO HERE!! Data varies from users and app types)
FY_ID = user_name
APP_ID_TYPE = "2"  # Keep default as 2, It denotes web login
REDIRECT_URI = "https://trade.fyers.in/api-login/redirect-uri/index.html"  # Redirect url from the app.
APP_TYPE = "100"

# API endpoints
BASE_URL = "https://api-t2.fyers.in/vagator/v2"
BASE_URL_2 = "https://api-t1.fyers.in/api/v3"
URL_SEND_LOGIN_OTP = BASE_URL + "/send_login_otp"
URL_VERIFY_TOTP = BASE_URL + "/verify_otp"
URL_VERIFY_PIN = BASE_URL + "/verify_pin"
URL_TOKEN = BASE_URL_2 + "/token"
URL_VALIDATE_AUTH_CODE = BASE_URL_2 + "/validate-authcode"

SUCCESS = 1
ERROR = -1


def send_login_otp(fy_id, app_id):
    try:
        payload = {
            "fy_id": fy_id,
            "app_id": app_id
        }

        result_string = requests.post(url=URL_SEND_LOGIN_OTP, json=payload)
        if result_string.status_code != 200:
            return [ERROR, result_string.text]

        result = json.loads(result_string.text)
        request_key = result["request_key"]

        return [SUCCESS, request_key]

    except Exception as e:
        return [ERROR, e]


def verify_totp(request_key, totp):
    try:
        payload = {
            "request_key": request_key,
            "otp": totp
        }

        result_string = requests.post(url=URL_VERIFY_TOTP, json=payload)
        if result_string.status_code != 200:
            return [ERROR, result_string.text]

        result = json.loads(result_string.text)
        request_key = result["request_key"]

        return [SUCCESS, request_key]

    except Exception as e:
        return [ERROR, e]


def verify_PIN(request_key, pin):
    try:
        payload = {
            "request_key": request_key,
            "identity_type": "pin",
            "identifier": pin
        }

        result_string = requests.post(url=URL_VERIFY_PIN, json=payload)
        if result_string.status_code != 200:
            return [ERROR, result_string.text]

        result = json.loads(result_string.text)
        access_token = result["data"]["access_token"]

        return [SUCCESS, access_token]

    except Exception as e:
        return [ERROR, e]


def token(fy_id, app_id, redirect_uri, app_type, access_token):
    try:
        payload = {
            "fyers_id": fy_id,
            "app_id": app_id,
            "redirect_uri": redirect_uri,
            "appType": app_type,
            "code_challenge": "",
            "state": "sample_state",
            "scope": "",
            "nonce": "",
            "response_type": "code",
            "create_cookie": True
        }
        headers = {'Authorization': f'Bearer {access_token}'}

        result_string = requests.post(
            url=URL_TOKEN, json=payload, headers=headers
        )

        if result_string.status_code != 308:
            return [ERROR, result_string.text]

        result = json.loads(result_string.text)
        url = result["Url"]
        auth_code = parse.parse_qs(parse.urlparse(url).query)['auth_code'][0]

        return [SUCCESS, auth_code]

    except Exception as e:
        return [ERROR, e]


def validate_authcode(app_id_hash, auth_code):
    try:
        payload = {
            "grant_type": "authorization_code",
            "appIdHash": app_id_hash,
            "code": auth_code,
        }

        result_string = requests.post(url=URL_VALIDATE_AUTH_CODE, json=payload)
        if result_string.status_code != 200:
            return [ERROR, result_string.text]

        result = json.loads(result_string.text)
        access_token = result["access_token"]

        return [SUCCESS, access_token]

    except Exception as e:
        return [ERROR, e]

def genereate_token():
    fyer_access_token = ''
    try:
        send_otp_result = send_login_otp(fy_id=FY_ID, app_id=APP_ID_TYPE)
        if send_otp_result[0] != SUCCESS:
            print(f"send_login_otp failure - {send_otp_result[1]}")
            sys.exit()
        else:
            print("send_login_otp success")

        request_key = send_otp_result[1]
        if send_otp_result[0] != SUCCESS:
            return ''
        totp = pyotp.TOTP(totp_key).now()
        verify_totp_result = verify_totp(request_key=request_key, totp=totp)
        if verify_totp_result[0] != SUCCESS:
            print(f"verify_totp_result failure - {verify_totp_result[1]}")
            sys.exit()
        else:
            print("verify_totp_result success")

        request_key_2 = verify_totp_result[1]
        verify_pin_result = verify_PIN(request_key=request_key_2, pin=pin)

        if verify_pin_result[0] != SUCCESS:
            print(f"verify_pin_result failure - {verify_pin_result[1]}")
            sys.exit()
        else:
            print("verify_pin_result success")

        token_result = token(
            fy_id=FY_ID, app_id=app_id.split("-")[0], redirect_uri=redirect_uri, app_type=APP_TYPE,
            access_token=verify_pin_result[1]
        )
        if token_result[0] != SUCCESS:
            print(f"token_result failure - {token_result[1]}")
            sys.exit()
        else:
            print("token_result success")


        # Step 6 - Get API V2 access token from validating auth code
        auth_code = token_result[1]
        m = hashlib.sha256()
        string_to_hash = app_id + ":" + secret_key
        string_to_hash = string_to_hash.encode('utf-8')
        m.update(string_to_hash)
        app_id_hash =  m.hexdigest()

        validate_authcode_result = validate_authcode(
            app_id_hash=app_id_hash, auth_code=auth_code
        )
        #print(validate_authcode_result)
        fyer_access_token = validate_authcode_result[1]
    except:
        pass
    f = open(token_dir + "token.txt", "w")
    f.write(fyer_access_token)
    f.close()



def get_access_token():
    token = None
    try:
        fl = token_dir + "token.txt"
        t = datetime.fromtimestamp(os.path.getmtime(fl))
        hours = divmod((datetime.now() - t).total_seconds(), 3600)
        if hours[0] >= 3:
            os.remove(fl)
        else:
            f = open(fl, "r")
            token = f.read()
            f.close()
    except Exception as e:
        print(e)
    if token:
        return token
    else:
        genereate_token()
        return get_access_token()
