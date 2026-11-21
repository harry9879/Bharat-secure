package com.bharatsecure.app.scam

import org.junit.Assert.assertEquals
import org.junit.Test

class TransliteratorTest {

    @Test
    fun dropsSilentA() {
        assertEquals("karna", Transliterator.word("करना"))
        assertEquals("samajh", Transliterator.word("समझ"))
        assertEquals("bhej", Transliterator.word("भेज"))
        assertEquals("raha", Transliterator.word("रहा"))
        assertEquals("rahe", Transliterator.word("रहे"))
        assertEquals("kya", Transliterator.word("क्या"))
    }

    @Test
    fun loanwordsBecomeEnglish() {
        assertEquals("arrest", Transliterator.word("अरेस्ट"))
        assertEquals("otp", Transliterator.word("ओटीपी"))
        assertEquals("police", Transliterator.word("पुलिस"))
    }

    @Test
    fun romanTextIsUntouched() {
        assertEquals("share the otp abhi", Transliterator.toRoman("share the otp abhi"))
        assertEquals("aapka otp batao", Transliterator.toRoman("आपका otp batao"))
    }

    @Test
    fun realCallFromTheApp() {
        // What Vosk wrote during the WhatsApp test call (Hindi model, Devanagari).
        val vosk = "आपने अपना इनकम टैक्स नहीं भरा था हम आपको अरेस्ट कर रहे हैं अपना फोन छोड़कर कहीं नहीं " +
            "जा सकते पेमेंट करनी होगी मैं आपको एक लिंक भेज रहा हूँ उस लिंक पर जाकर पेमेंट कर दीजिए"
        val roman = PhoneText.fromTranscript(vosk)
        println(roman)
        assertEquals(true, roman.contains("hum aapko arrest kar rahe hain"))
        assertEquals(true, roman.contains("payment"))
    }
}
