####################################################################################################
#
# Generate-HASP-Fonts.ps1
#
# Create the Nextion ZI version 5 fonts used by the HASP project
#
# All the real hard work done by https://github.com/fvanroie.  THANK YOU FVANROIE!
#
# ZiLib library included here sourced from:
# https://github.com/fvanroie/nextion-font-editor
#
# Noto Sans font included here sourced from:
# https://github.com/googlefonts/noto-fonts/tree/master/hinted/NotoSans
# License: https://github.com/googlefonts/noto-fonts/blob/master/LICENSE
#
# MaterialDesign font included here sourced from:
# https://github.com/Templarian/MaterialDesign-Font
# License: https://github.com/Templarian/MaterialDesign/blob/master/LICENSE
#
####################################################################################################
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this hardware,
# software, and associated documentation files (the "Product"), to deal in the Product without
# restriction, including without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Product, and to permit persons to whom the
# Product is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Product.
#
# THE PRODUCT IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
# NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE PRODUCT OR THE USE OR OTHER DEALINGS IN THE PRODUCT.
####################################################################################################

Set-Location $PSScriptRoot
[void] [System.Reflection.Assembly]::LoadWithPartialName("System.Drawing")
Add-Type -Path ./ZiLib.dll

Function Main {
  <#
  .SYNOPSIS
  Main Execute New-ZiFontV5() to generate each font required for the project.
  #>

  $codePage = [ZiLib.CodePageIdentifier]::utf_8

  $outfile = "output" | Resolve-Path | ForEach-Object { $_.Path }
  $textFont = "./Roboto/Roboto-Regular.ttf" | Get-ChildItem | ForEach-Object { $_.FullName }
  $textFontBold = "./Roboto/Roboto-Bold.ttf" | Get-ChildItem | ForEach-Object { $_.FullName }
  $iconFont = "./MaterialDesign-Webfont/fonts/materialdesignicons-webfont.ttf" | Get-ChildItem | ForEach-Object { $_.FullName }
  $startCP = 0xf0001
  $offsetCP = 0xe2001
  $endCP = 0xf1c81

  $rangeText = @(
    @(0x0, 0x7f), # Basic Latin
    @(0x80, 0xff), # C1 Controls and Latin-1 Supplement
    @(0x100, 0x17f), # Latin Extended-A
    @(0x180, 0x24f) # Latin Extended-B
  )
  $rangeTextWeather = @(
    @(0x0, 0x7f), # Basic Latin
    @(0x80, 0xff) # C1 Controls and Latin-1 Supplement
  )
  $rangeIcon = @(@($startCP..$endCP))
  $weatherIcons = @(
    0xf0590, 0xf0591, 0xf0592, 0xf0593, 0xf0594, 0xf0595, 0xf0596, 0xf0597, 0xf0598, 0xf0599, 0xf059a, 0xf059b, 0xf059c, 0xf059d, 0xf059e, 0xf067e, 0xf067f, 0xf0898, 0xf0e6e, 0xf0f2f, 0xf0f30, 0xf0f31, 0xf0f32, 0xf0f33, 0xf0f34, 0xf0f35, 0xf0f36, 0xf0f37, 0xf0f38, 0xf14e4, 0xf18f6, 0xf1b5a, 0xf1c78
  )
  # $textFontSize,$textVerticalOffset,$iconFontSizeOffset,$iconVerticalOffset
  $toGenerate = @(
    @(20, 1, 4, 0),
    @(24, 1, 0, 2),
    @(32, 1, -2, 4),
    @(48, 1, 0, 4)
  )
  # $textFontSize,$textVerticalOffset,$iconFontSizeOffset,$iconVerticalOffset
  $toGenerateWeather = @(
    @(72, 0, 0, 6),
    @(96, 0, 0, 6),
    @(112, 0, 0, 8),
    @(128, 0, 0, 8)
  )

  foreach ($values in $toGenerate) {
    $textFontSize = $values[0]
    $textVerticalOffset = $values[1]
    $iconFontSizeOffset = $values[2]
    $iconVerticalOffset = $values[3]
    New-ZiFontV5 -textFont $textFont -iconFont $iconFont -iconFontFirstCP $startCP -iconFontLastCP $endCP -iconCPOffset $offsetCP -iconVerticalOffset $iconVerticalOffset -textVerticalOffset $textVerticalOffset -textFontSize $textFontSize -iconFontSizeOffset $iconFontSizeOffset -Codepage $codePage -Path $outfile -rangeIcon $rangeIcon -rangeText $rangeText
    New-ZiFontV5 -textFont $textFontBold -iconFont $iconFont -iconFontFirstCP $startCP -iconFontLastCP $endCP -iconCPOffset $offsetCP -iconVerticalOffset $iconVerticalOffset -textVerticalOffset $textVerticalOffset -textFontSize $textFontSize -iconFontSizeOffset $iconFontSizeOffset -Codepage $codePage -Path $outfile -rangeIcon $rangeIcon -rangeText $rangeText
  }

  foreach ($values in $toGenerateWeather) {
    $textFontSize = $values[0]
    $textVerticalOffset = $values[1]
    $iconFontSizeOffset = $values[2]
    $iconVerticalOffset = $values[3]
    New-ZiFontV5 -textFont $textFont -iconFont $iconFont -iconFontFirstCP $startCP -iconFontLastCP $endCP -iconCPOffset $offsetCP -iconVerticalOffset $iconVerticalOffset -textVerticalOffset $textVerticalOffset -textFontSize $textFontSize -iconFontSizeOffset $iconFontSizeOffset -Codepage $codePage -Path $outfile -rangeIcon $weatherIcons -rangeText $rangeTextWeather
    New-ZiFontV5 -textFont $textFontBold -iconFont $iconFont -iconFontFirstCP $startCP -iconFontLastCP $endCP -iconCPOffset $offsetCP -iconVerticalOffset $iconVerticalOffset -textVerticalOffset $textVerticalOffset -textFontSize $textFontSize -iconFontSizeOffset $iconFontSizeOffset -Codepage $codePage -Path $outfile -rangeIcon $weatherIcons -rangeText $rangeTextWeather
  }
}

