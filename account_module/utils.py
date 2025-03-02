import requests
import json
import random


def send_verification_code(phone_number, code):
    return True
    # if phone_number[0] == '0':
    #     phone_number = phone_number[1:]
    # url = 'https://api.sms.ir/v1/send/verify'
    # body = {
    #         "mobile": phone_number,
    #         "templateId": 540146,
    #         "parameters": [
    #         {
    #             "name": "VERIFICATION",
    #             "value": code
    #         }
    #     ]
    # }
    # res = requests.post(
    #     url=url,
    #     headers={
    #         'Content-Type': 'application/json',
    #         'Accept': 'text/plain',
    #         'x-api-key': 'ozglAKBlpBGrE7qRS8z67K4GzQE3z6riwlj6ZLHU1TCgrWLo'
    #     },
    #     data=json.dumps(body)
    # )


def random_number():
    code = ''
    for i in range(5):
        code += str(random.randint(0, 9))
    return code
