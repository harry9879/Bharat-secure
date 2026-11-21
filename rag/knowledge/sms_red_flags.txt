# SMS red-flag guide (given to the LLM on every SMS check)

## Scam types
- **phishing_otp**: link or call-back to "update KYC", "re-verify PAN/Aadhaar", "unblock account/card/SIM", claim a "refund" or "reward points", install an APK; any request to share an OTP/PIN/CVV/password.
- **digital_arrest**: claims to be police, CBI, ED, NCB, customs, cyber cell, TRAI or a court; legal notice, warrant or FIR threats; "call this officer now".
- **banking**: money sent "by mistake", QR/collect request to "receive" money, a loan or cashback that needs a fee or UPI PIN first, fake debit alerts with a "cancel" link.
- **other_scam**: electricity/gas cut "tonight", lottery/KBC prizes, part-time/task jobs with registration fee or Telegram/WhatsApp contact, parcel "on hold" with a fee link, fake relative on a new number asking for money, guaranteed-return investments, passport/insurance/subsidy fees.

## Strong red flags
1. Link on a look-alike or unusual domain (hyphenated brand name, .xyz .top .click .site .co, URL shorteners) in a message claiming to be a bank, government or courier.
2. Urgency plus a threat: "blocked today", "within 2 hours", "tonight", "arrest".
3. A fee must be paid first to receive a prize, loan, job, refund or parcel.
4. Asks you to call a mobile number or move to WhatsApp/Telegram.
5. Asks to share an OTP/PIN/CVV, or to install an app/APK.
6. Sender is a plain mobile number or foreign (+92, +234...) number but pretends to be a bank or government body.

## Genuine SMS (do NOT flag these)
- OTP / transaction alerts from registered headers (like VM-HDFCBK) that say "do not share this OTP" and ask for nothing else.
- Debit/credit alerts, bill reminders, EMI reminders, recharge confirmations, ticket and booking confirmations, delivery updates that link to a verified official site.
- Awareness messages ("we never ask for your OTP").
- Friends and family chatting in Hindi/Hinglish/English with no money, link or secret requested.
- Marketing offers from known brands with no urgency threat and no request for secrets.
A genuine SMS may mention a bank, OTP, parcel or payment; that alone is not a red flag. A message that merely CONTAINS an OTP is normal. What matters is a request for a secret, money, a fee, an app install or a suspicious link, under pressure.
The on-device rule findings are hints, not facts: a rule can fire on a genuine message.
