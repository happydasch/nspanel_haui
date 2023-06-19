import json

scss_file = 'scripts/gen_fonts/MaterialDesign-Webfont/scss/_variables.scss'

# start codepage
start = 0xf0001
# offset for chr value (i - offset)
offset = 0xe2001

with open(scss_file, 'r') as f:
    string = f.read()

content = string[string.find('(') + 1:string.find(')')]
pairs = content.split(',')

dictionary = {}
for pair in pairs:
    key, value = pair.strip().split(':')
    key = key.strip().strip('"')
    value = value.strip().strip('"')
    dictionary[key] = chr(int(value, 16) - offset)

print(f'Total: {len(dictionary)} ({hex(len(dictionary))})')
print(f'Offset: {hex(offset)}')
print(f'Start: {hex(start)}')
print(f'End: {hex(start+len(dictionary))}')
icons = '\n'.join(f'{" "*4}\'{k}\': \'{v}\',' for k, v in dictionary.items())
icon_var = f'ICONS_MAPPING = {{\n{icons}\n}}'

with open('scripts/gen_fonts/icons_mapping.py', 'w') as f:
    f.write(icon_var)

with open('scripts/gen_fonts/icons_mapping.json', 'w') as f:
    json.dump(dictionary, f)
