import os
import json
import re

with open('scripts/gen_fonts/icons_mapping.json', 'r') as f:
    icon_mapping = json.load(f)
icon_data = []

path = 'scripts/gen_fonts/MaterialDesign-SVG/svg'

for icon in icon_mapping.keys():
    filename = os.path.join(path, f'{icon}.svg')
    pathfile = os.path.abspath(filename)
    if not os.path.isfile(pathfile):
        print(f'Missing icon: {icon}')
    with open(pathfile, 'r') as f:
        icon_cnt = f.read()
        value = ord(icon_mapping[icon])
        data_value = re.search(r'path\sd="([^"]*)"', icon_cnt).group(1)
        icon_data.append({
            'name': icon,
            'hex': hex(value)[2:].upper(),
            'data': data_value})

with open('scripts/gen_fonts/icons_data.json', 'w') as f:
    json.dump(icon_data, f)
