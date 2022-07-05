
from wnfapostersgen.image_processing import GridArt
from wnfapostersgen.emotion_analysis import predict_emo
from wnfapostersgen.azureTranslate import translate

import base64
import io
from PIL import Image

'''
    this class is used to generate an art from text data
    text data must be in english
'''
class ArtGeneratorFromText:
    def __init__(self, text):
        self.text_en, self.text_cn = translate(text)
    
    def generate(self):
        emotion_data = predict_emo(self.text_en)
        
        # emotion_data_json_string = json.dumps(emotion_data)
        art = GridArt(emotion_data, {
            'base64': str(base64.b64encode(self.text_en.encode('ascii'))),
            'text_cn': self.text_cn, 
            'text_en': self.text_en
        })

        out = art.gen()
        
        img_pil = Image.fromarray(out)        
        buff = io.BytesIO()
        img_pil.save(buff, format="JPEG")

        return buff.getvalue()