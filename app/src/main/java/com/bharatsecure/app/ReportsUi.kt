package com.bharatsecure.app

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.bharatsecure.app.reports.Authorities
import com.bharatsecure.app.reports.ScamReport
import com.bharatsecure.app.reports.ScamReports
import com.bharatsecure.app.scam.ScamType

/** Top of the Reports screen: how many scam calls are on record and how many were passed on. */
@Composable
fun ReportsSummaryCard(reports: List<ScamReport>) {
    val forwarded = reports.count { it.forwarded }
    Card(colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Scam call records", fontWeight = FontWeight.Bold)
            Text(
                "${reports.size} scam call${if (reports.size == 1) "" else "s"} saved - " +
                    "$forwarded forwarded to authorities",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                "Every call the detector flags is saved here with the number, the reason and the transcript. " +
                    "Forwarding hands the full report to the cyber-crime portal, the 1930 helpline or " +
                    "Sanchar Saathi, so the number can be taken out of service. Nothing is filed " +
                    "automatically, and no number is ever blocked on this phone.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

/** One saved scam call, with the button that forwards it to the authorities. */
@Composable
fun ReportCard(report: ScamReport, onChanged: () -> Unit) {
    val context = LocalContext.current
    var showDetail by remember { mutableStateOf(false) }
    var reference by remember(report.id, report.reference) { mutableStateOf(report.reference.orEmpty()) }
    var referenceSaved by remember(report.id, report.reference) {
        mutableStateOf(!report.reference.isNullOrBlank())
    }

    val accent = when (report.level) {
        "SCAM" -> Brand.Danger
        "WARNING" -> Brand.Warning
        else -> Brand.Navy
    }

    Card {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(report.number, fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                    Text(
                        "${report.sourceLabel} - ${report.whenText()}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Text(
                    report.levelLabel + report.typeLabel?.let { "\n$it" }.orEmpty(),
                    color = accent,
                    fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.labelMedium,
                )
            }

            if (report.score > 0.0) {
                Text(
                    "Scam score ${(report.score * 100).toInt()}%",
                    style = MaterialTheme.typography.labelSmall,
                    color = accent,
                )
            }

            StatusStrip(report)

            report.reason?.let { Text("Why: $it", style = MaterialTheme.typography.bodyMedium) }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Button(
                    onClick = {
                        Authorities.forward(context, report)
                        ScamReports.markForwarded(context, report.id)
                        onChanged()
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (report.forwarded) Brand.Blue else accent,
                    ),
                ) { Text(if (report.forwarded) "Forward again" else "Forward to authorities") }
                TextButton(onClick = { showDetail = !showDetail }) {
                    Text(if (showDetail) "Hide details" else "Details")
                }
            }

            if (report.forwarded) {
                Row(verticalAlignment = Alignment.Bottom, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = reference,
                        onValueChange = { reference = it; referenceSaved = false },
                        label = { Text("Complaint / acknowledgement no.") },
                        singleLine = true,
                        modifier = Modifier.weight(1f),
                    )
                    TextButton(
                        enabled = !referenceSaved,
                        onClick = {
                            ScamReports.setReference(context, report.id, reference)
                            referenceSaved = true
                            onChanged()
                        },
                    ) { Text(if (referenceSaved) "Saved" else "Save") }
                }
            }

            if (showDetail) {
                HorizontalDivider()
                report.advice?.let { Text("What to do: $it", style = MaterialTheme.typography.bodyMedium) }
                report.recordingName?.let {
                    Text(
                        "Recording: $it.wav (in Recordings)",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Text("Transcript", fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.labelMedium)
                Column(
                    Modifier.fillMaxWidth()
                        .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(8.dp))
                        .padding(12.dp),
                ) {
                    if (report.transcript.isEmpty()) {
                        Text(
                            "(No transcript was produced for this call.)",
                            style = MaterialTheme.typography.bodySmall,
                        )
                    } else {
                        report.transcript.forEach { Text(it, style = MaterialTheme.typography.bodySmall) }
                    }
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    TextButton(onClick = { Authorities.copy(context, Authorities.reportText(report)) }) {
                        Text("Copy report")
                    }
                    TextButton(onClick = {
                        ScamReports.delete(context, report.id)
                        onChanged()
                    }) { Text("Delete", color = Brand.Danger) }
                }
            }
        }
    }
}

/** Green "forwarded" line, or an amber nudge while the report is still only on the phone. */
@Composable
private fun StatusStrip(report: ScamReport) {
    val forwardedAt = report.forwardedText()
    val background: Color
    val text: String
    if (forwardedAt != null) {
        background = Color(0xFFE8F5E9)
        text = "✅ Forwarded to authorities - $forwardedAt" +
            report.reference?.let { "\nComplaint no. $it" }.orEmpty()
    } else {
        background = Color(0xFFFFF3E0)
        text = "⚠️ Not forwarded yet. Forward it so this number can be taken out of service."
    }
    Text(
        text,
        modifier = Modifier.fillMaxWidth().background(background, RoundedCornerShape(8.dp)).padding(10.dp),
        style = MaterialTheme.typography.bodySmall,
    )
}

/**
 * "This number has been reported before" line, shown during a call and on the
 * incoming-call notification. It is a warning only: the call is never blocked,
 * rejected or silenced, and the number keeps ringing normally.
 */
@Composable
fun ReportedNumberWarning(number: String?) {
    val context = LocalContext.current
    val times = remember(number) { ScamReports.timesReported(context, number) }
    if (times == 0) return
    Text(
        "⚠️ This number was reported as a scam " +
            (if (times == 1) "once" else "$times times") + " on this phone.",
        modifier = Modifier.fillMaxWidth()
            .background(Color(0xFFFFEBEE), RoundedCornerShape(8.dp))
            .padding(10.dp),
        style = MaterialTheme.typography.bodySmall,
        color = Brand.Danger,
        fontWeight = FontWeight.SemiBold,
    )
}

/** Shown in the Recordings list, for a call the detector did not flag by itself. */
@Composable
fun ReportThisCallButton(rec: Recording, onReported: () -> Unit) {
    val context = LocalContext.current
    var reported by remember(rec.name) { mutableStateOf(ScamReports.hasRecording(context, rec.name)) }
    if (reported) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Spacer(Modifier.width(8.dp))
            Text("✅ In Reports", style = MaterialTheme.typography.labelMedium, color = Brand.Safe)
        }
        return
    }
    TextButton(onClick = {
        ScamReports.add(context, ScamReport.fromRecording(rec))
        reported = true
        onReported()
    }) { Text("Report as scam") }
}

