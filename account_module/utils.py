import requests
import json
import random


def send_verification_code(phone_number, code):
    url = 'https://api.sms.ir/v1/send/verify'

    body = {
            "mobile": str(phone_number),
            "templateId": 540146,
            "parameters": [
            {
                "name": "VERIFICATION",
                "value": str(code)
            }
        ]
    }

    res = requests.post(
        url=url,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'text/plain',
            'x-api-key': 'sOFaP4ySGKroLlvf1S7TMFSbkupKrA9D9x6nfvHITo9mfcOB'
        },
        data=json.dumps(body)
    )

    print(res.text)


def random_number():
    code = ''
    for i in range(5):
        code += str(random.randint(0, 9))
    return code
