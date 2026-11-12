# Annotated walkthrough: five alerts

These five alerts show how the assistant behaves, not how often. Alert 4762 is the first one in the queue. The other four were picked from the 100 alerts I reviewed by hand to show different failure types, so they are not a random sample. Rates are in the README and `docs/results.md`. Fraud labels are not used or shown anywhere here.

Each section covers what the assistant said, what the evidence shows, what went wrong, and what the analyst's screen lets them catch.

## Alert 4762: a coarse history cited as a reason to escalate

**Suggested:** escalate.

**What it said.** Two reasons to escalate: the risk score, and "No prior activity in history_30d; first transaction for this customer."

**What the evidence shows.** The 30-day count is 0. The customer group count is only 10, and the same device and email appear in 2,484 transactions across 839 customers. There are no prior alerts.

**What went wrong.** A zero count over 30 days does not mean this is the customer's first transaction, and the same output says many customers share this profile. The model flags the weakness in its reliability note, then uses the same history as a reason to escalate. This pattern appeared in 37 of the 100 reviewed alerts. The validator passed the output with one warning, about the word "high".

**What the analyst sees.** The "How reliable is the history?" box says coarse, and the rows behind the claim are highlighted next to the shared-profile counts. An analyst who reads them would not treat "first transaction" as fact.

## Alert 2936: no unsupported claims, still misleading

**Suggested:** escalate. Risk score 0.18.
**My review:** 0 unsupported of 15 claims; framing misleading; disposition unsure.

**What it said.** Escalate because the customer has 5 prior alerts, the most recent on 2018-04-13. Against: a single device type and "no shared device-email activity". Closing note: a "recent alert cluster" warrants review.

**What the evidence shows.** The transaction is on 2018-04-20 and its device type is missing. The five prior alerts run from April 11 to April 13. Four of the five carry an identical score, and two of those are about four minutes apart.

**What went wrong.** Every number matches the packet, so the claim-level check is clean. Three things still mislead:
- With the device missing, a device-and-email match count of 0 means no match could be made. It is not evidence that nothing was shared, yet it is offered as reassurance.
- The "recent" cluster is about a week before the transaction.
- The output counts five prior alerts. Four share one score, which could mean repeats rather than five separate signals. The output does not say.

**What the analyst sees.** The missing device type is shown in amber, and the prior-alert dates and scores are listed.

**Takeaway.** "No unsupported claims" does not mean "safe to rely on". My "misleading" label is the less reliable of my two scores (see `docs/results.md`), so treat this as an example, not a rate.

## Alert 809: a precise-sounding number that was wrong

**Suggested:** escalate.
**My review:** 3 unsupported of 16 claims; framing misleading; disposition reasonable.

**What it said.** Reason to escalate: "Five prior alerts same date, three with identical risk score 0.337156614."

**What the evidence shows.** All five prior alerts are on April 5, between 02:59 and 05:04. Only two of them carry that score. The other prior alerts have 0.3103358809 (two) and 0.1650091289 (one). The count of three is right only if the current alert is included.

**What went wrong.**
- The miscount got past the validator. My note is that the spelled-out "three" bypassed its number check.
- "Typical" is the whole reason given for the first false-positive point. Nothing in the packet says what is typical.
- "Established pattern" for 2 device types and 10 email domains is not supported by the evidence, and 10 domains in 30 days is not obviously reassuring.
- An escalate reason cites 404 transactions in 30 days, while the same output says 1,156 customers share the device and email, so the 404 may not belong to one person.

**What the analyst sees.** The prior-alert list shows each score, so a careful analyst can count the matches.

**Takeaway.** Escalating looks reasonable here, but two of the four stated reasons are unsupported. Reasons that get pasted into a case note would carry the errors forward.

## Alert 3738: a rule the model broke and the validator missed

**Suggested:** request more info. Risk score 0.22.
**My review:** 1 unsupported of 7 claims; framing misleading; disposition sensible.

**What it said.** Escalate reasons include "5 prior alerts from same rule within 2 days" and "amount 53.611 below max_amount 217.512".

**What went wrong.**
- "Within 2 days" is a computed duration, which the prompt forbids. It is roughly right here, but computed values are not in the evidence the analyst sees. The validator accepted it.
- An amount below the 30-day maximum is reassuring, yet it is listed as a reason to escalate.
- "Risk score is low" is the whole first false-positive reason, with no threshold in the packet to say what "low" means.
- The confidence note talks about a common device and email profile but cites only the risk score and prior alerts.

**Takeaway.** Several small errors, and the model chose the cautious middle option, which I scored as sensible. One case does not show that it does this reliably. In `docs/results.md`, computed durations appear in 13 of 100 reviewed alerts, and v3 adds a code rule for them.

## Alert 1636: a reasonable close with a wrong label

**Suggested:** close as false positive. Risk score 0.16.
**My review:** 1 unsupported of 5 claims; framing not misleading; disposition sensible.

**What it said.** No reasons to escalate. For false positive: the amount 46.11 is below the 30-day maximum of 52.381, a single device type and email domain, and no prior alerts.

**What the evidence shows.** No prior alerts, no device-and-email matches, and a customer group count of 80.

**What went wrong.** The output calls the history "coarse", but a group of 80 is far below the 500 threshold used to define coarse. Also, "no escalation signals" is backed only by the risk score, though the other facts support it. Not scored as an error, but worth knowing: there are only 4 transactions in the 30-day window, so "single device type" rests on four transactions. The output does not say that.

**Why it is here.** Only 8 of the 163 stored outputs suggest closing, and closing is the action that ends review. The recommendation looks reasonable, but the reliability label is wrong, and an analyst who believes it might distrust a good call. The screen does not pre-select a decision, and disagreeing with the model requires a written reason.

## What these have in common

- The numbers are mostly right. The mistakes are in inference and framing: a missing value read as reassurance, a count that sounds exact but is off by one, a reliability label applied wrongly.
- The validator checks what code can check: that citations exist and that numbers appear in the packet. It cannot judge whether an argument makes sense. Alert 809 shows the limit: a miscounted prior-alert tally still passed.
- That gap is why the screen puts the evidence beside every claim, marks missing values in amber, and leaves the final call to the analyst.

## What I would change

The v3 plan in `docs/results.md` follows from these cases: reject outputs that cite history flagged as coarse, add code checks for computed durations, currency symbols and comparison words, treat a missing device type as missing, and collapse near-duplicate prior alerts. Then re-run the same 100 alerts to compare.
