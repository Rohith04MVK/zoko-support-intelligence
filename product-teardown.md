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

**Change:** Configure voice agents with store knowledge, languages, instructions,
and permitted actions. Make them available in calling and Flows for product discovery,
purchase guidance, order questions, and requested callbacks. Carry chat context into
calls, store summaries/outcomes, and support human handoff. Respect calling permissions,
account health, calling hours, and attempt limits; disclose the automated agent.

**Why / expected impact:** Merchants could handle multiple voice journeys with shared
store context rather than separate manual processes. Pilot task completion, customer
satisfaction, handoff quality, and cost per completed task before claiming ROI.
Technical feasibility and existing capability need validation.

## 5. Add A/B testing for broadcasts

**Change:** Add an A/B Test broadcast type. Merchants could create two versions of a
campaign and choose what to test, such as message copy or CTA, image or carousel
content, discount or offer, and send time. Zoko would randomly split a selected
audience between the variants and compare results using replies, clicks, orders,
revenue, and return on spend.

For larger campaigns, merchants could optionally send each variant to a small sample
first, choose a winning metric such as revenue per recipient, and automatically send
the winning version to the remaining audience.

**Why / expected impact:** Merchants already have the data needed to evaluate
campaigns. Experimentation turns that data into a repeatable optimization loop.
Controlled tests show which message performs better without comparing separate
broadcasts sent to different audiences. Measure experiment adoption, lift between
tested and subsequent campaigns, revenue per recipient, and the percentage of tests
that produce a statistically meaningful winner.
