from fyers_apiv3 import fyersModel
from infrastructure.fyers.settings import app_id, secret_key, redirect_uri
# Replace these values with your actual API credentials
import webbrowser
import pygetwindow as gw
import pyautogui
import time

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

response_type = "code"
state = "sample_state"
grant_type = "authorization_code"

def get_access_token():
    # Create a session model with the provided credentials
    appSession = fyersModel.SessionModel(
        client_id=app_id,
        secret_key=secret_key,
        redirect_uri=redirect_uri,
        response_type=response_type,
        state = state,
        grant_type = grant_type
    )

    generateTokenUrl = appSession.generate_authcode()
    from selenium import webdriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get(generateTokenUrl)
    webbrowser.open(generateTokenUrl, new=1)
    time.sleep(10)
    print(driver.current_url)
    auth_code = driver.current_url.split('auth_code=')[1].split('&state')[0]
    print(auth_code)


    webbrowser.open(generateTokenUrl, new=1)
    browser_window = gw.getAllTitles()
    from selenium import webdriver
    driver = webdriver.Chrome()
    print(driver.current_url)

    print(browser_window)
    browser_window.activate()
    pyautogui.hotkey('ctrl', 'l')
    time.sleep(2)
    pyautogui.hotkey('ctrl', 'c')
    keyboard.press_and_release('ctrl + c')
    time.sleep(0.5)
    url = pyperclip.paste()
    print(url)

    #auth_code = webbrowser.current_url.split('auth_code=')[1].split('&state')[0]
    tt = webbrowser.get()
    print(tt.__dict__.keys())
    print(dir([object]))
    object_methods = [method_name for method_name in dir(object)
                      if callable(getattr(object, method_name))]
    print(object_methods)
    appSession.set_token(auth_code)
    response = appSession.generate_token()

    # Generate the auth code using the session model
    response = appSession.generate_authcode()

    # Print the auth code received in the response
    print(response)
    return response
