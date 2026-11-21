package com.bharatsecure.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test

/**
 * Talks to a running rag/server.py on this PC (http://localhost:8000).
 * Skipped when the server isn't running, so the build never depends on it.
 */
class RagClientTest {
    private val base = "http://localhost:8000"

    private fun serverUp() = runCatching { RagClient.health(base).getBoolean("ok") }.getOrDefault(false)

    @Test
    fun normalizesAddresses() {
        assertEquals("http://10.30.137.250:8000", RagSettings.normalize(" 10.30.137.250:8000/ "))
        assertEquals("https://x.example", RagSettings.normalize("https://x.example"))
        assertEquals("", RagSettings.normalize("  "))
    }

    @Test
    fun scamCallRisesThroughTheServer() {
        assumeTrue("rag server not running on localhost:8000", serverUp())
        val id = RagClient.startSession(base)
        val lines = listOf(
            "hello sir main mumbai cyber crime se inspector sharma bol raha hoon",
            "aapke aadhaar se money laundering case hua hai aapko arrest kiya jayega",
            "video call band mat karna kisi ko mat batana rbi safe account mein paise transfer karo",
        )
        var last: RagUpdate? = null
        for (line in lines) {
            last = RagClient.sendText(base, id, line)
            println("score ${last.score} ${last.level} ${last.typeName} | ${last.reason}")
        }
        RagClient.endSession(base, id)
        assertTrue("expected a scam verdict, got $last", last!!.level == "SCAM")
    }
}
