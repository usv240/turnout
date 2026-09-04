# Shared Design System

> This file is the design contract shared by two projects built for the same hackathon,
> Turnout and Tally. It is committed to both repositories so that either one can be read on
> its own. Where it says "both projects", those are the two.


One design language for both projects so a judge who opens both sees the same standard of care. This document is the contract for every page, component, message, and spoken line.

Version 2. Sections 1 to 8 cover the web surfaces. Sections 9 to 16 were added after a second research pass and cover the product experience for the three constrained users: a chief glancing at a phone, a volunteer on SMS, and a provider with no free hands. Section 17 is the ceiling checklist for the Design criterion.

Design goals, in priority order:

1. A first-time visitor, technical or not, understands what the project is, who it is for, and why it matters within 30 seconds, without scrolling past the first screen.
2. A judge can find every item the rubric asks for from a single "For judges" link.
3. Every feature has an "i" button that explains what it is and why it exists, in one or two plain sentences.
4. The agent stays in the periphery. It earns the user's attention only when it must, and it says why.
5. Light and dark themes are first-class. Mobile and desktop are first-class.
6. Accessible to WCAG 2.2 AA and usable by people over 50 with reading glasses and cold hands.
7. Fast. Largest Contentful Paint under 2.5 seconds on a mid-range phone over 4G.

---

## 1. Research-backed principles we apply

| Principle | Source | How we apply it |
|---|---|---|
| Recognition over recall | Nielsen's usability heuristics | Every control is labeled in words, never icon-only. The "i" button reveals context in place instead of sending users to a docs page. |
| Progressive disclosure | Nielsen Norman Group | The landing page shows the story first. Technical depth is one click away, never in the way. |
| Inverted pyramid | Nielsen Norman Group web writing research | The first sentence of every section carries the conclusion. Details follow. |
| F-pattern and scanning | Nielsen Norman Group eye-tracking studies | Headings state the takeaway. Bolded first words on bullets. Left-aligned text. No centered paragraphs. |
| Plain language | US Plain Writing Act guidance, Hemingway grade 6 to 8 target | Short sentences. Common words. Domain terms get an "i" button on first use. |
| Fitts's law | HCI | Touch targets are at least 48 by 48 CSS pixels on product screens (see section 14), 44 on marketing pages. Primary actions sit near the thumb on mobile. |
| Hick's law | HCI | At most two calls to action above the fold. Menus have at most six items. |
| Aesthetic-usability effect | Kurosu and Kashimura | Consistent spacing scale, one type family, restrained color. Premium comes from restraint. |
| Trust signals | Stanford Web Credibility research | Citations with links. Named data sources. A visible "what this does not do" section. Real traces, not mockups. |
| Dark mode done properly | Material Design and Apple HIG guidance | Dark surfaces are desaturated near-black, not pure black. Elevation shown with lighter surfaces, not shadows. Reduced saturation for accents in dark mode. |
| Calm technology | Weiser and Brown, Xerox PARC, 1995; Amber Case, 2015 | Section 10. The agent lives in the periphery and moves to the center only for a real decision. |
| Human-AI interaction guidelines | Amershi et al., CHI 2019 (Microsoft) | Section 9. All 18 guidelines mapped to concrete behaviors. |
| Interruption cost | Gloria Mark, UC Irvine | Section 13. Interruptions are budgeted and batched because recovery from one takes about 23 minutes. |
| Designing for older adults | Nielsen Norman Group senior usability research; touchscreen guideline reviews | Section 14. Larger type, larger targets, no sliders or dropdowns, visible navigation. |

---

## 2. Design tokens

Both projects share the token structure. Each project overrides only the accent hue.

