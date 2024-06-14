import json
import os
import re
# Define a regular expression to match a `self.translate()` call with an argument
translate_pattern = re.compile(r'\.translate\((\'|")(.*)(\'|")\)')
# Define the directory to search for Python files in
directory = 'apps/nspanel_haui'
# Create a list to store the translated strings
translations = {}
# Iterate over all Python files in the directory and its subdirectories
for root, dirs, files in os.walk(directory):
    for file in files:
        if file.endswith('.py'):
            # Read the contents of the file into a string
            with open(os.path.join(root, file), 'r') as f:
                contents = f.read()
            # Use the regular expression to find all `self.translate()` calls with arguments
            for match in translate_pattern.finditer(contents):
                # Add the argument to the list of translations
                translations[match.group(2)] = ''

with open('scripts/translations/translate.json', 'w') as file:
    json.dump({'text': translations}, file, indent=2)
