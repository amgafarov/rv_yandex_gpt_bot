import json
import requests

__secret_key__ = "AQVN38CDRBlod2wbgEbrgemiKeDC8BZ88Ni_o3-1"
__secret_key_image__ = 'AQVN03F4BTXdVFcR81rjeCtGlTpK1Q1VCITJjudD'
__secret_key_speech__ = 'AQVNwY58QeOsASeRgoZ6i24Jt5R3ZcsaMkkIkqXR'
__storage_id__ = "b1gjtlqofdt5mu5io6a9"
__url__ = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'
__url_image__ = 'https://ocr.api.cloud.yandex.net/ocr/v1/recognizeTextAsync'

DEFAULT_SYSTEM_PROMT = ('Ты — профессиональный журналист интернет-издания «Реальное время». Перепиши этот текст в '
                    'новость для сайта. Придумай заголовок, который содержит подлежащее и сказуемое. '
                    'Сказуемое должно быть глаголом. Не добавляй ничего от себя. '
                    'Не используй страдательный залог и формулировки по типу «было установлено», «было произведено» '
                    'и так далее. Если в тексте упоминается Татарстан, то в своей новости сделай акцент на нем '
                    'и вынеси его в заголовок')

__system_promt__ = ('Ты — профессиональный журналист интернет-издания «Реальное время». Перепиши этот текст в '
                    'новость для сайта. Если в тексте упоминается Татарстан, сделай в новости акцент именно'
                    ' на нем. Новость должна состоять из заголовка, лида и далее не менее двух абзацев текста.'
                    'Сделай текст понятным и читаемым, но сохраняй информационный стиль. Опирайся только на ту '
                    'информацию, которая есть в тексте!')

__headers__ = {
    "Content-Type": "application/json",
    "Authorization": "Api-Key {}".format(__secret_key__)
}

__headers_image__ = {
    "Content-Type": "application/json",
    "Authorization": "Api-Key {}".format(__secret_key_image__),
    "x-folder-id": f"{__storage_id__}",
    'x-data-logging-enabled': 'false'
}


temp = 0.6


# Functions for admin
def admin_set_system_promt(system_promt_text=DEFAULT_SYSTEM_PROMT):
    global __system_promt__
    __system_promt__ = str(system_promt_text)


def admin_set_temp(new_temp) -> None:
    global temp
    temp = new_temp


def admin_get_temp() -> float:
    return temp


def create_promt(user_promt, admin_promt=__system_promt__):
    if len(str(user_promt)) == 0 or user_promt is None:
        return None

    return {
        "modelUri": "gpt://{}/yandexgpt/latest".format(__storage_id__),
        "completionOptions": {
            "stream": False,
            "temperature": temp,
            "maxTokens": "2000"
        },
        "messages": [
            {
                "role": "system",
                "text": admin_promt
            },
            {
                "role": "user",
                "text": user_promt
            }
        ]
    }


def get_response(promt=None, user_promt=None, admin_promt=None):
    if promt is None and user_promt is None:
        return None

    if promt is None:
        if admin_promt is None:
            promt = create_promt(user_promt=user_promt)
        else:
            promt = create_promt(user_promt=user_promt, admin_promt=admin_promt)

    return requests.post(url=__url__, headers=__headers__, json=promt)


def get_text_from_image_id(base64_image, image_type):
    img_json = {
        'mimeType': str(image_type),
        "languageCodes": ["ru"],
        "model": "page",
        "content": base64_image
    }
    response = requests.post(url=__url_image__, headers=__headers_image__, json=img_json)
    return response.json()


def get_text_from_image_by_id(reader_id):
    url = f'https://ocr.api.cloud.yandex.net/ocr/v1/getRecognition?operationId={reader_id}'
    response = requests.get(url=url, headers=__headers_image__)
    parts = response.text.split('\n')
    jsons = []
    for part in parts:
        if len(part) == 0 or part == '' or part is None:
            continue
        jsons.append(json.loads(part))
    return jsons