Function New-ZiFontV5 {
  <#
  .SYNOPSIS
  New-ZiFontV5 Generate a new Nextion .ZI v5 font from local font files

  .DESCRIPTION
  Provided a text font, and optionally an icon font, generate a Nextion .ZI v5 font file.  Offers controls for remapping text and icon font
  position and size, along with controls for remapping codepoints into Private Use space from 0xE000 to 0xF8FF.

  .LINK
  https://github.com/aderusha/Generate-HASP-Fonts
  #>

  [CmdletBinding()]
  param (
    [Parameter(Position = 0, Mandatory = $true, HelpMessage = "Text font filename")][ValidateScript( { Test-Path $_ })][string]$textFont,
    [Parameter(Position = 1, Mandatory = $false, HelpMessage = "Icon font filename")][ValidateScript( { Test-Path $_ })][string]$iconFont,
    [Parameter(Position = 2, Mandatory = $false, HelpMessage = "Icon font start codepoint")][int]$iconFontFirstCP,
    [Parameter(Position = 3, Mandatory = $false, HelpMessage = "Icon font end codepoint")][int]$iconFontLastCP,
    [Parameter(Position = 4, Mandatory = $false, HelpMessage = "Icon font codepoint offset to fit result below 0xFFFF")][int]$iconCPOffset = 0,
    [Parameter(Position = 5, Mandatory = $false, HelpMessage = "Text font vertical offset")][int]$textVerticalOffset = 0,
    [Parameter(Position = 6, Mandatory = $false, HelpMessage = "Icon font vertical offset")][int]$iconVerticalOffset = 0,
    [Parameter(Position = 7, Mandatory = $true, HelpMessage = "Text font size")][int]$textFontSize,
    [Parameter(Position = 8, Mandatory = $false, HelpMessage = "Icon font size offset from text size")][int]$iconFontSizeOffset=0,
    [Parameter(Position = 9, Mandatory = $false, HelpMessage = "Font codepage")]$Codepage = [ZiLib.CodePageIdentifier]::utf_8,
    [Parameter(Position = 10, Mandatory = $true, HelpMessage = "Generated font output folder")][string]$Path,
    [Parameter(Position = 11, Mandatory = $true, HelpMessage = "Range of text")][array]$rangeText,
    [Parameter(Position = 12, Mandatory = $true, HelpMessage = "Range of icons")][array]$rangeIcon
  )

  $locationText = [System.Drawing.PointF]::new(0, $textVerticalOffset)
  $locationIcon = [System.Drawing.PointF]::new(0, $iconVerticalOffset)

  $file = Get-ChildItem $textFont

  if ((($file.Extension -eq ".ttf") -or ($file.Extension -eq ".otf")) -and ($file.Exists)) {
    # Check if fontname is a otf/ttf file
    $pfc = [System.Drawing.Text.PrivateFontCollection]::new()
    $pfc.AddFontFile($textFont)
    $font = [System.Drawing.Font]::new($pfc.Families[0], $textFontSize, "regular", [System.Drawing.GraphicsUnit]::pixel );

    if ($iconFont) {
      $pfc.AddFontFile($iconFont)
      $iconFontSet = $pfc.families | Select-Object -First 1
    }
  }
  else {
    $font = [ZiLib.Extensions.BitmapExtensions]::GetFont($textFont, $textFontSize, "Regular")
  }

  $newfontsize = $textFontSize
  $i = 0
  while ([math]::Abs($textFontSize - $font.Height) -gt 0.1 -and $i++ -lt 10) {
    $newfontsize += ($textFontSize - $font.Height) / 2 * $newfontsize / $font.Height;
    $font = [System.Drawing.Font]::new($font.fontfamily, $newfontsize, "regular", [System.Drawing.GraphicsUnit]::pixel );
  }

  $f = [ZiLib.FileVersion.V5.ZiFontV5]::new()
  $f.CharacterHeight = $textFontSize
  $f.CodePage = $codepage
  $f.Version = 5

  foreach ($values in $rangeText) {
    foreach ($ch in $values[0]..$values[1]) {
      # normal text
      $txt = [Char]::ConvertFromUtf32([uint32]($ch + $codepoint.delta))
      $character = [ZiLib.FileVersion.Common.ZiCharacter]::FromString($f, $ch, $font, $locationText, $txt)
      $f.AddCharacter($ch, $character)
    }
  }
  #foreach ($ch in 32..1024) {
  #  # normal text
  #  $bytes = [bitconverter]::GetBytes([uint16]$ch)
  #  if ($f.CodePage.CodePageIdentifier -eq "UTF_8") {
  #    if ($ch -lt 0x00d800 -or $ch -gt 0x00dfff) {
  #      $txt = [Char]::ConvertFromUtf32([uint32]($ch + $codepoint.delta))
  #    }
  #    else { $txt = "?" }
  #  }
  #  else {
  #    if ($ch -gt 255) {
  #      $txt = $f.CodePage.Encoding.GetChars($bytes, 0, 2)
  #    }
  #    else {
  #      $txt = $f.CodePage.Encoding.GetChars($bytes, 0, 1)
  #    }
  #  }
  #
  #  $character = [ZiLib.FileVersion.Common.ZiCharacter]::FromString($f, $ch, $font, $locationText, $txt)
  #  $f.AddCharacter($ch, $character)
  #}
  if ($iconFont) {
    $font = [System.Drawing.Font]::new($iconFontSet, ($newfontsize + $iconFontSizeOffset), "regular", [System.Drawing.GraphicsUnit]::pixel )
    foreach ($values in $rangeIcon) {
      $chars = @()
      if ($values -is [int]) {
        $chars += $values
      } else {
        foreach ($ch in $values[0]..$values[1]) {
          $chars += $ch
        }
      }
      foreach ($char in $chars) {
        $txt = [Char]::ConvertFromUtf32([uint32]($char))
        $character = [ZiLib.FileVersion.Common.ZiCharacter]::FromString($f, $char - $iconCPOffset, $font, $locationIcon, $txt)
        $f.AddCharacter($char, $character)
      }
    }
  }

  $file = Get-Item $textFont
  $filename = $file.basename
  $f.Name = $filename

  New-Item -ItemType Directory -Path $path -Force | Out-Null
  $outfile = Join-Path -Path $path -ChildPath ("{0} {1} ({2}).zi" -f $filename, $textFontSize, $Codepage)
  Write-Host "Writing $outfile"
  $f.Save($outfile)
}

Main