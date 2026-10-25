# Generate Fonts

Create the Nextion ZI version 5 fonts used by the display (based on the HASP font generator)

- [Generate Fonts](#generate-fonts)
  - [Scripts](#scripts)
  - [PowerShell Script](#powershell-script)
  - [Cheatsheet](#cheatsheet)
  - [Credits](#credits)
  - [MIT License](#mit-license)

## Scripts

- `extract_chr_from_scss.py`

  Extracts mdi characters from scss file. This script will output also hex values for
  Total, Offset, Start, End. These values are needed for the PS script.

- `extract_weather.py`

  Extracts weather icons (icon name starts with weather), needed for the PS script.

- `gen_cheatsheet.py`

  Generates the icon cheatsheet based on current font.

- `extract_svg_from_mdi.py`

## PowerShell Script

The PowerShell script `Generate-HASP-Fonts.ps1` generates the fonts in the needed format for the nextion display.

Make sure to check and update these values:

```powershell
  $startCP = 0x..
  $offsetCP = 0x..
  $endCP = 0x..
  $weatherIcons = @(
    0x.., 0x..
  )
```

## Cheatsheet

[Check out the Cheatsheet to browse and select icons](https://happydasch.github.io/nspanel_haui/cheatsheet.html).  Click the "U" button next to your desired icon and the correct codepoint will be copied to your clipboard.

Regenerate it from `icons_data.json` (run from the repository root — the script uses relative paths):

```bash
python3 scripts/gen_fonts/gen_cheatsheet.py
```

Commit the regenerated `docs/cheatsheet.html` together with any change to
`scripts/gen_fonts/icons_data.json`; the `tests.yml` workflow fails when the
committed cheatsheet is stale.

See [Pictogrammers](https://pictogrammers.com/library/mdi/) if you need the char of the source font.

## Credits

All the real hard work done by GitHub user [fvanroie](https://github.com/fvanroie) and [joBr99](https://github.com/joBr99).

**ZiLib library** included in this project: [Source](https://github.com/fvanroie/nextion-font-editor)

**Roboto font** included in this project: [Source](https://github.com/googlefonts/roboto)/[License](https://github.com/googlefonts/roboto/blob/master/LICENSE)

**MaterialDesign SVG** included in this project: [Source](https://github.com/Templarian/MaterialDesign-SVG)/[License](https://github.com/Templarian/MaterialDesign-SVG/blob/master/LICENSE)

**MaterialDesign Webfont** included in this project: [Source](https://github.com/Templarian/MaterialDesign-Webfont)/[License](https://github.com/Templarian/MaterialDesign-Webfont/blob/master/LICENSE)

## MIT License

    Permission is hereby granted, free of charge, to any person obtaining a copy of this hardware, software, and associated documentation files (the "Product"), to deal in the Product without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Product, and to permit persons to whom the Product is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Product.

    THE PRODUCT IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE PRODUCT OR THE USE OR OTHER DEALINGS IN THE PRODUCT.
