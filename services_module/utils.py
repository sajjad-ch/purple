import random
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import requests
import json

import jdatetime

def is_valid_jalali_date(year, month, day):
    try:
        jdatetime.date(year, month, day)
        return True
    except ValueError:
        return False

def random_code():
    number_list = [x for x in range(10)]
    code = []
    for i in range(8):
        num = random.choice(number_list)
        code.append(num)

    code_string = "".join(str(item) for item in code)
    return code_string


def send_visit_notification(user_id, message):
    channel_layer = get_channel_layer()
    user_group = f"user_{user_id}"

    async_to_sync(channel_layer.group_send)(
        user_group,
        {
            "type": "visit_notification",
            "message": message,
        },
    )


def send_message():
    url = 'https://api.sms.ir/v1/send/verify'

    body = {
            "mobile": "9104627599",
            "templateId": 540146,
            "parameters": [
            {
                "name": "VERIFICATION",
                "value": "12345"
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



def sms_for_new_visiting_time_saloon(phone_number, saloon_name, date, customer):
    url = "https://api.sms.ir/v1/send/verify"
    if phone_number[0] == '0':
        new_phone_number = phone_number[1:]
    else:
        new_phone_number = phone_number
    body = {
        "mobile": str(new_phone_number),
        "templateId": 749786,
        "parameters": [
            {
                "name": "SALOON",
                "value": str(saloon_name)
            },
            {
                "name": "DATE",
                "value": str(date)
            },
            {
                "name": "CUSTOMER",
                "value": str(customer)
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



def sms_for_new_visiting_time_artist(phone_number, artist_name, date, customer):
    url = "https://api.sms.ir/v1/send/verify"
    if phone_number[0] == '0':
        new_phone_number = phone_number[1:]
    else:
        new_phone_number = phone_number
    body = {
        "mobile": str(new_phone_number),
        "templateId": 190287,
        "parameters": [
            {
                "name": "ARTIST",
                "value": str(artist_name)
            },
            {
                "name": "DATE",
                "value": str(date)
            },
            {
                "name": "CUSTOMER",
                "value": str(customer)
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


def sms_for_result_of_appointment(phone_number, result, appointment_id, date, saloon, artist, customer):
    url = "https://api.sms.ir/v1/send/verify"
    if phone_number[0] == '0':
        new_phone_number = phone_number[1:]
    else:
        new_phone_number = phone_number
    body = {
        "mobile": str(new_phone_number),
        "templateId": 114040,
        "parameters": [
            {
                "name": "RESULT",
                "value": str(result)
            },
            {
                "name": "APPOINTMENTID",
                "value": str(appointment_id)
            },
                        {
                "name": "ARTIST",
                "value": str(artist)
            },
                        {
                "name": "DATE",
                "value": str(date)
            },
            {
                "name": "CUSTOMER",
                "value": str(customer)
            },
                        {
                "name": "SALOON",
                "value": str(saloon)
            },
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


def sms_for_reminding_deposit(phone_number, paying_url, saloon, artist, appointmet_id, customer, date):
    url = "https://api.sms.ir/v1/send/verify"
    if phone_number[0] == '0':
        new_phone_number = phone_number[1:]
    else:
        new_phone_number = phone_number
    body = {
        "mobile": str(new_phone_number),
        "templateId": 302725,
        "parameters": [
            {
                "name": "DEPOSIT",
                "value": str(paying_url)
            },
            {
                "name": "SALOON",
                "value": str(saloon)
            },
            {
                "name": "ARTIST",
                "value": artist
            },
            {
                "name": "APPOINTMENTID",
                "value": str(appointmet_id)
            },
            {
                "name": "CUSTOMER",
                "value": str(customer)
            },
            {
                "name": "DATE",
                "value": str(date)
            },
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



def sms_for_deposit_paid(phone_number, customer, appointmet_id, visit_date):
    url = "https://api.sms.ir/v1/send/verify"
    if phone_number[0] == '0':
        new_phone_number = phone_number[1:]
    else:
        new_phone_number = phone_number
    body = {
        "mobile": str(new_phone_number),
        "templateId": 302725,
        "parameters": [
            {
                "name": "CUSTOMER",
                "value": str(customer)
            },
            {
                "name": "APPOINTMENTID",
                "value": str(appointmet_id)
            },
            {
                "name": "DATE",
                "value": str(visit_date)
            },
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


def sms_for_unregistered_user(phone_number, customer):
    url = "https://api.sms.ir/v1/send/verify"
    if phone_number[0] == '0':
        new_phone_number = phone_number[1:]
    else:
        new_phone_number = phone_number
    body = {
        "mobile": str(new_phone_number),
        "templateId": 302725,
        "parameters": [
            {
                "name": "CUSTOMER",
                "value": str(customer)
            },
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