

from wnfapostersgen.art_generator import ArtGeneratorFromText
from wnfapostersgen.loadFileShareFiles import warm_up
import azure.functions as func
import base64, json, logging, random


def compute(text):
    poster_binary = ArtGeneratorFromText(text).generate()

    return poster_binary


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    if (req.params.get('server') == 'wakeup'):
        if (warm_up()):
            return func.HttpResponse(
                str(random.random()),
                status_code=200
            )
        else:
            return func.HttpResponse(
                str(random.random()),
                status_code=500
            )

    text = req.params.get('text')
    if not text:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else: 
            text = req_body.get('text')
    
    if text:

        # image_binary = compute(text)
        # image_base64 = base64.b64encode(image_binary).decode('ascii')
        # # image_base64 = base64.urlsafe_b64encode(image_binary).decode('ascii')
        # return func.HttpResponse(
        #     json.dumps({
        #         'image_data': str(image_base64)
        #     }),
        #     status_code=200
        # )

        try:
            # validation
            if len(text) > 500:
                raise ValueError
            
            image_binary = compute(text)
            image_base64 = base64.b64encode(image_binary).decode('ascii')
            # image_base64 = base64.urlsafe_b64encode(image_binary).decode('ascii')
            return func.HttpResponse(
                json.dumps({
                    'image_data': str(image_base64)
                }),
                status_code=200
            )
        except ValueError:
            return func.HttpResponse(
                "invalid input",
                status_code=400
            )
        except:
            return func.HttpResponse(
                "server error",
                status_code=500
            )

    else:
        return func.HttpResponse(
            "invalid input",
            status_code=400
        )