```
Color (light)
  --bg:            #FAFAF8   (warm off-white ground)
  --surface:       #FFFFFF
  --surface-2:     #F3F2EE
  --text:          #1A1A1A
  --text-muted:    #5C5C57
  --border:        #E4E2DC
  --accent:        project-specific (see below)
  --accent-text:   #FFFFFF
  --success:       #1F7A4D
  --warning:       #9A6700
  --danger:        #B42318
  --info:          #175CD3

Color (dark)
  --bg:            #121212
  --surface:       #1C1C1C
  --surface-2:     #262626
  --text:          #ECECEA
  --text-muted:    #A3A39E
  --border:        #2E2E2E
  --accent:        project-specific, lightened for contrast
  --accent-text:   #0E0E0E
  --success:       #4CC38A
  --warning:       #F5B324
  --danger:        #F97066
  --info:          #84AEFF

Accent
  Turnout:  light #B3261E (engine red), dark #F26D63
  Tally:    light #0F6E56 (deep green), dark #4FC79E

Status colors are never the only signal. Every status also has a word and a shape
(circle low, triangle elevated, diamond high, octagon critical).

Typography
  Family:        Inter (UI and body), JetBrains Mono (code, traces)
  Scale (rem):   0.75, 0.875, 1, 1.125, 1.25, 1.5, 2, 2.5, 3.25
  Base size:     16 px on marketing pages, 18 px on product screens (section 14)
  Line height:   1.5 body, 1.2 headings
  Max line width: 68 characters for body text

Spacing (px):   4, 8, 12, 16, 24, 32, 48, 64, 96
Radius (px):    6 (controls), 12 (cards), 999 (pills)
Shadow:         light mode only, one level: 0 1px 2px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04)
Motion:         150 ms ease-out for state changes; 250 ms for panels; all disabled under prefers-reduced-motion
```

Contrast is verified for every text and background pair at 4.5:1 minimum (3:1 for large text), in
both themes. `tools/a11y_audit.py` in each repository runs axe-core over every page, in both
themes, at 390, 768 and 1280 pixels wide, which is 30 page renders per project, and fails on any
WCAG 2.2 A or AA violation including contrast. It runs in CI on every push and it is currently
clean on both projects.

Theme behavior:

- **Light is the default.** Following `prefers-color-scheme` means a person whose laptop is in dark
  mode meets the product in a theme they never chose for it, and a first impression should be the
  one the design was drawn in. The toggle still offers System, it is just no longer what you get
  without asking.
- A toggle offers Light, Dark, System. The choice persists in `localStorage` across pages.
  Below 640px the header toggle is hidden and the footer one carries it, because a brand, a
  three-way toggle and a call to action do not fit in 390px.
- The `<html>` element gets `data-theme="light|dark"`. Tokens are defined on `:root` for light, redefined under `[data-theme="dark"]`, and also under `@media (prefers-color-scheme: dark)` guarded by `:root:not([data-theme="light"])`.
- No flash of wrong theme: an inline script sets `data-theme` before first paint.
- Images and diagrams have light and dark variants, or use currentColor SVG.

---

## 3. Layout and responsiveness

Breakpoints: 360 (small phone), 640 (phone), 768 (tablet), 1024 (laptop), 1280 (desktop).

- Mobile first. Single column below 768. Two columns from 768. Max content width 1200.
- Navigation: at most five items in the header, per Hick's law, and each one a word rather than an
  icon. The header nav collapses below 1040px because word labels need the room. Every page
  below the landing page carries a back link at the top of its content, where a person looks
  for it, not only in the footer.
- Tables and code blocks scroll horizontally inside their own container. The page body never
  scrolls sideways, and that is enforced rather than hoped for: grid and flex children get
  `min-width: 0`, because the default `min-width: auto` lets one long line, such as a curl
  command, push a whole page sideways. Checked at 1920, 1280, 1024, 768, 390 and 360.
- Sticky "Try the live demo" button on mobile, bottom right, above the bottom bar.
- Diagrams are SVG, pan and zoom on touch, with a "View full size" link.

---

## 4. The "i" button (InfoTip) component

Purpose: let anyone learn what a feature is and why it exists without leaving the page.

Behavior:

- A 20 px circular button with a lowercase "i" glyph, placed immediately after the label it explains.
- `aria-label="More about {label}"`. Opens a popover on click or Enter or Space. Closes on Escape, on outside click, or on focus leaving the popover.
- Popover content is at most three short sentences: what it is, why it exists, and optionally a "Learn more" link to the docs anchor or a citation.
- On touch devices the popover opens as a bottom sheet for readability.
- Popovers never contain interactive controls other than the "Learn more" link.
- Content lives in a single `infotips.json` per project so the copy can be reviewed in one place.

Where it is mandatory:

