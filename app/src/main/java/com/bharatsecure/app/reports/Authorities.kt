package com.bharatsecure.app.reports

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.widget.Toast

/**
 * Forwarding a report to the authorities.
 *
 * No Indian authority offers a public API to file a complaint, and filing one
 * on the user's behalf is deliberately not done: a false report has a real
 * cost. So "forward" writes the whole report out as text, copies it to the
 * clipboard and hands it to the share sheet, where the user picks the
 * destination - the cyber-crime portal's e-mail, their local cyber cell, the
 * 1930 helpline follow-up, Sanchar Saathi (Chakshu), or their own records.
 */
object Authorities {
    /** National cyber-crime helpline, dialled from the live-call banner. */
    const val HELPLINE = "1930"

    private const val FOOTER =
        "Requested action: please verify this number and take it out of service so it " +
            "cannot be used for further scam calls.\n" +
            "Official channels: National Cyber Crime Reporting Portal (cybercrime.gov.in), " +
            "helpline 1930, Sanchar Saathi / Chakshu (sancharsaathi.gov.in).\n" +
            "Note: the transcript is machine-generated from the call audio and may contain " +
            "recognition errors. The call recording is kept on the reporting phone and can be " +
            "supplied on request."

    fun subject(report: ScamReport): String =
        "Scam call report - ${report.number} - ${report.whenText()}"

    fun reportText(report: ScamReport): String = buildString {
        appendLine("SCAM CALL REPORT")
        appendLine("Filed from BharatSecure (scam-call detection app)")
        appendLine()
        appendLine("Caller number : ${report.number}")
        report.callerName?.let { appendLine("Caller claimed: $it") }
        appendLine("Call type     : ${report.sourceLabel}")
        appendLine("Date and time : ${report.whenText()}")
        appendLine(
            "Detection     : ${report.levelLabel}" +
                (report.typeLabel?.let { " - $it" } ?: "") +
                " (confidence ${(report.score * 100).toInt()}%)"
        )
        report.reason?.let { appendLine("Why flagged   : $it") }
        report.recordingName?.let { appendLine("Recording     : $it.wav") }
        report.reference?.let { appendLine("Complaint no. : $it") }
        appendLine()
        appendLine("TRANSCRIPT OF THE CALL")
        if (report.transcript.isEmpty()) {
            appendLine("(No transcript was produced for this call.)")
        } else {
            report.transcript.forEach { appendLine(it) }
        }
        appendLine()
        append(FOOTER)
    }

    /**
     * Copies the report and opens the share sheet. Returns false only if the
     * phone has nothing at all to share with.
     */
    fun forward(context: Context, report: ScamReport): Boolean {
        val text = reportText(report)
        copy(context, text, toast = false)
        val send = Intent(Intent.ACTION_SEND)
            .setType("text/plain")
            .putExtra(Intent.EXTRA_SUBJECT, subject(report))
            .putExtra(Intent.EXTRA_TEXT, text)
        val chooser = Intent.createChooser(send, "Forward report to authorities")
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        return try {
            context.startActivity(chooser)
            Toast.makeText(context, "Report also copied, ready to paste on a portal.", Toast.LENGTH_SHORT).show()
            true
        } catch (e: Exception) {
            Toast.makeText(context, "Nothing on this phone can share the report; it was copied instead.",
                Toast.LENGTH_LONG).show()
            false
        }
    }

    fun copy(context: Context, text: String, toast: Boolean = true) {
        context.getSystemService(ClipboardManager::class.java)
            ?.setPrimaryClip(ClipData.newPlainText("Scam call report", text))
        if (toast) Toast.makeText(context, "Report copied", Toast.LENGTH_SHORT).show()
    }
}
