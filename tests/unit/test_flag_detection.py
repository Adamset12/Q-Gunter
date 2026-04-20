import re
import pytest

FLAG_PATTERNS = [
    r"flag\{[^\}]+\}",
    r"FLAG\{[^\}]+\}",
    r"HTB\{[^\}]+\}",
    r"CTF\{[^\}]+\}",
    r"[A-Za-z0-9_]+\{[^\}]+\}",
    r"\b[a-f0-9]{32}\b",
]

def detect_flags(text: str) -> list[str]:
    flags = []
    for pattern in FLAG_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if match.group(0) not in flags:
                flags.append(match.group(0))
    return flags


@pytest.mark.unit
class TestFlagDetection:
    def test_flag_lowercase(self):
        assert "flag{s3cr3t}" in detect_flags("Found flag{s3cr3t}")

    def test_htb(self):
        assert "HTB{h4ck}" in detect_flags("HTB{h4ck}")

    def test_hex_32(self):
        assert "0123456789abcdef0123456789abcdef" in detect_flags(
            "Flag: 0123456789abcdef0123456789abcdef"
        )

    def test_multiple(self):
        text = "flag{one} and HTB{two} and 0123456789abcdef0123456789abcdef"
        flags = detect_flags(text)
        assert len(flags) >= 3

    def test_no_flags(self):
        flags = detect_flags("Just normal text here")
        assert not any(f.startswith(("flag{", "FLAG{", "HTB{")) for f in flags)

    def test_deduplication(self):
        flags = detect_flags("flag{dup} and again flag{dup}")
        assert flags.count("flag{dup}") == 1