- Every domain term on first use (mutual aid, second due, NERIS, CACFP, meal component, ratio, subsidy authorization).
- Every metric on a dashboard (risk score, expected calls, reimbursable, interrupt count).
- Every agent name in the architecture view.
- Every AgentCore service named on the "For judges" page.
- Every API endpoint on the developer page.

---

## 5. Landing page pattern (both projects)

Order of sections, top to bottom. Every section has a one-line heading that states its conclusion.

1. Hero. One sentence: what it is. One sentence: who it is for. Two buttons: "Try the live demo" and "Watch the 4-minute video". A short looping screen recording (muted, with a play/pause control). Under the hero, a single line of three credibility markers with citations.
2. The problem. Three cards, each one statistic with its source linked and an "i" button. A two-sentence story of a real-shaped person.
3. How it works. A four-step storyboard, horizontal on desktop, vertical on mobile. Each step has an illustration, one line, and an "i" button.
4. See it happen. The live demo embedded. A "Judge mode" toggle that pre-loads the demo scenario and needs no login.
5. What makes it different. Three short blocks, then an honest comparison to existing tools.
6. Built on Strands and AgentCore. An architecture diagram with clickable nodes; each node opens an InfoTip.
7. For judges. A checklist that mirrors the five criteria, each linking to the evidence.
8. For developers. Quickstart, API overview with a sandbox key, OpenAPI link.
9. Safety and limits. What the agent will never do without a human.
10. References. Numbered, with links.
11. Footer. License, repo, contact, theme toggle, hackathon line.

Copy rules: no jargon without an InfoTip, no sentence over 25 words, no paragraph over four sentences, no emojis, no em dashes.

---

## 6. Accessibility checklist

- All functionality reachable by keyboard; visible focus ring (2 px accent outline, 2 px offset).
- Landmarks: header, nav, main, footer. One h1 per page. Heading order never skips.
- Color is never the only signal; every status has a word and a shape.
- Live regions announce agent status changes ("Gap closed by Riverton").
- Forms: labels tied to inputs, errors described in text next to the field, `aria-invalid` set.
- Media: video has captions and a transcript link. Looping hero video has a pause control and respects reduced motion.
- Language attribute set. Text resizable to 200 percent without loss.
- Tested with axe-core in CI (`tools/a11y_audit.py`, 30 page renders per project, zero violations)
  and a keyboard pass over every page. The same tool separately checks the two things axe cannot
  see: that no page scrolls sideways at any of the three widths, and that every control meets a
  target size, 24 by 24 as WCAG 2.2 AA requires and 48 by 48 for the buttons, tabs and fields a
  person presses to do something.

---

## 7. Performance budget

- Total JavaScript under 200 KB gzipped on the landing page.
- Fonts: two families, subset, `font-display: swap`, self-hosted.
- Images: AVIF or WebP with width descriptors; hero video under 3 MB, H.264 and WebM.
- Lighthouse, measured against the deployed sites rather than asserted:

| Page | Performance | Accessibility | Best practices | SEO |
|---|---|---|---|---|
| Turnout landing | 98 | 100 | 100 | 100 |
| Tally landing | 99 | 100 | 100 | 100 |
| Tally setup | 100 | 100 | 100 | 100 |
| Turnout crew | 83, then the layout shift was fixed | 100 | 100 | 100 |
| Tally sponsor | 82, then the layout shift was fixed | 100 | 100 | 100 |

  The two pages that scored in the eighties both did so for one reason: they fetched their content
  and then grew, giving a cumulative layout shift around 0.33. Both now write their summary blocks
  out at final height in the HTML and fill in only the words, which took the shift under 0.07. A
  page that reflows under a reader loses their place, and on these two pages the reader is a
  sponsor auditing a claim or a volunteer reading what was asked of them.

---

## 8. Voice and tone

- Confident and plain. We say what the system does and what it does not do.
- Domain-respectful. We use the words practitioners use and explain them, never dumb them down.
- No hype words: revolutionary, game-changing, seamless, cutting-edge.
- Numbers are always sourced. If we cannot source it, we do not say it.

---

## 9. Human-AI interaction guidelines, applied

