class PurePythonBarcode128:
    """Generates Code 128 subset B SVG vectors directly in pure Python."""

    # Simplified Code128 pattern table subset for numeric/alphanumeric strings
    PATTERNS = {
        '0': "212222", '1': "222122", '2': "222221", '3': "121223", '4': "121322",
        '5': "131222", '6': "122213", '7': "122312", '8': "132212", '9': "221213",
        'A': "112232", 'B': "122132", 'C': "122231", 'D': "113222", 'E': "123122",
        'F': "123221", 'G': "221132", 'H': "221231", 'I': "213212", 'J': "223112",
        'K': "312131", 'L': "311222", 'M': "321122", 'N': "321221", 'O': "312212",
        'P': "322112", 'Q': "322211", 'R': "212123", 'S': "212321", 'T': "232121",
        'U': "111323", 'V': "131123", 'W': "131321", 'X': "112313", 'Y': "132113",
        'Z': "132311", '-': "211133", '_': "211331", ' ': "211213"
    }
    START_CODE = "211214"
    STOP_CODE = "2331112"

    @classmethod
    def generate_svg(cls, code_text: str, width: int = 300, height: int = 80) -> str:
        code_clean = code_text.upper().replace(':', '-').replace('/', '-')
        modules = [cls.START_CODE]
        
        for char in code_clean:
            modules.append(cls.PATTERNS.get(char, "111111"))
            
        modules.append(cls.STOP_CODE)
        full_pattern = "".join(modules)

        bar_width = width / (len(full_pattern) * 2)
        svg_bars = []
        x_pos = 10.0
        
        is_bar = True
        for digit in full_pattern:
            w = int(digit) * bar_width * 1.5
            if is_bar:
                svg_bars.append(f'<rect x="{x_pos:.2f}" y="10" width="{w:.2f}" height="{height-30}" fill="#000000"/>')
            x_pos += w
            is_bar = not is_bar

        text_x = width / 2
        text_y = height - 5
        
        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
    <rect width="100%" height="100%" fill="#ffffff"/>
    {''.join(svg_bars)}
    <text x="{text_x}" y="{text_y}" font-family="monospace" font-size="12" text-anchor="middle" fill="#000000">{code_clean}</text>
</svg>"""
        return svg_content