package com.bharatsecure.app.reports

import android.content.Context
import android.util.Log
import org.json.JSONArray
import java.io.File

/**
 * The saved scam reports, in one JSON file in the app's private storage.
 *
 * Written from the recording service (background thread) and read by the UI,
 * so every access is guarded by [lock]. Reports are never used to block or
 * reject a call - a reported number keeps ringing as normal; [isReported] only
 * lets the app tell the user the number has a history.
 */
object ScamReports {
    private const val TAG = "ScamReports"
    private const val FILE = "scam_reports.json"
    private val lock = Any()

    private fun file(context: Context) = File(context.filesDir, FILE)

    /** Newest first. */
    fun list(context: Context): List<ScamReport> =
        synchronized(lock) { read(context) }.sortedByDescending { it.createdAtMs }

    fun add(context: Context, report: ScamReport) = synchronized(lock) {
        write(context, read(context) + report)
    }

    fun delete(context: Context, id: String) = synchronized(lock) {
        write(context, read(context).filterNot { it.id == id })
    }

    /** Marks a report as passed on to the authorities. */
    fun markForwarded(context: Context, id: String) =
        update(context, id) { it.copy(forwardedAtMs = System.currentTimeMillis()) }

    /** Stores the complaint / acknowledgement number the user got back. */
    fun setReference(context: Context, id: String, reference: String) =
        update(context, id) { it.copy(reference = reference.trim().takeIf { r -> r.isNotBlank() }) }

    private fun update(context: Context, id: String, block: (ScamReport) -> ScamReport) = synchronized(lock) {
        write(context, read(context).map { if (it.id == id) block(it) else it })
    }

    /** True when this call already has a report, so the UI doesn't offer a duplicate. */
    fun hasRecording(context: Context, recordingName: String): Boolean =
        synchronized(lock) { read(context) }.any { it.recordingName == recordingName }

    /**
     * Has this number been reported on this phone before? Used only to show a
     * warning - the call still comes through untouched.
     */
    fun isReported(context: Context, number: String?): Boolean = timesReported(context, number) > 0

    fun timesReported(context: Context, number: String?): Int {
        val key = key(number)
        if (key.length < MIN_DIGITS) return 0
        return synchronized(lock) { read(context) }.count { key(it.number) == key }
    }

    /** Last 10 digits, so "+91 98765 43210" and "09876543210" count as one number. */
    private fun key(number: String?): String {
        val digits = number.orEmpty().filter { it.isDigit() }
        return if (digits.length > 10) digits.takeLast(10) else digits
    }

    private const val MIN_DIGITS = 6

    private fun read(context: Context): List<ScamReport> {
        val f = file(context)
        if (!f.exists()) return emptyList()
        return try {
            val arr = JSONArray(f.readText())
            (0 until arr.length()).mapNotNull { i ->
                runCatching { ScamReport.fromJson(arr.getJSONObject(i)) }.getOrNull()
            }
        } catch (e: Exception) {
            Log.w(TAG, "could not read reports", e)
            emptyList()
        }
    }

    private fun write(context: Context, reports: List<ScamReport>) {
        try {
            val arr = JSONArray()
            reports.forEach { arr.put(it.toJson()) }
            file(context).writeText(arr.toString())
        } catch (e: Exception) {
            Log.e(TAG, "could not save reports", e)
        }
    }
}