Amershi et al., "Guidelines for Human-AI Interaction," CHI 2019, validated with 49 practitioners against 20 products. We treat the 18 guidelines as acceptance criteria. Each row names the concrete behavior in each product.

| Guideline | Turnout | Tally |
|---|---|---|
| G1 Make clear what the system can do | First-run screen and the landing hero list the five things it does and the three it never does. | Home screen subtitle: "Photograph the plate. Say who is here. I do the rest." Landing lists what it never does. |
| G2 Make clear how well it can do it | Risk badges show the numbers. Roll Call parsing accuracy from the eval set is shown on the About screen. | Each identified item shows a confidence pill. The eval accuracy for plates and voice is shown on the About screen. |
| G3 Time services based on context | Polls go out at 06:30 local. Asks respect quiet hours. Decision messages are never sent between 22:00 and 06:00 unless the gap starts within 12 hours. | Meal verdicts are spoken at the table. Reconciliation questions wait for the evening digest. Nothing is spoken during nap time (configurable). |
| G4 Show contextually relevant information | The gap card shows only the window, the numbers, and the recommended action. Full roster is one tap deeper. | The verdict card shows only components, the verdict, and the fix. Rule text is one tap deeper. |
| G5 Match relevant social norms | Messages use the department's name and fire-service words. Never chatty. | Spoken lines are short and warm, like a co-worker, never cute. |
| G6 Mitigate social biases | Response probability is learned per member from their own history, never from demographics. | Names are matched phonetically against the roster without assumptions about language or origin. Spanish is a first-class setting. |
| G7 Support efficient invocation | The chief can text "status" or "gaps" at any time and get the board summary. | One press to talk, one press to photograph. No menus before the action. |
| G8 Support efficient dismissal | Reply 3 to leave a gap open. Members reply N. STOP is honored instantly. | "Skip" on any question; "not now" by voice defers to the digest. |
| G9 Support efficient correction | The chief can reply "2" for options or text a correction in plain words ("use Cedar Hollow instead"). Members can reply "actually till 2". | "No, Leo's not here" corrects attendance. "Re-take" replaces a plate reading. Every log has an undo for 10 minutes. |
| G10 Scope services when in doubt | When the risk engine lacks 90 days of call history it says "estimate based on national pattern" on the badge. | When an item's confidence is below the threshold, the agent asks one question instead of logging. |
| G11 Make clear why the system did what it did | Every decision message includes the one-line explanation. The Trace Viewer shows the full chain. | Every verdict names the rule ("Snack needs two components"). The trace shows the vision reading and the rule version. |
| G12 Remember recent interactions | A member who said "till 2" is not re-asked for the morning. The chief's last decision style is remembered. | "The usual crackers" resolves to the provider's product. Yesterday's absence is not re-asked. |
| G13 Learn from user behavior | Response probabilities update from replies. Offer scoring learns the chief's preferred peers. | The provider's food vocabulary and typical menus are learned; fix suggestions come from foods she uses. |
| G14 Update and adapt cautiously | Learned preferences change scoring weights slowly (bounded step per week) and never override an explicit setting. | Vocabulary learning requires two consistent confirmations before it is used automatically. |
| G15 Encourage granular feedback | The chief can tap "good call" or "bad call" on any past decision; this feeds offer scoring. | Each verdict has "right" and "wrong" chips; wrong opens a one-tap correction. |
| G16 Convey the consequences of user actions | Approving an offer states the ledger effect: "Millbrook will owe Riverton 4 hours." | Sending a claim states the total and that the sponsor will receive the photos. |
| G17 Provide global controls | Settings: quiet hours default, weekly ask limit, auto-approval rules, peer list, pause the agent. | Settings: nap time, question budget, language, camera framing guide, pause the agent. |
| G18 Notify users about changes | A one-line note in the weekly summary when a rule, a peer, or a model version changes. | The evening digest notes when the rules data version changes, with the effective date. |

---

## 10. Calm technology, applied

Weiser and Brown (1995) defined calm technology as that which "informs but doesn't demand our focus or attention." This is the design philosophy of the hackathon brief itself: agents that run in the background and surface only for a real decision. We apply Amber Case's eight principles as follows.

