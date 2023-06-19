with open('scripts/gen_fonts/icons_data.json', 'r') as f:
    icons = f.read()
cheatsheet = '''
<!doctype html>
<html lang="en">

<head>
    <meta charset="utf-8" />
    <meta name="google" content="notranslate">
    <title>HASwitchPlate Material Design Icons</title>
    <style>
        * {
            margin: 0;
            padding: 0;
        }

        body {
            margin: 0;
            padding: 0;
            background: #fff;
            color: #222;
        }

        h1,
        h2,
        h3,
        p,
        div,
        blockquote,
        footer {
            font-family: "Helvetica Neue", Arial, sans-serif;
        }

        h1 {
            padding: 20px 20px 16px 20px;
            font-size: 26px;
            line-height: 26px;
            font-weight: normal;
            color: #FFF;
            background-color: #2196F3;
        }

        h1 svg {
            vertical-align: middle;
            width: 26px;
            height: 26px;
            margin: 0 6px 4px 0;
        }

        h1 svg path {
            fill: #FFF;
        }

        h1 .version {
            font-size: 14px;
            background: #FFF;
            padding: 4px 10px;
            float: right;
            border-radius: 2px;
            margin: -3px 0 0 0;
            color: #666;
            font-weight: bold;
        }

        h1 code {
            font-size: 20px;
            background: rgba(0, 0, 0, 0.5);
            padding: 4px 12px;
            border-radius: 3px;
            float: right;
            margin: -3px 10px 0 0;
            border: 1px solid transparent;
            cursor: pointer;
        }

        h1 code:hover {
            border: 1px solid #FFF;
        }

        h1 code svg {
            width: 24px;
            height: 24px;
            margin: -1px -4px 0 -2px
        }

        h2 {
            font-size: 18px;
            padding: 20px;
        }

        h2 small {
            color: #555;
            font-size: 0.8rem;
        }

        h2 small::before {
            content: '(';
        }

        h2 small::after {
            content: ')';
        }

        h2 span {
            position: relative;
        }

        h3 {
            font-size: 14px;
            padding: 10px 20px 0 20px;
            font-weight: bold;
        }

        p {
            padding: 10px 20px;
        }

        p code {
            display: inline-block;
            vertical-align: middle;
            background: #F1F1F1;
            padding: 3px 5px;
            border-radius: 3px;
            border: 1px solid #DDD;
        }

        p i.mdi {
            vertical-align: middle;
            border-radius: 4px;
            display: inline-block;
        }

        p i.mdi.dark-demo {
            background: #333;
        }

        p.note {
            color: #999;
            font-size: 14px;
            padding: 0 20px 5px 20px;
        }

        p.extras {
            margin-top: -0.5rem;
        }

        div.icons {
            padding: 0 20px 10px 20px;
            -webkit-column-count: 5;
            -moz-column-count: 5;
            column-count: 5;
            -webkit-column-gap: 20px;
            -moz-column-gap: 20px;
            column-gap: 20px;
        }

        div.icons div {
            line-height: 2em;
            white-space: nowrap;
        }

        div.icons div span {
            cursor: pointer;
            font-size: 14px;
            text-overflow: ellipsis;
            display: inline-block;
            max-width: calc(100% - 90px);
            overflow: hidden;
            vertical-align: middle;
            white-space: nowrap;
        }

        div.icons div span:hover,
        div.icons div svg:hover {
            fill: #3c90be;
        }

        div.icons div code.hex:hover {
            border-color: #3c90be;
            z-index: 1;
            position: relative;
        }

        div.icons div code.hex {
            border: 1px solid #DDD;
            width: 46px;
            margin-right: 4px;
            border-radius: 0 4px 4px 0;
            display: inline-block;
            vertical-align: middle;
            text-align: center;
            line-height: 24px;
            cursor: pointer;
        }

        div.icons div code.unicode:hover {
            border-color: #3c90be;
            background: #3c90be;
            color: #FFF;
            z-index: 1;
            position: relative;
        }

        div.icons div code.unicode {
            border: 1px solid #DDD;
            background: #DDD;
            font-weight: bold;
            margin-right: -1px;
            padding-left: 3px;
            padding-right: 3px;
            border-radius: 4px 0 0 4px;
            display: inline-block;
            vertical-align: middle;
            text-align: center;
            line-height: 24px;
            cursor: pointer;
        }
        div.icons div code.unicode::before {
            content: 'U';
        }

        div.icons div svg {
            display: inline-block;
            width: 32px;
            height: 24px;
            text-align: center;
            vertical-align: middle;
            cursor: pointer;
            line-height: 24px;
        }

        div.icons .mdi::before {
            font-size: 24px;
        }

        pre {
            margin: 0 20px;
            font-family: Consolas, monospace;
            padding: 10px;
            border: 1px solid #DDD;
            background: #F1F1F1;
        }

        ul.usage-list {
            list-style: square;
            padding-left: 3rem;
            line-height: 1.25rem;
            font-family: "Helvetica Neue", Arial, sans-serif;
        }

        blockquote {
            position: relative;
            margin: 1rem 1rem 0 1rem;
            padding: 0.5rem 0.5rem 0.5rem 0.75rem;
        }

        blockquote.note::before {
            content: ' ';
            width: 0.25rem;
            height: 100%;
            background: #DDD;
            position: absolute;
            border-radius: 0.25rem;
            top: 0;
            left: 0;
        }

        div.copied {
            position: fixed;
            top: 100px;
            left: 50%;
            width: 200px;
            text-align: center;
            color: #3c763d;
            background-color: #dff0d8;
            border: 1px solid #d6e9c6;
            padding: 10px 15px;
            border-radius: 4px;
            margin-left: -100px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
        }

        footer {
            display: flex;
            padding: 20px;
            color: #666;
            border-top: 1px solid #DDD;
            background: #F1F1F1;
        }

        footer > div:first-child {
            flex: 1;
        }

        footer > div:last-child {
            text-align: right;
        }

        footer a {
            color: #e91e63;
            text-decoration: none;
        }

        footer a:hover {
            text-decoration: underline;
        }
    </style>
</head>

<body>
    <h1>
        <svg>
            <path d="M0,0H8V3H18V0H26V8H23V18H26V26H18V23H8V21H18V18H21V8H18V5H8V8H5V18H8V26H0V18H3V8H0V0M2,2V6H6V2H2M2,20V24H6V20H2M20,2V6H24V2H20M20,20V24H24V20H20Z"></path>
        </svg>
        HASwitchPlate Material Design Icons
        <span class="version">7.2.96</span>
    </h1>

    <h2 class="usage">Cheatsheet Usage</h2>

    <ul class="usage-list">
      <li>
        <b>HASP Users</b>: Click the <code>U</code> value to copy the character to your clipboard
      </li>
      <li>Click the icon to copy the SVG to your clipboard</li>
      <li>Click the hex value to copy the codepoint to your clipboard</li>
      <li>Click the icon name to copy to your clipboard</li>
    </ul>
    <h2 class="icons">All Icons <small id="iconsCount">-</small></h2>
    <div class="icons" id="icons"></div>

    <footer>
        <div>
            <a href="https://github.com/Templarian/MaterialDesign-Webfont">https://github.com/Templarian/MaterialDesign-Webfont</a>
        </div>
    </footer>

    <script type="text/javascript">
        function copyText(text) {
            var copyFrom = document.createElement('textarea');
            copyFrom.setAttribute("style", "position:fixed;opacity:0;top:100px;left:100px;");
            copyFrom.value = text;
            document.body.appendChild(copyFrom);
            copyFrom.select();
            document.execCommand('copy');
            var copied = document.createElement('div');
            copied.setAttribute('class', 'copied');
            copied.appendChild(document.createTextNode('Copied to Clipboard'));
            document.body.appendChild(copied);
            setTimeout(function () {
                document.body.removeChild(copyFrom);
                document.body.removeChild(copied);
            }, 1500);
        };
        function getIconItem(icon) {
            var svgNS = 'http://www.w3.org/2000/svg';
            var div = document.createElement('div'),
                svg = document.createElementNS(svgNS, 'svg'),
                path = document.createElementNS(svgNS, 'path');
            path.setAttribute('d', icon.data);
            svg.appendChild(path);
            div.appendChild(svg);
            var unicode = document.createElement('code');
            unicode.setAttribute('class', 'unicode');
            div.appendChild(unicode);
            var code = document.createElement('code');
            code.setAttribute('class', 'hex');
            code.appendChild(document.createTextNode(icon.hex));
            div.appendChild(code);
            var span = document.createElement('span');
            span.appendChild(document.createTextNode(icon.name));
            div.appendChild(span);
            span.onclick = function () {
                alert(icon.name);
            };
            svg.onmouseup = function () {
                copyText(`<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd"><svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" id="mdi-${icon.name}" width="24" height="24" viewBox="0 0 24 24"><g><path fill-opacity="0" d="M0,0H24V24H0" /><path d="${icon.data}" /></g></svg>`);
            };
            unicode.onmouseup = function () {
                console.log(icon.hex, parseInt(icon.hex, 16))
                copyText(String.fromCodePoint(parseInt(icon.hex, 16)));
            };
            code.onmouseup = function () {
                copyText(icon.hex);
            };
            span.onmouseup = function () {
                copyText(icon.name);
            };
            return div;
        }
        (function () {
            var iconsCount = 0;
            var newIconsCount = 0;
            var deprecatedIconsCount = 0;
            var icons = ''' + icons + ''';
            icons.forEach(function (icon) {
                var item = getIconItem(icon);
                document.getElementById('icons').appendChild(item);
                iconsCount++;
            });

            document.getElementById('iconsCount').innerText = iconsCount;
        })();
    </script>

</body>

</html>
'''
with open('docs/cheatsheet.html', 'w') as f:
    f.write(cheatsheet)
