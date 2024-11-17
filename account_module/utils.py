import requests
import random


def token():
    API_KEY = ""
    SECURITY_KEY = ""
    url = "https://RestfulSms.com/api/Token"

    response = requests.post(url, data={
        "UserApiKey": API_KEY,
        "SecretKey": SECURITY_KEY
    })

    if response.status_code == 201:
        json_date = response.json()
        return json_date["TokenKey"]
    else:
        return "Not successfully requested"


def random_code():
    number_list = [x for x in range(10)]
    code = []
    for i in range(5):
        num = random.choice(number_list)
        code.append(num)

    code_string = "".join(str(item) for item in code)
    return code_string


def send_verify_code_SMS(number, code):
    # token_key = token()
    # url = "https://RestfulSms.com/api/VerificationCode"
    #
    # response = requests.post(url, data={
    #     "Code": code,
    #     "MobileNumber": number
    # },
    # headers={
    #     'x-sms-ir-secure-token':token_key
    #     })
    #
    # return response.status_code
    return True


def send_notifying_SMS(message, number, url):
    # token_key = token()
    # url = "https://RestfulSms.com/api/VerificationCode"
    #
    # response = requests.post(url, data={
    #     "Message": message,
    #     "MobileNumber": number,
    #     "url": url
    # },
    # headers={
    #     'x-sms-ir-secure-token': token_key
    # })
    #
    # return response.status_code
    return True