| Principle | Design decision |
|---|---|
| Require the smallest possible amount of attention | The chief's whole interface on a normal day is nothing. The provider's is two spoken confirmations per meal. |
| Inform and create calm | The Station Board opens with the sentence "All windows covered through Sunday" when true, in large type, before any table. Tally's home screen shows a single line: "Today: 3 meals logged, all qualify." |
| Make use of the periphery | Coverage is a color strip on the lock-screen widget and in the SMS "status" reply. The provider's ratio indicator is a small dot that turns amber, not a modal. |
| Amplify the best of technology and humanity | The agent does arithmetic, memory, and chasing. The human does judgment. Every screen names which is which. |
| Communicate without speaking | Earcons: a soft two-note chime for "logged," a single low tone for "needs you." Text always accompanies audio. |
| Work even when it fails | If the model is unavailable, Roll Call still sends the fixed poll text and stores raw replies for later parsing. Tally queues photos offline and logs "pending review" rather than blocking the meal. |
| The right amount of technology is the minimum | No app for volunteers. No forms for the provider. No dashboard for anyone who does not need one. |
| Respect social norms | Volunteers are asked in the tone a chief would use. Parents receive notes in the provider's voice, not a template's. |

---

## 11. Conversational SMS design

Applies to Turnout's volunteer and chief messages and to any Tally parent messages.

Rules:

1. One message, one purpose, one question. Never two questions in one text.
2. Under 160 characters, so it never splits. Decision messages to the chief may use up to 300 characters because they carry numbers, and they are tested to render as one bubble on iOS and Android.
3. Always begin with the sender name: "Millbrook VFC:" so the recipient knows who is asking and can search for it.
4. Offer numbered or single-letter replies. Always accept free text too. Parsing is tolerant: "yes", "yep", "y", "sure", "can do", "ok" all mean yes; "till 2", "until noon", "morning only" produce a partial window.
5. Echo the understanding back in one line: "Got it: Thu until 2 pm." If the parse confidence is low, ask one clarifying question with two options.
6. STOP and HELP are honored in every state. STOP confirms in one line and never messages again except a single "you are opted out; reply START to rejoin" if the chief manually re-adds them.
7. Quiet hours are per person and enforced in code. Messages queued during quiet hours are sent at the end of quiet hours, and their text says "Sent after your quiet hours."
8. Never more than one poll per day and two targeted asks per week per member, enforced by a hook. Members can see their own limits by replying "limits".
9. Response promise: any inbound reply gets an acknowledgment within 60 seconds, even if the agent is still working ("Got it, working on Thursday now").
10. Every message that asks for a commitment states what happens next: "If you say Y, I will put you on the board and tell the chief."

Message templates are fixed strings with slots, stored in `messages.yaml`, reviewed as copy, and tested for length.

---

## 12. Voice interaction design

Applies to Tally's provider experience and Turnout's voice debrief.

Rules:

1. Push to talk, never always-listening. A large button, held or toggled. A visible waveform confirms capture.
2. Every spoken response is under 12 words and always shown as text at the same time.
3. Confirm by echoing the understood facts, not by asking "did you mean": "Maya here, Leo here, Ava absent sick."
4. Corrections start with "no" and are handled without restarting: "No, Leo's not here" updates one fact.
5. When uncertain, ask exactly one question with two options: "Milk or juice?"
6. Barge-in is supported: the provider can speak over the confirmation.
7. Earcons precede speech so the provider knows the system is about to talk: two-note chime for a result, a single low tone for a question, a distinct triple tone for a safety alert.
8. Noise fallback: if transcription confidence is low, the system says "I did not catch that" once and offers the large-button alternative for the same action.
9. Language is a per-provider setting. Names are added to the recognizer's custom vocabulary from the roster.
10. Nothing is ever logged from speech without a spoken or visible confirmation that names what was logged.

---

## 13. The interruption budget as a visible object

Gloria Mark's research at UC Irvine found that after an interruption, people take about 23 minutes to return to the original task at the same level of focus, and that interruption management is a design problem rather than a discipline problem. Both products therefore treat the user's attention as a budgeted resource, and show the budget.

