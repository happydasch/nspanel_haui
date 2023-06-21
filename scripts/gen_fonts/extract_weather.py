import json

with open('scripts/gen_fonts/icons_mapping.json', 'r') as f:
    icon_mapping = json.load(f)

offset = 0xe2001
icons = []
for icon_name in icon_mapping:
    if icon_name.startswith('weather'):
        icons.append(hex(ord(icon_mapping[icon_name]) + offset))

print(', '.join(sorted(icons)))