/**
 * "File a scam report": the form for a scam call the app never heard - the
 * caller, the kind of scam and what happened, in the user's own words. It
 * saves a report identical to a detected one, so the same "Forward to
 * authorities" button works on it afterwards.
 */
@Composable
fun NewReportCard(onSaved: () -> Unit) {
    val context = LocalContext.current
    var open by remember { mutableStateOf(false) }
    var name by remember { mutableStateOf("") }
    var number by remember { mutableStateOf("") }
    var type by remember { mutableStateOf(ScamType.PHISHING_OTP) }
    var description by remember { mutableStateOf("") }

    // A report with no caller and no story is of no use to anyone.
    val ready = description.isNotBlank() && (name.isNotBlank() || number.isNotBlank())

    fun save(forward: Boolean) {
        val report = ScamReport.manual(
            callerName = name,
            number = number,
            type = type.label,
            description = description,
        )
        ScamReports.add(context, report)
        if (forward) {
            // Hands the finished report to the share sheet: the user picks the
            // portal, the cyber cell or their own records. Nothing is filed
            // automatically.
            Authorities.forward(context, report)
            ScamReports.markForwarded(context, report.id)
        } else {
            Toast.makeText(context, "Report saved. Forward it any time from its card.", Toast.LENGTH_SHORT).show()
        }
        name = ""
        number = ""
        description = ""
        type = ScamType.PHISHING_OTP
        open = false
        onSaved()
    }

    Card(colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("File a scam report", fontWeight = FontWeight.Bold)
                    Text(
                        "For a scam call the app did not hear - write it up and send it on.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                TextButton(onClick = { open = !open }) { Text(if (open) "Close" else "New report") }
            }

            if (open) {
                HorizontalDivider()

                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Caller name or company") },
                    placeholder = { Text("e.g. HDFC verification team") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = number,
                    onValueChange = { number = it },
                    label = { Text("Phone number") },
                    placeholder = { Text("+91 ...") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                    modifier = Modifier.fillMaxWidth(),
                )

                Text(
                    "Type of scam",
                    fontWeight = FontWeight.SemiBold,
                    style = MaterialTheme.typography.labelMedium,
                )
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    ScamType.entries.chunked(2).forEach { pair ->
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            pair.forEach { t ->
                                FilterChip(
                                    selected = type == t,
                                    onClick = { type = t },
                                    label = { Text(t.label, maxLines = 1) },
                                    modifier = Modifier.weight(1f),
                                )
                            }
                            if (pair.size == 1) Spacer(Modifier.weight(1f))
                        }
                    }
                }

                OutlinedTextField(
                    value = description,
                    onValueChange = { description = it },
                    label = { Text("What happened?") },
                    placeholder = {
                        Text("What they asked for, what they threatened, how much money was involved.")
                    },
                    minLines = 3,
                    modifier = Modifier.fillMaxWidth(),
                )

                Text(
                    type.advice,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Button(
                        onClick = { save(forward = true) },
                        enabled = ready,
                        colors = ButtonDefaults.buttonColors(containerColor = Brand.Danger),
                    ) { Text("Report to authorities") }
                    TextButton(onClick = { save(forward = false) }, enabled = ready) { Text("Save only") }
                }

                if (!ready) {
                    Text(
                        "Add the caller's name or number, and a short description, to file the report.",
                        style = MaterialTheme.typography.labelSmall,
                        color = Brand.Warning,
                    )
                }
            }
        }
    }
}