- Each product has a quiet meter on its main screen: "Interrupted you 1 time today. Budget: 2." An InfoTip explains why the budget exists.
- Every interruption states why now, in the message itself: "Thursday starts in 26 hours, and this cannot wait for the weekly summary."
- Everything that can wait, waits: Turnout batches non-critical items into a weekly summary on Sunday evening; Tally batches into the evening digest.
- The budget is a setting (G17) and is enforced by code, not by the prompt. Tests prove it.
- The Trace Viewer shows "interrupt decision" as a step, so a judge can see the agent choosing not to interrupt.

---

## 14. Designing for older adults and cold hands

Volunteer chiefs and many members are over 50. Providers often work in low light with wet or busy hands. Product screens follow the Nielsen Norman Group senior usability guidance and touchscreen guideline reviews.

- Base font 18 px on product screens; 20 px for the primary status line; users can raise to 200 percent.
- Touch targets 48 by 48 CSS pixels minimum, with 8 px between adjacent targets.
- No sliders, no dropdowns, no long-press gestures, no swipe-only actions. Choices are visible buttons or radio cards.
- Primary navigation is a visible bottom bar. Never a hamburger for the main destinations.
- Critical states do not rely on blue, which reads as faded for many older eyes. Critical is red plus an octagon plus the word.
- Labels sit above fields. Buttons say what they do: "Approve Riverton's offer," not "OK."
- Confirmation of every consequential action in words, on screen, for at least 4 seconds, with undo.
- Glove and wet-hand tolerance: no hover-only affordances; all actions available by tap.

---

## 15. States, onboarding, and recovery

Every screen defines five states before it is built: empty, loading, error, offline, success.

Empty states teach. The empty Station Board says "No members yet. Paste your roster from a group text and I will sort it out," with a paste box. Tally's empty home says "Add your first child by saying their name and birthday."

Loading states are honest about time: "Asking Riverton's agent, usually under 10 seconds" with a progress line, never an infinite spinner.

Error states say what happened, what the system did about it, and one action: "Weather service did not answer. Risk shown without the storm factor. Retry."

Offline states keep working: Tally captures and queues; Turnout's board shows the last synced time and the SMS channel keeps functioning.

Success states name what changed and offer undo for 10 minutes.

Onboarding target: a working system in under three minutes.

- Turnout: paste a roster (names and phones, any format), pick minimum crew from three presets, add peer departments by name, done. A sample department can be loaded with one tap to explore first.
- Tally: say each child's name and birthday, mark subsidized children, choose the state, done. A sample home can be loaded with one tap.

Recovery: every list and log has an undo. Every setting has "reset to default." Every agent has "pause" (G17) with a visible paused banner.

---

## 16. The judge's journey as a designed flow

A judge is a user with a time budget of about five minutes per project and a checklist of five criteria. The `/judges` page is designed for that user.

- Opens with the one-line pitch and a five-row checklist in rubric order, each row linking to evidence.
- "Play the week" or "Play the day" is one tap away and runs without login.
- The Trace Viewer is one tap from any decision in the demo.
- The eval results table is on the page, not behind a repo link.
- The page states what is synthetic and what is live.
- The video is embedded with chapter markers matching the five criteria.

---

## 17. Ceiling checklist for the Design criterion

The rubric: "Does the project deliver a complete, coherent product experience and not just a technical proof of concept?" Ceiling means every item below is true and visible.

- [ ] Landing page follows section 5 in full, in light and dark, at 360 px and 1280 px.
- [ ] Product screens exist for every user role, with all five states designed and built.
- [ ] Onboarding works from empty in under three minutes, with a one-tap sample.
- [ ] All 18 Human-AI guidelines have a visible behavior (section 9).
- [ ] The interruption budget is visible and enforced (section 13).
- [ ] SMS or voice flows follow sections 11 and 12, with templates in a reviewed file.
- [ ] InfoTips on every domain term, metric, agent, service, and endpoint.
- [ ] Product screens meet section 14 sizing and navigation rules.
- [x] axe-core clean in both themes at three widths, in CI, on both projects.
- [x] Lighthouse 100 on accessibility, best practices and SEO on every page measured; performance
      98 and 99 on the two landing pages, and cumulative layout shift under 0.07 everywhere.
- [ ] The judge's journey (section 16) completes in under five minutes without help.
- [ ] Undo, pause, and reset exist and work.
- [ ] No emojis, no em dashes, no hype words anywhere.
