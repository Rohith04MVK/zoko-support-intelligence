# Five Zoko product improvements

Based on exploration of Zoko's broadcast creation/results, abandoned-checkout
playbook, message editor, and calling settings. Benefits below are hypotheses to
measure. Observed behavior is distinguished from proposed extensions; this is not
a claim that every relevant feature or configuration was exhaustively inspected.

## 1. Fix editing of pasted broadcast recipients

**Observed:** In Create Broadcast → Add Contacts → Copy/paste Phone Numbers,
clicking a populated number cell dismissed the contact picker during a correction.
The country-code instructions were already visible; adding the prefix resolved
the unknown-country estimate. The finding is editing friction, not incorrect pricing.

**Change:** Keep the picker open for table interactions, allow inline correction,
and provide Apply changes. Validate corrections and refresh audience/cost information.

**Why / expected impact:** Correcting a typo should not require re-entering the
recipient list. Measure correction completion time and audience-step abandonment.
The dismissal was observed in the test session; reproduce across browsers before
attributing a technical cause.

## 2. Clarify broadcast engagement metrics

**Observed:** A broadcast showed 3 delivered, 1 seen, and 2 link clicks. Link clicked
showed 66.67% above its bar and 200% inside the sequential graphic, without explicit
denominators. [Zoko's guide](https://www.zoko.io/learning-micro-lessons/latest-broadcast-data)
explains that seen counts require read receipts; it does not define link-click
uniqueness or these percentage denominators.

**Change:** Define whether clicks are unique recipients or total events. Label
rate denominators and show confirmed reads and clicks as parallel engagement
metrics. If clicks are unique recipients, show 2 of 3 delivered recipients (66.7%).
Explain that missing read receipts do not establish that a message was unread.

**Why / expected impact:** A 200% Seen → Clicked ratio invites incorrect conclusions.
Test whether merchants can correctly interpret and compare campaign results.
This critiques presentation, not the correctness of underlying event counts.

## 3. Add guided configuration for ready-made playbooks

**Observed:** Recover Abandoned Checkouts — 3 Attempts opens a large canvas of
checkout checks, fetches, variables, tags, and message nodes. Fitting the flow makes
text unreadable; zooming in loses the whole sequence. Panning works and is not a bug.

**Change:** Add a setup panel grouped into First, Second, and Third reminder, with
timing and message choices, a summary of exit conditions, and links to the underlying
nodes. Retain the full canvas for advanced editing.

**Why / expected impact:** A merchant changing reminder timing should not need to
trace supporting data plumbing. Measure setup time, task completion without help,
and accidental changes to supporting logic.

## 4. Offer configurable AI voice agents

**Opportunity:** WhatsApp calling already exists in Zoko. The settings inspected
cover duration and callback-request language. The
[calling-health guide](https://www.zoko.io/learning-micro-lessons/whatsapp-calling-health-status)
covers restrictions, not AI agent functionality. Equivalent AI capabilities elsewhere
remain to be confirmed before treating this as entirely new.

**Change:** Configure voice agents with store knowledge, languages, instructions,
and permitted actions. Make them available in calling and Flows for product discovery,
purchase guidance, order questions, and requested callbacks. Carry chat context into
calls, store summaries/outcomes, and support human handoff. Respect calling permissions,
account health, calling hours, and attempt limits; disclose the automated agent.

**Why / expected impact:** Merchants could handle multiple voice journeys with shared
store context rather than separate manual processes. Pilot task completion, customer
satisfaction, handoff quality, and cost per completed task before claiming ROI.
Technical feasibility and existing capability need validation.

## 5. Preview personalized messages without sending

**Observed:** Inspected broadcast and flow previews displayed variable tokens such
as customer name and checkout-link references. Broadcast QR tests and the flow
Send Message action already exist. A preview rendered with selected customer data
was not visible in the screens inspected; availability elsewhere remains unconfirmed.

**Change:** Add Preview as customer for broadcasts and Preview with sample checkout
for flows. Render names, images, and destination links locally in the editor, flag
missing values, and offer suitable fallback settings before test sending.

**Why / expected impact:** Keep the existing test-send path while reducing the number
of sends needed to check personalization. Measure verification time, test-send
iterations, and missing-variable issues found before activation.
