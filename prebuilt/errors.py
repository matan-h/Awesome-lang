import base64
from . import fn,convert4

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


ENGLISH_FREQ_ORDER = " :_'().etaoinshrdlcumwfgypbvkjxqz"
weights = {ch: (len(ENGLISH_FREQ_ORDER) - i) for i, ch in enumerate(ENGLISH_FREQ_ORDER)}

def _score_english(s: str) -> float:
    """
    Score a string based on English-likeness:
      - Count fraction of characters in common English letters and digits
    """
    s = s.lower()
    if not s:
        return 0
    score = sum(weights.get(ch, 0) for ch in s)
    max_score = len(s) * len(ENGLISH_FREQ_ORDER)  # max possible if all letters were 'e'
    return score / max_score

def decode_xor_all(encoded: str, top_n: int = 3) -> None:
    """
    Given an encoded string from encode_xor_readable, try all 255 possible keys (g=1..255)
    and print candidate decoded messages. If encoded used the |...|n form, we reconstruct
    the full line = n*255 + g when printing.
    """
    # parse optional prefix/suffix
    n = 0
    payload = encoded
    if encoded.startswith("|") and "|" in encoded[1:]:
        # suffix is after last '|'
        parts = encoded[1:].rsplit("|", 1)
        if len(parts) == 2 and parts[1].isdigit():
            payload, suffix_n = parts[0], parts[1]
            n = int(suffix_n)
        else:
            # malformed; treat entire string as payload
            payload = encoded

    # decode Ascii85 to raw xored bytes; if that fails, warn and return
    try:
        raw_xored = base64.a85decode(payload.encode("ascii"))
    except Exception as e:
        print("Payload is not valid Ascii85:", e)
        return

    print(f"Decoded payload length (bytes): {len(raw_xored)}")
    print("Trying 255 candidate keys (g = 1..255).  Marker '*' = likely readable candidate.\n")
    candidates = []

    for g in range(1, 256):  # 1..255 inclusive (255 options)
        line = n * 255 + g
        orig_bytes = bytes((b ^ g) for b in raw_xored)
        # Try to decode as UTF-8; use 'replace' to always get a string for printing
        s = orig_bytes.decode("utf-8",errors="replace")

        score = _score_english(s)
        candidates.append((score, line, g, s))
    candidates.sort(reverse=True, key=lambda x: x[0])

    print(f"Top {top_n} likely decodings:\n")
    for score, line, g, s in candidates[:top_n]:
        shown = s if len(s) <= 250 else s[:240] + "…[truncated]"
        print(f"line {line:5d} (key {g:3d}) score {score:.2f}: {shown}")

    print("\nHint: look for entries that look like real error messages (contain 'Error', ':', file names, etc.).")

@fn("e2l")
@convert4()
def e2l(encoded: str, top_n: int = 3):
    return decode_xor_all(encoded,top_n)