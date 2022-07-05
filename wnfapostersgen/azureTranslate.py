import requests, uuid
from wnfapostersgen.secrets import subscription_key

# Add your subscription key and endpoint
endpoint = "https://api.cognitive.microsofttranslator.com"

# Add your location, also known as region. The default is global.
# This is required if using a Cognitive Services resource.
location = "global"

path = '/translate'
constructed_url = endpoint + path

def translate(text):
    params = {
        'api-version': '3.0',
        'to': ['en', 'zh-Hans']
    }
    constructed_url = endpoint + path

    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Ocp-Apim-Subscription-Region': location,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }

    # You can pass more than one object in body.
    body = [{
        'text': text
    }]

    request = requests.post(constructed_url, params=params, headers=headers, json=body)
    response = request.json()[0]
    
    text_en = response['translations'][0]['text']
    text_cn = response['translations'][1]['text']
    

    return text_en, text_cn
