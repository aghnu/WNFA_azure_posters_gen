

from wnfapostersgen.art_generator import ArtGeneratorFromText
import azure.functions as func
import base64
import logging


def compute(text):
    poster_binary = ArtGeneratorFromText(text).generate()

    return poster_binary


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        req_body = req.get_json()
    except ValueError:
        pass
    else:
        try:
            text = str(req_body.get('text'))
        except ValueError:
            pass
    
    if (text and len(text) > 0):
        try:
            image_binary = compute(text)
            image_base64 = base64.b64encode(image_binary)
            return func.HttpResponse(
                image_base64,
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
