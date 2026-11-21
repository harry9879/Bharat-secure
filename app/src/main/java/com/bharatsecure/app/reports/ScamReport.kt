package com.bharatsecure.app.reports

import com.bharatsecure.app.Recording
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID

/**
 * One scam call, kept after the call ends so the user can forward it to the
 * authorities. Written by ProtectionService when a call's verdict is not SAFE,
 * or by the user from the Recordings list.
 *
 * Nothing here blocks or filters calls: a reported number still rings normally.
 * The report only records what was heard and lets the user pass it on.
 */
data class ScamReport(
    val id: String,
    val createdAtMs: Long,
    /** Caller number as Android reported it, or "Unknown number". */
    val number: String,
    /** Who the caller claimed to be ("HDFC verification team"), when the user typed it in. */
    val callerName: String? = null,
    /** "Phone call" / "WhatsApp call" / "Manual". */
    val sourceLabel: String,
    /** SCAM, WARNING (from the detector) or USER (marked by the user). */
    val level: String,
    val typeLabel: String?,
    /** Scam score at the end of the call, 0..1. */
    val score: Double,
    val reason: String?,
    val advice: String?,
    val transcript: List<String>,
    /** Links to the .wav/.txt in Recordings, when the call was recorded. */
    val recordingName: String?,
    /** When the user forwarded it; null while it has not been forwarded. */
    val forwardedAtMs: Long? = null,
    /** Complaint / acknowledgement number the user types back in. */
    val reference: String? = null,
) {
    val forwarded: Boolean get() = forwardedAtMs != null

    val levelLabel: String get() = when (level) {
        "SCAM" -> "Scam call"
        "WARNING" -> "Possible scam"
        else -> "Marked by you"
    }

    fun whenText(): String = STAMP.format(Date(createdAtMs))

    fun forwardedText(): String? = forwardedAtMs?.let { STAMP.format(Date(it)) }

    fun toJson(): JSONObject = JSONObject().apply {
        put("id", id)
        put("createdAtMs", createdAtMs)
        put("number", number)
        putOpt("callerName", callerName)
        put("sourceLabel", sourceLabel)
        put("level", level)
        putOpt("typeLabel", typeLabel)
        put("score", score)
        putOpt("reason", reason)
        putOpt("advice", advice)
        put("transcript", JSONArray(transcript))
        putOpt("recordingName", recordingName)
        putOpt("forwardedAtMs", forwardedAtMs)
        putOpt("reference", reference)
    }

    companion object {
        private val STAMP = SimpleDateFormat("d MMM yyyy, h:mm a", Locale.US)

        /** Keeps the saved file small; a long call is trimmed to its last lines. */
        const val MAX_TRANSCRIPT_LINES = 60

        fun fromJson(o: JSONObject): ScamReport {
            val arr = o.optJSONArray("transcript")
            return ScamReport(
                id = o.optString("id").ifBlank { UUID.randomUUID().toString() },
                createdAtMs = o.optLong("createdAtMs", System.currentTimeMillis()),
                number = o.optString("number").ifBlank { "Unknown number" },
                callerName = o.optString("callerName").takeIf { it.isNotBlank() },
                sourceLabel = o.optString("sourceLabel").ifBlank { "Phone call" },
                level = o.optString("level").ifBlank { "USER" },
                typeLabel = o.optString("typeLabel").takeIf { it.isNotBlank() },
                score = o.optDouble("score", 0.0),
                reason = o.optString("reason").takeIf { it.isNotBlank() },
                advice = o.optString("advice").takeIf { it.isNotBlank() },
                transcript = (0 until (arr?.length() ?: 0)).map { arr!!.optString(it) },
                recordingName = o.optString("recordingName").takeIf { it.isNotBlank() },
                forwardedAtMs = o.optLong("forwardedAtMs", 0L).takeIf { it > 0L },
                reference = o.optString("reference").takeIf { it.isNotBlank() },
            )
        }

        /**
         * A report the user files by hand from the Recordings list, for a call
         * the detector did not flag. The caller and the verdict are read back
         * out of the header ProtectionService writes into the .txt file.
         */
        fun fromRecording(rec: Recording): ScamReport {
            val text = if (rec.transcript.exists()) rec.transcript.readText() else ""
            val header = text.substringBefore("\n\n")
            fun field(name: String): String? = header.lineSequence()
                .firstOrNull { it.startsWith("$name:") }
                ?.substringAfter(":")?.trim()?.takeIf { it.isNotBlank() && it != "unknown" }
            val ragLine = header.lineSequence().firstOrNull { it.startsWith("Laptop RAG") }
            val body = text.substringAfter("\n\n", "")
                .lineSequence()
                .map { it.trim() }
                .filter { it.isNotEmpty() && !it.startsWith("(") }
                .toList()
            return ScamReport(
                id = UUID.randomUUID().toString(),
                createdAtMs = rec.audio.lastModified().takeIf { it > 0L } ?: System.currentTimeMillis(),
                number = field("Caller") ?: "Unknown number",
                sourceLabel = field("Source") ?: "Phone call",
                level = "USER",
                typeLabel = null,
                score = SCORE_IN_RAG_LINE.find(ragLine.orEmpty())?.groupValues?.get(1)?.toDoubleOrNull() ?: 0.0,
                reason = "Marked as a scam by the user from the recording list.",
                advice = null,
                transcript = body.takeLast(MAX_TRANSCRIPT_LINES),
                recordingName = rec.name,
            )
        }

        private val SCORE_IN_RAG_LINE = Regex("""score ([0-9.]+)""")

        /**
         * A report the user writes out by hand on the Reports screen, for a scam
         * call the app never heard - the caller, what kind of scam it was and
         * what happened, in their own words. Saved exactly like a detected one,
         * so it forwards to the authorities through the same button.
         */
        fun manual(
            callerName: String,
            number: String,
            type: String,
            description: String,
        ): ScamReport = ScamReport(
            id = UUID.randomUUID().toString(),
            createdAtMs = System.currentTimeMillis(),
            number = number.trim().ifBlank { "Unknown number" },
            callerName = callerName.trim().takeIf { it.isNotBlank() },
            sourceLabel = "Reported by hand",
            level = "USER",
            typeLabel = type.trim().takeIf { it.isNotBlank() },
            score = 0.0,
            reason = description.trim().takeIf { it.isNotBlank() },
            advice = null,
            transcript = emptyList(),
            recordingName = null,
        )
    }
}
