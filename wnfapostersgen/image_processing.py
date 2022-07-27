from wnfapostersgen.loadFileShareFiles import get_list_of_files_binary_async
import wnfapostersgen.image_processing_utilities as iu
import numpy as np
import asyncio, json, os, string, base64, math

# constance
OUT_RES_WIDTH = 3200
OUT_RES_HEIGHT = 2700
OUT_GRID = 12

chinese_chars = [
    ( 0x4E00,  0x62FF),
    ( 0x6300,  0x77FF),
    ( 0x7800,  0x8CFF),
    ( 0x8D00,  0x9FCC),
    ( 0x3400,  0x4DB5),
    (0x20000, 0x215FF),
    (0x21600, 0x230FF),
    (0x23100, 0x245FF),
    (0x24600, 0x260FF),
    (0x26100, 0x275FF),
    (0x27600, 0x290FF),
    (0x29100, 0x2A6DF),
    (0x2A700, 0x2B734),
    (0x2B740, 0x2B81D),
    (0x2B820, 0x2CEAF),
    (0x2CEB0, 0x2EBEF),
    (0x2F800, 0x2FA1F)
]

def is_chinese_char(char):
    c = ord(char)
    for b,t in chinese_chars:
        if c >= b and c <= t:
            return True
    return False

def get_path(relative_path):
    path = os.path.abspath(os.path.split(__file__)[0] + "/" + relative_path)
    return path

