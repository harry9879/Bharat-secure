"""Devanagari -> Roman Hinglish, so every transcript ends up in one form.

Python port of app/.../scam/Transliterator.kt (keep the two in step):
  - English words written in Hindi script, and everyday Hindi words, come
    from a dictionary (अरेस्ट -> arrest, नहीं -> nahi);
  - everything else is converted letter by letter, dropping the silent
    inherent "a" (आपको -> aapko, करना -> karna).
Roman text passes through unchanged.
"""

import re

LOANWORDS = {
    "अरेस्ट": "arrest", "अरेस्टेड": "arrested", "पुलिस": "police", "ऑफिसर": "officer", "ओटीपी": "otp",
    "पिन": "pin", "पासवर्ड": "password", "अकाउंट": "account", "एकाउंट": "account", "बैंक": "bank",
    "पेमेंट": "payment", "लिंक": "link", "कस्टम्स": "customs", "कस्टम": "customs", "पार्सल": "parcel",
    "कूरियर": "courier", "केस": "case", "वीडियो": "video", "कॉल": "call", "आधार": "aadhaar", "केवाईसी": "kyc",
    "यूपीआई": "upi", "रिफंड": "refund", "लोन": "loan", "सीबीआई": "cbi", "ड्रग्स": "drugs", "ड्रग": "drugs",
    "मनी": "money", "लॉन्ड्रिंग": "laundering", "डिजिटल": "digital", "वारंट": "warrant", "कोर्ट": "court",
    "एफआईआर": "fir", "साइबर": "cyber", "क्राइम": "crime", "टैक्स": "tax", "इनकम": "income",
    "डिपार्टमेंट": "department", "कार्ड": "card", "क्रेडिट": "credit", "डेबिट": "debit", "नंबर": "number",
    "मोबाइल": "mobile", "फोन": "phone", "फ़ोन": "phone", "मैसेज": "message", "कोड": "code", "ऐप": "app",
    "डाउनलोड": "download", "इंस्टॉल": "install", "क्लिक": "click", "सर": "sir", "मैडम": "madam", "सिम": "sim",
    "कंपनी": "company", "ट्रांसफर": "transfer", "अमाउंट": "amount", "फीस": "fee", "चार्ज": "charge",
    "जॉब": "job", "लॉटरी": "lottery", "कैशबैक": "cashback", "ऑफर": "offer", "ब्लॉक": "block",
    "वेरिफिकेशन": "verification", "वेरीफाई": "verify", "अपडेट": "update", "डिटेल्स": "details",
    "सिक्योरिटी": "security", "सेफ": "safe", "आरबीआई": "rbi", "एसबीआई": "sbi", "पेटीएम": "paytm",
    "फोनपे": "phonepe", "गूगल": "google", "पे": "pay", "क्यूआर": "qr", "स्कैन": "scan", "रुपये": "rupees",
    "रुपए": "rupees", "लाख": "lakh", "हजार": "hazaar", "हज़ार": "hazaar", "प्लीज": "please", "प्लीज़": "please",
    "ओके": "ok", "हेलो": "hello", "हैलो": "hello", "इंस्पेक्टर": "inspector", "नारकोटिक्स": "narcotics",
    "कैमरा": "camera", "स्काइप": "skype", "सेटलमेंट": "settlement",
    "हम": "hum", "तुम": "tum", "है": "hai", "हैं": "hain", "में": "mein", "नहीं": "nahi", "मैं": "main",
    "क्या": "kya", "यह": "ye", "ये": "ye", "वह": "woh", "वो": "woh", "और": "aur", "कि": "ki", "की": "ki",
    "को": "ko", "से": "se", "का": "ka", "के": "ke", "भी": "bhi", "जी": "ji", "आप": "aap", "आपका": "aapka",
    "आपको": "aapko", "आपके": "aapke", "आपकी": "aapki", "अभी": "abhi", "हाँ": "haan", "हां": "haan",
    "ठीक": "theek", "मत": "mat", "पैसे": "paise", "पैसा": "paisa", "किसी": "kisi", "कोई": "koi",
    "दीजिए": "dijiye", "कीजिए": "kijiye", "बताइए": "bataiye", "बताइये": "bataiye", "हूँ": "hoon",
    "हूं": "hoon", "घर": "ghar", "वालों": "walon", "बताना": "batana", "जल्दी": "jaldi", "तुरंत": "turant",
}
VOWELS = {"अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo", "ऋ": "ri", "ए": "e", "ऐ": "ai",
          "ओ": "o", "औ": "au", "ऑ": "o", "ऍ": "e"}
MATRAS = {"ा": "aa", "ि": "i", "ी": "i", "ु": "u", "ू": "oo", "ृ": "ri", "े": "e", "ै": "ai", "ो": "o",
          "ौ": "au", "ॉ": "o", "ॅ": "e"}
CONSONANTS = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh",
              "ञ": "n", "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d",
              "ध": "dh", "न": "n", "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r",
              "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s", "ह": "h", "ळ": "l"}
NUKTA = {"क": "q", "ख": "kh", "ग": "gh", "ज": "z", "ड": "r", "ढ": "rh", "फ": "f", "य": "y"}
NUKTA_SIGN, VIRAMA = "़", "्"
WORD = re.compile(r"[ऀ-ॿ]+")


def word(w: str) -> str:
    if w in LOANWORDS:
        return LOANWORDS[w]
    units = []  # [sound, has_schwa, is_vowel]
    i = 0
    while i < len(w):
        c = w[i]
        if c in CONSONANTS:
            sound = CONSONANTS[c]
            if i + 1 < len(w) and w[i + 1] == NUKTA_SIGN:
                sound = NUKTA.get(c, sound)
                i += 1
            nxt = w[i + 1] if i + 1 < len(w) else None
            if nxt == VIRAMA:
                units.append([sound, False, False]); i += 1
            elif nxt in MATRAS:
                units.append([sound, False, False]); units.append([MATRAS[nxt], False, True]); i += 1
            else:
                units.append([sound, True, False])
        elif c in VOWELS:
            units.append([VOWELS[c], False, True])
        elif c in ("ं", "ँ"):
            units.append(["n", False, False])
        elif c == "ः":
            units.append(["h", False, False])
        elif "०" <= c <= "९":
            units.append([str(ord(c) - ord("०")), False, False])
        i += 1
    n = len(units)
    keep = [u[1] for u in units]
    is_vowel = [u[2] for u in units]
    if n > 1 and keep[-1]:
        keep[-1] = False
    vowel_at = lambda k: 0 <= k < n and (is_vowel[k] or keep[k])
    for k in range(n - 2, 0, -1):
        if keep[k] and vowel_at(k - 1) and not is_vowel[k + 1] and (vowel_at(k + 1) or (k + 2 < n and is_vowel[k + 2])):
            keep[k] = False
    out = []
    for k, (sound, _, _) in enumerate(units):
        out.append("a" if (k == n - 1 and sound == "aa" and n > 1) else sound)
        if keep[k]:
            out.append("a")
    return "".join(out)


def to_roman(text: str) -> str:
    """Converts every Devanagari word; other text is left as it is."""
    return WORD.sub(lambda m: word(m.group(0)), text)
