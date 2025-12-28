import base64
from . import fn

def encode_xor_readable(message: str, line_number: int) -> str:
    """
    Encode message so it's:
      - readable ASCII (Ascii85)
      - reversible
      - short
    Follows the spec: if line_number > 255, result is '|<payload>|n' where n = (line-1)//255.
    """
    g, prefix, suffix = _line_to_key_parts(line_number)
    data = message.encode("utf-8")
    xored = bytes((b ^ g) for b in data)
    payload = base64.a85encode(xored).decode("ascii")
    return prefix + payload + suffix

def _line_to_key_parts(line: int):
    if line < 1:
        raise ValueError("line numbers must be >= 1 (this scheme reserves 1..255 keys)")
    if line <= 255:
        return line, "", ""        # g=line, no prefix/suffix
    # for line > 255: choose n and g so that line = n*255 + g, with g in 1..255
    n = (line - 1) // 255
    g = ((line - 1) % 255) + 1
    return g, "|", f"|{n}"
