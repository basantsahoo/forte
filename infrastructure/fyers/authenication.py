import time,os
from datetime import datetime
from fyers_api import fyersModel
from fyers_api import accessToken
from fyers_api.Websocket import ws
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from infrastructure.fyers.settings import (
    app_id,
    secret_key,
    redirect_uri,
    user_name,
    pass_word,
    pan,
    pin,
    totp_key
)
import pyotp
from servers.server_settings import chromedriver,token_dir


def genereate_token():
    fyer_access_token = ''
    try:
        session=accessToken.SessionModel(client_id=app_id, secret_key=secret_key, redirect_uri=redirect_uri, response_type="code", state='aaaaaa', grant_type = "authorization_code")
        # Hit the auth api
        auth_code_url = session.generate_authcode()
        print(auth_code_url)
        browser = webdriver.Chrome(chromedriver)
        browser.get(auth_code_url)
        time.sleep(4)
        # Client id screen
        username = browser.find_element(By.ID, "fy_client_id")
        username.send_keys(user_name)
        browser.find_element(By.ID, "clientIdSubmit").click()
        # browser.find_element(By.cssSelector("[type='submit']")).click()
        time.sleep(4)
        # TOTP screen
        totp = pyotp.TOTP(totp_key)
        totp = totp.now()
        print("totp=========", totp)
        browser.find_element_by_xpath("//form[@id='confirmOtpForm']/div/input[@id='first']").send_keys(totp[0])
        browser.find_element_by_xpath("//form[@id='confirmOtpForm']/div/input[@id='second']").send_keys(totp[1])
        browser.find_element_by_xpath("//form[@id='confirmOtpForm']/div/input[@id='third']").send_keys(totp[2])
        browser.find_element_by_xpath("//form[@id='confirmOtpForm']/div/input[@id='fourth']").send_keys(totp[3])
        browser.find_element_by_xpath("//form[@id='confirmOtpForm']/div/input[@id='fifth']").send_keys(totp[4])
        browser.find_element_by_xpath("//form[@id='confirmOtpForm']/div/input[@id='sixth']").send_keys(totp[5])
        time.sleep(1)
        browser.find_element_by_xpath("//button[@id='confirmOtpSubmit']").click()
        time.sleep(3)
        # PIN screen
        digit1 = browser.find_element_by_xpath('/html/body/section[8]/div[3]/div[3]/form/div[2]/input[1]')
        digit1.click()
        digit1.send_keys(int(pin[0]))
        digit2 = browser.find_element_by_xpath('/html/body/section[8]/div[3]/div[3]/form/div[2]/input[2]')
        digit2.click()
        digit2.send_keys(int(pin[1]))
        digit3 = browser.find_element_by_xpath('/html/body/section[8]/div[3]/div[3]/form/div[2]/input[3]')
        digit3.click()
        digit3.send_keys(int(pin[2]))
        digit4 = browser.find_element_by_xpath('/html/body/section[8]/div[3]/div[3]/form/div[2]/input[4]')
        digit4.click()
        digit4.send_keys(int(pin[3]))
        print('completed 1')
        time.sleep(2)
        browser.find_element(By.ID, "verifyPinSubmit").click()
        print('completed 2')
        time.sleep(3)
        # Now get auth_code
        auth_code = browser.current_url.split('auth_code=')[1].split('&state')[0]
        print('completed 3')
        time.sleep(1)
        browser.close()
        browser.quit()
        session.set_token(auth_code)
        response = session.generate_token()
        fyer_access_token = response["access_token"]
        #print(response)
        #print(fyer_access_token)

    except Exception as e:
        print(e)
    f = open(token_dir + "token.txt", "w")
    f.write(fyer_access_token)
    f.close()

    #return fyer_access_token

def get_access_token():
    token = None
    try:
        fl = token_dir + "token.txt"
        t = datetime.fromtimestamp(os.path.getmtime(fl))
        hours = divmod((datetime.now() - t).total_seconds(), 3600)
        print(hours)
        if hours[0] >= 3:
            os.remove(fl)
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
