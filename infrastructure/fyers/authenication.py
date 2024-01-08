import time,os
from datetime import datetime
from fyers_api import fyersModel
from fyers_api import accessToken
from fyers_api.Websocket import ws
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
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
from servers.server_settings import chromedriver, token_dir


def genereate_token():
    fyer_access_token = ''
    try:
        service_object = Service(executable_path=chromedriver)
        """
        browserOpts = webdriver.ChromeOptions()
        browserOpts.binary_location = chromedriver
        service_object = Service(executable_path=chromedriver)
        browserPrefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
        browserOpts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        browserOpts.add_experimental_option("prefs", browserPrefs)
        browserOpts.add_experimental_option("detach", True)
        browserOpts.add_argument("--disable-single-click-autofill")
        browserOpts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        browser = webdriver.Chrome(options=browserOpts, service=service_object)
        browser.get("https://www.google.com")
        """
        session=accessToken.SessionModel(client_id=app_id, secret_key=secret_key, redirect_uri=redirect_uri, response_type="code", state='aaaaaa', grant_type = "authorization_code")
        # Hit the auth api
        auth_code_url = session.generate_authcode()
        print(auth_code_url)
        #browser = webdriver.Chrome(options=chrome_options)
        browser = webdriver.Chrome(service=service_object)
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

def get_access_token_0():
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

def get_access_token():
    token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkuZnllcnMuaW4iLCJpYXQiOjE3MDQ2NTg4ODIsImV4cCI6MTcwNDY3MzgyMiwibmJmIjoxNzA0NjU4ODgyLCJhdWQiOlsieDowIiwieDoxIiwieDoyIiwiZDoxIiwiZDoyIiwieDoxIiwieDowIl0sInN1YiI6ImFjY2Vzc190b2tlbiIsImF0X2hhc2giOiJnQUFBQUFCbG13ZkM4MWk4RllMeGZ0SUlHa2ZpckVrTDdHbFRXNVRTd3FubVhFU0JRTEQ5Y1JQak1JN2oxcUUzTXZOdllfLUl2OFgxNUZjb19JMDlTYWwyRGNLSWpxN2JjTUNuZUY5ZEltZUx3eU9fRWtTMHdxdz0iLCJkaXNwbGF5X25hbWUiOiJCQVNBTlQgU0FIT08iLCJvbXMiOiJLMSIsImhzbV9rZXkiOiJlOWEyNTdmZjAzN2VhYzc4ODkxZjMwOTk0ZTVmMDc1NzQ5ZTdhMjBjNDcxOTQ2M2Y2NjdiYWU1MyIsImZ5X2lkIjoiREIwMDI1NCIsImFwcFR5cGUiOjEwMCwicG9hX2ZsYWciOiJOIn0.ugh27sh5BFX6MbrXC9YvWUp9Once80TTQBFcXzzPqJA'
    return token
    auth_code = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJhcGkubG9naW4uZnllcnMuaW4iLCJpYXQiOjE3MDQ2NTg4MzEsImV4cCI6MTcwNDY4ODgzMSwibmJmIjoxNzA0NjU4MjMxLCJhdWQiOiJbXCJ4OjBcIiwgXCJ4OjFcIiwgXCJ4OjJcIiwgXCJkOjFcIiwgXCJkOjJcIiwgXCJ4OjFcIiwgXCJ4OjBcIl0iLCJzdWIiOiJhdXRoX2NvZGUiLCJkaXNwbGF5X25hbWUiOiJEQjAwMjU0Iiwib21zIjoiSzEiLCJoc21fa2V5IjoiZTlhMjU3ZmYwMzdlYWM3ODg5MWYzMDk5NGU1ZjA3NTc0OWU3YTIwYzQ3MTk0NjNmNjY3YmFlNTMiLCJub25jZSI6IiIsImFwcF9pZCI6IjdRS0xFMUc0WDMiLCJ1dWlkIjoiMTljNWViNTMzMmM5NDRkNmEyNWU2M2UwZmU4Mjg1ZTAiLCJpcEFkZHIiOiIwLjAuMC4wIiwic2NvcGUiOiIifQ.VLdf8N7T2NZD_FKgQ7NfwuaPm22JHUC5JRykZptBMb8'
    session = accessToken.SessionModel(client_id=app_id, secret_key=secret_key, redirect_uri=redirect_uri,
                                       response_type="code", state='aaaaaa', grant_type="authorization_code")
    session.set_token(auth_code)
    response = session.generate_token()

    print(response)
    fyer_access_token = response["access_token"]
    print(fyer_access_token)
    return fyer_access_token
