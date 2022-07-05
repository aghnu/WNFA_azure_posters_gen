from wnfapostersgen.loadFileShareFiles import get_file_binary

import numpy as np
import cv2 as cv
from skimage import io, transform, img_as_ubyte
from PIL import Image, ImageDraw, ImageFont
import math
import textwrap
import io as sysio

'''
get the absolute path for a file
'''
def get_path(relative_path):
    # path = os.path.abspath(os.path.split(__file__)[0] + "/" + relative_path)
    return relative_path

'''
load an image from path
image is an numpy array with RGBA chanels and a type of np.ubyte
'''
def load_image(relative_path):
    image_binary = get_file_binary(relative_path)
    image = np.array(Image.open(sysio.BytesIO(image_binary)))

    return img_as_ubyte(cv.cvtColor(image, cv.COLOR_RGB2RGBA))

'''
make an RGBA image grey scale
'''
def make_grey_scale(img):
    img = img.copy()
    return cv.cvtColor(img, cv.COLOR_RGBA2GRAY)

'''
resize an image to given size - (height, width)
'''
def resize_image_to_size(img, size_hw):
    img = img.copy()
    img_pil = Image.fromarray(img).resize([size_hw[1], size_hw[0]], resample=Image.Resampling.NEAREST)
    img = np.array(img_pil)
    return img

'''
crop an image with given size and starting position
'''
def crop_image(img, size_hw, position_hw):
    img = img.copy()
    return img[position_hw[0]:position_hw[0]+size_hw[0],position_hw[1]:position_hw[1]+size_hw[1]]


'''
paste overlay onto the img at given position
'''
def paste_image(img, overlay, position_hw):
    img = img.copy()
    
    img_selected = Image.fromarray(crop_image(img, (overlay.shape[0], overlay.shape[1]), position_hw))
    img_overlay = Image.fromarray(overlay)
    img_selected.paste(img_overlay, mask=img_overlay)
    
    img[position_hw[0]:position_hw[0]+overlay.shape[0],position_hw[1]:position_hw[1]+overlay.shape[1]] = np.array(img_selected)
    return img

'''
apply rotation to an image with given angle
'''
def rotate_image(img, angle):
    return img_as_ubyte(transform.rotate(img, angle))

'''
change aplha value for only pixels that are semi transparent or solid
ignore fully transparent value
'''
def change_valid_pixels_alpha(img, value):
    img = img.copy()
    img[:,:,3][img[:,:,3] > 0] = value
    return img

'''
change alpha value for only pixels that are fully transparent
'''
def change_fully_transparent_pixels_alpha(img, value):
    img = img.copy()
    img[:,:,3][img[:,:,3] == 0] = value
    return img

'''
generate an 4x4 image with given RGBA value
'''
def get_single_color_img(value_RGBA):
    return np.array([
        [value_RGBA,value_RGBA],
        [value_RGBA,value_RGBA],
    ], dtype=np.ubyte)

'''
make an character
'''
def get_char_image(char, font_relative_path, font_size, color):
    img = get_single_color_img((255,255,255,0))
    img = resize_image_to_size(img, (font_size, font_size))
    img_pil = Image.fromarray(img)

    draw = ImageDraw.Draw(img_pil)

    

    font = ImageFont.truetype(sysio.BytesIO(get_file_binary(font_relative_path)), font_size)
    draw.text((0,0), char, fill=color, font=font)

    img = np.array(img_pil)
    return img

'''
print text to an newly generated transparent image
'''
def get_text_image(text, size_hw, font_relative_path, font_size, color):
    text = str(text)
    text = text[0:2000]
    img = get_single_color_img((255,255,255,0))
    img = resize_image_to_size(img, (size_hw[0], size_hw[1]))
    img_pil = Image.fromarray(img)

    draw = ImageDraw.Draw(img_pil)
    font = ImageFont.truetype(sysio.BytesIO(get_file_binary(font_relative_path)), font_size)
    text_str = "\n".join(textwrap.wrap(text, width=size_hw[1]*2//font_size))
    draw.text((0,0), text_str, fill=color, font=font)

    img = np.array(img_pil)
    return img

'''
apply mask to img with img's pixel RGB value inverted at mask
'''
def add_mask_to_image_invert(img, mask):
    img = img.copy()
    mask = mask.copy()
    mask = change_valid_pixels_alpha(mask, 50)
    img[:,:,:3][mask[:,:,3] > 0] = np.invert(img[:,:,:3][mask[:,:,3] > 0])
    return img

'''
erase an image using the given mask, replace erased pixel to given value
'''
def erase_image_with_mask(img, mask, value_RGBA):
    img = img.copy()
    img[:,:][mask[:,:,3] == 0] = value_RGBA

'''
filter invert
'''
def filter_invert(img):
    img = img.copy()
    img = cv.cvtColor(img, cv.COLOR_RGBA2RGB)
    img = np.invert(img)
    img = cv.cvtColor(img, cv.COLOR_RGB2RGBA)
    return img

'''
filter color
'''
def filter_color(img, filter_value_RGBA):
    img = img.copy()
    
    filter = get_single_color_img(filter_value_RGBA)
    filter = resize_image_to_size(filter, (img.shape[0], img.shape[1]))

    grey = cv.cvtColor(img, cv.COLOR_RGBA2GRAY)
    white_mask = grey[:,:] == 255
    grey = cv.cvtColor(grey, cv.COLOR_GRAY2RGBA)

    img = cv.addWeighted(grey, 0.8, filter, 0.2, 0)
    img[:,:][white_mask] = [255,255,255,255]

    return img

def resize_image_width(img, width):
    ratio = img.shape[0]/img.shape[1]
    height = math.floor(ratio * width)

    return resize_image_to_size(img, (height, width))

def resize_image_height(img, height):
    ratio = img.shape[1]/img.shape[0]
    width = math.floor(ratio * height)

    return resize_image_to_size(img, (height, width))

def make_RGBA_to_RGB(img):
    img = img.copy()
    return cv.cvtColor(img, cv.COLOR_RGBA2RGB)