def grid_to_size(gridHeight, gridWidth):
    return (gridHeight * (OUT_RES_HEIGHT//OUT_GRID), gridWidth * (OUT_RES_WIDTH//OUT_GRID))

def grid_to_pos(gridStartHeight, gridStartWidth):
    return (gridStartHeight * (OUT_RES_HEIGHT//OUT_GRID), gridStartWidth * (OUT_RES_WIDTH//OUT_GRID))

'''
mirror the given grid along the y axis
'''
def grid_mirror(grid_pos_size):
    # height, width
    grid_position, grid_size = grid_pos_size
    grid_position_new = [grid_position[0], OUT_GRID - (grid_position[1] + grid_size[1])]

    return grid_position_new, grid_size

'''
rotate the given grid 90 degrees to the right
'''
def grid_rotate_right(grid_pos_size):
    grid_position, grid_size = grid_pos_size
    grid_position_new = [grid_position[0] + grid_size[0], grid_position[1]]
    
    grid_position_new = [grid_position_new[1], OUT_GRID - grid_position_new[0]]
    grid_size = (grid_size[1], grid_size[0])

    return grid_position_new, grid_size

def check_validation(en_text, cn_text):
    # check length
    if (len(en_text) == 0 or len(cn_text) == 0):
        return False

    # check cn_text contains chinese character
    has_cnchar = False
    for char in cn_text:
        if is_chinese_char(char):
            has_cnchar = True
            break
    if not has_cnchar:
        return False

    # valid    
    return True
    

class EmotionDataParser:
    def __init__(self, emotion_data):
        self.emotion_data_raw = emotion_data
        self.emotion_data_sorted = []

        for key in self.emotion_data_raw.keys():
            self.emotion_data_sorted.append((key, self.emotion_data_raw[key]))
        self.emotion_data_sorted = sorted(self.emotion_data_sorted, key=lambda x: x[1], reverse=True)

        # normalize 0 - 1 # ranking
        self.emotion_data_norm = dict()
        self.emotion_ranking = dict()
        main = self.get_main_emotion()
        least = self.get_least_emotion()

        rank = 0        
        for data in self.emotion_data_sorted:
            norm_value = (data[1] - least[1]) / (main[1] - least[1])
            self.emotion_data_norm[data[0]] = norm_value
            self.emotion_ranking[data[0]] = rank
            rank += 1

    '''
    return a tuple (emotion_name, emotion_value)
    '''
    def get_main_emotion(self):
        return self.emotion_data_sorted[0]
    
    def get_major_emotion_candidates(self):
        return self.emotion_data_sorted[0:3]

    def get_least_emotion(self):
        return self.emotion_data_sorted[-1]
    
    def get_normalized_emotion_value(self, emotion_name):
        return self.emotion_data_norm(emotion_name)
    
    def get_ranking(self, emotion_name):
        return self.emotion_ranking[emotion_name]

'''
Use emotion_data to produce a seed
this seed will be used to generate random number whenever feasible
'''
class ControlledRandomGenerator:
    def __init__(self, emotion_data):
        self.emotion_data = emotion_data
        self.numpy_rng = self.gen_rng()
    
    def gen_rng(self):
        seed = 0
        index = 0
        ranking = sorted(list(self.emotion_data.values()))
        for score in ranking:
            seed = seed + score if index % 2 == 0 else seed - score
            index += 1
        
        return np.random.default_rng(int(seed * 1e17))
    
    def select_list(self,alist):
        index = math.floor(len(alist) * self.numpy_rng.random())
        return alist[index]

    def gen_range(self,min, max):
        return math.floor((max - min) * self.numpy_rng.random() + min)

    def gen_random_rotation_and_flip(self):
        steps = []
        # flip if machine says so, hehe
        if (self.select_list([True, False])):
            steps.append('f')
        
        # rotation
        rotation = self.gen_range(0,3)
        for _ in range(rotation):
            steps.append('r')
        
        # flip again if machine says so, keke
        if (self.select_list([True, False])):
            steps.append('f')

        return steps
    
    def gen_random_string(self, length):
        letters = string.ascii_letters
        return ''.join(self.select_list(letters) for i in range(length))

'''
Generate a grid art when provided with emotion data
'''
class GridArt:
    def __init__(self, emotion_data, record):
        # CORRECTION
        # 'happy' is used as foldname to grab asset, however, happiness is used in emotion_data
        # here we change the key 'happiness' to 'happy' for easy fix
        emotion_data['happy'] = emotion_data['happiness']
        emotion_data.pop('happiness', None)
        # END

        self.data_parser = EmotionDataParser(emotion_data)                                                          # emotion data parser
        self.random_generator = ControlledRandomGenerator(emotion_data)                                             # seeded random generator
        self.out = np.zeros((OUT_RES_HEIGHT, OUT_RES_WIDTH, 4), dtype=np.ubyte)                                     # output image
        self.out[:,:] = [255,255,255,255]
        # self.major_emotion = self.random_generator.select_list(self.data_parser.get_major_emotion_candidates())   # major emotion
        self.major_emotion = self.data_parser.get_main_emotion()
        self.record = record                                                                                        # (base64, text_cn, text_en)

    def get_list_of_valid_files_local(self, relative_path):
        file_list = \
            [f for f in os.listdir(get_path(relative_path)) \
                if f.split('.')[1] in ['png', 'jpg', 'json', 'ttf', 'otf', 'ttc']]

        return file_list

    def get_random_grid_transformation(self, steps, grid_pos_size):
        new_grid_pos_size = grid_pos_size

        for step in steps:
            if step == 'f':
                new_grid_pos_size = grid_mirror(new_grid_pos_size)
            if step == 'r':
                new_grid_pos_size = grid_rotate_right(new_grid_pos_size)

        return new_grid_pos_size

    def read_lookup(self):
        path = "assets/meta.json"
        lookup_meta = dict()

        with open(get_path(path)) as f:
            lookup_meta = json.load(f)
        
        return lookup_meta


    def read_grid(self):
        grids = {
            'a': [],
            'b': [],
            'c': [],
            'd': [],
            'e': [],
            'f': [],
            'g': []
        }

        for layer in grids.keys():
            path = "assets/grids/" + self.major_emotion[0] + "/" + layer + "/"
            file_list = self.get_list_of_valid_files_local(path)
            selected_file = self.random_generator.select_list(file_list)
            
            with open(get_path(path + selected_file)) as f:
                grid_json_dict = json.load(f)
                grids[layer].append(grid_json_dict)
        
        return grids

    def get_binary_code_text(self):
        binary_code = [
            "0001", "0011",
            "0111", "1111",
            "0010", "0110",
            "1110", "0100",
            "1100", "1000"
        ]
        return ''.join(self.random_generator.select_list(binary_code) for i in range(75))


    def stretch_crop_res(self, res, size_des):

        size_ratio = size_des[0]/size_des[1]
        res_ratio = res.shape[0]/res.shape[1]

        # pre rotate res to have the best fitting
        if (size_ratio >= 1 and res_ratio < 1) or (size_ratio < 1 and res_ratio >= 1):
            res = iu.rotate_image(res, self.random_generator.select_list([90, 270]))
            res_ratio = res.shape[0]/res.shape[1]
        else:
            res = iu.rotate_image(res, self.random_generator.select_list([0, 180]))

        # negative -> height smaller than width
        # positive -> height longer than width

        if size_ratio > res_ratio:
            # fit height
            res = iu.resize_image_height(res, size_des[0])
            range_width = res.shape[1] - size_des[1]
            position_width = self.random_generator.gen_range(0,range_width)
            res = iu.crop_image(res, size_des, (0,position_width))

            return res
        else:
            # fit width
            res = iu.resize_image_width(res, size_des[1])
            range_height = res.shape[0] - size_des[0]

            position_height = self.random_generator.gen_range(0,range_height)
            res = iu.crop_image(res, size_des, (position_height, 0))
            return res

    def apply_layer_block(self, grid):
        grid_transformation_steps = self.random_generator.gen_random_rotation_and_flip()
        for job in grid[0]:
            # get transformed position
            position, size = self.get_random_grid_transformation(grid_transformation_steps, (job['position'], job['size']))

            # get res
            res_block = iu.get_single_color_img((0,0,0,255))
            res_block = iu.resize_image_to_size(res_block, grid_to_size(*size))

            # apply mask to res if relevant
            if (job.get('mask', None) != None):
                # apply mask to res
                mask = job['mask']

                for m in mask:
                    # first get the position of the mask in canvas, apply transformation to it
                    # then get the position of the mask in res
                    m_p = [m['position'][0] + job['position'][0], m['position'][1] + job['position'][1]]
                    m_s = m['size']
                    m_p, m_s = self.get_random_grid_transformation(grid_transformation_steps, (m_p, m_s))
                    m_p = [m_p[0] - position[0], m_p[1] - position[1]]

                    # apply mask to res
                    res_m = iu.get_single_color_img((255,255,255,0))
                    res_m = iu.resize_image_to_size(res_m, grid_to_size(*m_s))
                    res_block = iu.paste_image(res_block, res_m, grid_to_pos(*m_p))
            
            # paste res
            self.out = iu.paste_image(self.out, res_block, grid_to_pos(*position))

    def apply_layer_grid(self, grid, files_binary):
        files_index = 0
        for job in grid[0]:
            # get res
            img_binary = files_binary[files_index]
            files_index += 1

            res_grid = iu.binary_to_image(img_binary)
            res_grid = iu.resize_image_to_size(res_grid, grid_to_size(*job['size']))
            
            # paste
            self.out = iu.paste_image(self.out, res_grid, grid_to_pos(*job['position']))

    def apply_layer_background(self, grid, files_binary):
        grid_transformation_steps = self.random_generator.gen_random_rotation_and_flip()
        files_index = 0
        for job in grid[0]:
            # get transformed position
            position, size = self.get_random_grid_transformation(grid_transformation_steps, (job['position'], job['size']))

            # get res
            img_binary = files_binary[files_index]
            files_index += 1

            res_block = iu.binary_to_image(img_binary)
            res_block = self.stretch_crop_res(res_block, grid_to_size(*size))

            # apply mask to res if relevant
            if (job.get('mask', None) != None):
                # apply mask to res
                mask = job['mask']

                for m in mask:
                    # first get the position of the mask in canvas, apply transformation to it
                    # then get the position of the mask in res
                    m_p = [m['position'][0] + job['position'][0], m['position'][1] + job['position'][1]]
                    m_s = m['size']
                    m_p, m_s = self.get_random_grid_transformation(grid_transformation_steps, (m_p, m_s))
                    m_p = [m_p[0] - position[0], m_p[1] - position[1]]

                    # apply mask to res
                    res_m = iu.get_single_color_img((255,255,255,0))
                    res_m = iu.resize_image_to_size(res_m, grid_to_size(*m_s))
                    res_block = iu.paste_image(res_block, res_m, grid_to_pos(*m_p))
            
            # paste res
            self.out = iu.paste_image(self.out, res_block, grid_to_pos(*position))

    def apply_layer_picture(self, grid, files_binary):
        grid_transformation_steps = self.random_generator.gen_random_rotation_and_flip()
        files_index = 0
        for job in grid[0]:
            # get transformed position
            position, size = self.get_random_grid_transformation(grid_transformation_steps, (job['position'], job['size']))

            # get res
            img_binary = files_binary[files_index]
            files_index += 1

            res_block = iu.binary_to_image(img_binary)
            res_block = self.stretch_crop_res(res_block, grid_to_size(*size))

            # apply mask to res if relevant
            if (job.get('mask', None) != None):
                # apply mask to res
                mask = job['mask']

                for m in mask:
                    # first get the position of the mask in canvas, apply transformation to it
                    # then get the position of the mask in res
                    m_p = [m['position'][0] + job['position'][0], m['position'][1] + job['position'][1]]
                    m_s = m['size']
                    m_p, m_s = self.get_random_grid_transformation(grid_transformation_steps, (m_p, m_s))
                    m_p = [m_p[0] - position[0], m_p[1] - position[1]]

                    # apply mask to res
                    res_m = iu.get_single_color_img((255,255,255,0))
                    res_m = iu.resize_image_to_size(res_m, grid_to_size(*m_s))
                    res_block = iu.paste_image(res_block, res_m, grid_to_pos(*m_p))
            
            # paste res
            self.out = iu.paste_image(self.out, res_block, grid_to_pos(*position))

    def apply_layer_text(self, grid, files_binary):
        grid_transformation_steps = self.random_generator.gen_random_rotation_and_flip()
        files_index = 0
        for job in grid[0]:
            # get transformed position
            position, size = self.get_random_grid_transformation(grid_transformation_steps, (job['position'], job['size']))
           
            # get font path
            font_binary = files_binary[files_index]
            files_index += 1
           
            # gen res
            text_type = job['type'] 
            if text_type == 'char':
                text_str = self.random_generator.select_list([c for c in list(self.record['text_cn']) if is_chinese_char(c)])
                res_block = iu.get_char_image(text_str, font_binary, grid_to_size(*size)[1], "black")
                res_block = iu.resize_image_to_size(res_block, grid_to_size(*size))
            elif text_type == 'text':

                text_str = self.record.get('base64', None)
                # base64 string, if not provide, use the image so far
                if text_str == None:
                    text_str = self.random_generator.gen_random_string(1000)
                    text_str = base64.b64encode(text_str.encode()).decode('ascii')
                    
                
                
                res_block = iu.get_text_image(text_str, grid_to_size(*size), font_binary, self.random_generator.gen_range(75, 175), "black")
                res_block = iu.resize_image_to_size(res_block, grid_to_size(*size))
            elif text_type == 'binary':
                text_str = self.get_binary_code_text()
                res_block = iu.get_text_image(text_str, grid_to_size(*size), font_binary, self.random_generator.gen_range(75, 175), "black")
                res_block = iu.resize_image_to_size(res_block, grid_to_size(*size))

            # apply mask to res if relevant
            if (job.get('mask', None) != None):
                # apply mask to res
                mask = job['mask']

                for m in mask:
                    # first get the position of the mask in canvas, apply transformation to it
                    # then get the position of the mask in res
                    m_p = [m['position'][0] + job['position'][0], m['position'][1] + job['position'][1]]
                    m_s = m['size']
                    m_p, m_s = self.get_random_grid_transformation(grid_transformation_steps, (m_p, m_s))
                    m_p = [m_p[0] - position[0], m_p[1] - position[1]]

                    # apply mask to res
                    res_m = iu.get_single_color_img((255,255,255,0))
                    res_m = iu.resize_image_to_size(res_m, grid_to_size(*m_s))
                    res_block = iu.paste_image(res_block, res_m, grid_to_pos(*m_p))
            
            # paste res
            out_selected = iu.crop_image(self.out, grid_to_size(*size), grid_to_pos(*position))
            res_block = iu.add_mask_to_image_invert(out_selected, res_block)

            self.out = iu.paste_image(self.out, res_block, grid_to_pos(*position))

    def apply_layer_decoration(self, grid, files_binary):
        grid_transformation_steps = self.random_generator.gen_random_rotation_and_flip()
        files_index = 0
        for job in grid[0]:
            # get transformed position
            position, size = self.get_random_grid_transformation(grid_transformation_steps, (job['position'], job['size']))

            # get res
            img_binary = files_binary[files_index]
            files_index += 1

            res_block = iu.binary_to_image(img_binary)
            res_block = self.stretch_crop_res(res_block, grid_to_size(*size))

            # apply mask to res if relevant
            if (job.get('mask', None) != None):
                # apply mask to res
                mask = job['mask']

                for m in mask:
                    # first get the position of the mask in canvas, apply transformation to it
                    # then get the position of the mask in res
                    m_p = [m['position'][0] + job['position'][0], m['position'][1] + job['position'][1]]
                    m_s = m['size']
                    m_p, m_s = self.get_random_grid_transformation(grid_transformation_steps, (m_p, m_s))
                    m_p = [m_p[0] - position[0], m_p[1] - position[1]]

                    # apply mask to res
                    res_m = iu.get_single_color_img((255,255,255,0))
                    res_m = iu.resize_image_to_size(res_m, grid_to_size(*m_s))
                    res_block = iu.paste_image(res_block, res_m, grid_to_pos(*m_p))
            
            # paste res
            self.out = iu.paste_image(self.out, res_block, grid_to_pos(*position))

    def apply_layer_geometry(self, grid, files_binary):
        grid_transformation_steps = self.random_generator.gen_random_rotation_and_flip()
        files_index = 0
        for job in grid[0]:
            # get transformed position
            position, size = self.get_random_grid_transformation(grid_transformation_steps, (job['position'], job['size']))

            # get res
            img_binary = files_binary[files_index]
            files_index += 1

            res_block = iu.binary_to_image(img_binary)
            res_block = self.stretch_crop_res(res_block, grid_to_size(*size))

            # apply mask to res if relevant
            if (job.get('mask', None) != None):
                # apply mask to res
                mask = job['mask']

                for m in mask:
                    # first get the position of the mask in canvas, apply transformation to it
                    # then get the position of the mask in res
                    m_p = [m['position'][0] + job['position'][0], m['position'][1] + job['position'][1]]
                    m_s = m['size']
                    m_p, m_s = self.get_random_grid_transformation(grid_transformation_steps, (m_p, m_s))
                    m_p = [m_p[0] - position[0], m_p[1] - position[1]]

                    # apply mask to res
                    res_m = iu.get_single_color_img((255,255,255,0))
                    res_m = iu.resize_image_to_size(res_m, grid_to_size(*m_s))
                    res_block = iu.paste_image(res_block, res_m, grid_to_pos(*m_p))
            
            # paste res
            out_selected = iu.crop_image(self.out, grid_to_size(*size), grid_to_pos(*position))
            res_block = iu.add_mask_to_image_invert(out_selected, res_block)
            self.out = iu.paste_image(self.out, res_block, grid_to_pos(*position))

    def check_path_lookup(self, path, lookup):
        val = lookup['path'][path]
        if isinstance(val, str):
            val = lookup['variable'][val]
        
        return val


    def get_all_assets_from_async_client(self, grids, lookup):
        # calculate all the assets required by each layer and retrieve them in one go.

        paths = []
        indexs = dict()

        # a 
        # b
        grid = grids['b']
        indexs['b'] = []
        indexs['b'].append(len(paths))
        for job in grid[0]:
            path = "art_assets/" + job['path']
            file_list = self.check_path_lookup(path, lookup)
            selected_file = self.random_generator.select_list(file_list)
            paths.append(selected_file)
        indexs['b'].append(len(paths))

        #c
        grid = grids['c']
        indexs['c'] = []
        indexs['c'].append(len(paths))
        for job in grid[0]:
            path = "art_assets/" + job['path']
            file_list = self.check_path_lookup(path, lookup)
            selected_file = self.random_generator.select_list(file_list)
            paths.append(selected_file)
        indexs['c'].append(len(paths))

        # d
        grid = grids['d']
        indexs['d'] = []
        indexs['d'].append(len(paths))
        for job in grid[0]:
            path = "art_assets/" + job['path']
            file_list = self.check_path_lookup(path, lookup)
            selected_file = self.random_generator.select_list(file_list)
            paths.append(selected_file)
        indexs['d'].append(len(paths))

        # e
        grid = grids['e']
        indexs['e'] = []
        indexs['e'].append(len(paths))
        for job in grid[0]:
            path = "art_assets/" + job['path']
            file_list = self.check_path_lookup(path, lookup)
            selected_file = self.random_generator.select_list(file_list)
            paths.append(selected_file)
        indexs['e'].append(len(paths))
        
        # f
        grid = grids['f']
        indexs['f'] = []
        indexs['f'].append(len(paths))
        for job in grid[0]:
            path = "art_assets/" + job['path']
            file_list = self.check_path_lookup(path, lookup)
            selected_file = self.random_generator.select_list(file_list)
            paths.append(selected_file)
        indexs['f'].append(len(paths))

        # g
        grid = grids['g']
        indexs['g'] = []
        indexs['g'].append(len(paths))
        for job in grid[0]:
            path = "art_assets/" + job['path']
            file_list = self.check_path_lookup(path, lookup)
            selected_file = self.random_generator.select_list(file_list)
            paths.append(selected_file)
        indexs['g'].append(len(paths))
        
        # load all binary files
        files_binary = asyncio.run(get_list_of_files_binary_async(paths))

        files_binary_dict = dict()
        for layer in indexs.keys():
            files_binary_dict[layer] = files_binary[indexs[layer][0]: indexs[layer][1]]
        
        return files_binary_dict

    def gen(self):
        '''
        Grid System Layers:
            "emotion"
                - a: block layer
                    - pure color block as resource
                    - stretch it to fit box
                - b: grid layer
                    - apply grid image to fit box
                    - stretch to fit
                - c: background layer
                    - apply bg image to fit box
                    - select the range to crop using width/height
                    - remove the selected mask block to alpha
                - d: picture layer
                    - apply resource to fit box
                    - resize the picture
                    - select the range to crop using width/height
                    - emove the selected mask block to alpha
                - e: text layer
                    - apply text using given font
                    - select font size
                    - stetch and fit the box
                - f: decoration layer
                    - stretch to fit
                    - apply grid image to fit box
                - g:
        '''

        grids = self.read_grid()
        lookup = self.read_lookup()
        binary_files = self.get_all_assets_from_async_client(grids, lookup)

        self.apply_layer_block(grids['a'])                                  # a
        self.apply_layer_grid(grids['b'], binary_files['b'])                # b
        self.apply_layer_background(grids['c'], binary_files['c'])          # c
        self.apply_layer_picture(grids['d'], binary_files['d'])             # d
        self.apply_layer_text(grids['e'], binary_files['e'])                # e
        self.apply_layer_decoration(grids['f'], binary_files['f'])          # f
        self.apply_layer_geometry(grids['g'], binary_files['g'])            # g

        # post processing
        self.out = iu.change_fully_transparent_pixels_alpha(self.out, 255)
        self.out = iu.change_valid_pixels_alpha(self.out, 255)

        # invert
        negative_emotion = ['anger', 'disgust', 'fear', 'sadness', 'shame']

        if self.major_emotion[0] in negative_emotion:
            # self.out = iu.filter_color(self.out, (30,85,170,255))
            self.out = iu.filter_invert(self.out)
            self.out = iu.filter_color(self.out, (200,190,160,255))
        else:
            self.out = iu.filter_color(self.out, (200,190,160,255))
        
        # convert RGBA to RGB
        self.out = iu.make_RGBA_to_RGB(self.out)

        return self.out