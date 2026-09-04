# Turnout: UX Specification

Screen-by-screen and message-by-message. Follows `DESIGN_SYSTEM.md` sections 9 to 16. Copy here is final unless a test proves it confusing.

---

## 1. Users and contexts

| User | Context | Device | Time available | Design consequence |
|---|---|---|---|---|
| Chief | Day job; checks phone between customers | Phone, sometimes a laptop at the station | 10 seconds at a glance, 2 minutes at most | One-line status first. One decision per message. Undo. |
| Deputy or officer | Same as chief; receives escalations | Phone | Seconds | Same messages as chief, labeled "escalated." |
| Volunteer member | At work, driving, at home; often over 50 | Any phone, including flip phones | 5 seconds | SMS only. One character to reply. Never more than one poll a day. |
| Neighboring chief | Receives offers to approve, unless auto-approval is set | Phone | Seconds | Same decision message shape. Ledger effect stated. |
| Judge | Five minutes, a checklist | Laptop, sometimes a phone | Five minutes | `/judges` page and Judge mode per design system section 16. |

---

## 2. The chief's messages (SMS)

All templates in `messages.yaml`. Slots in braces. Every message begins with the department short name.

### 2.1 Decision message (the only interrupt)

```
{dept}: {day} {start}-{end} {district}: {LEVEL}.
{explanation}.
{recommendation}.
Reply 1 approve, 2 options, 3 leave open.
```

Example (287 characters):

```
Millbrook VFC: Thu 10a-2p north: CRITICAL.
1-2 calls expected, no driver, ice storm warning.
Riverton can cover, 9 min delay. Millbrook would owe 4 hrs.
Reply 1 approve, 2 options, 3 leave open.
```

Rules: level in capitals; explanation is the risk engine's one-liner; recommendation states the ledger effect (G16); exactly three numbered replies.

### 2.2 After approval

```
Millbrook VFC: Done. Riverton covers Thu 10a-2p north. Members told. Reply UNDO within 10 min to cancel.
```

### 2.3 Options

```
Millbrook VFC: Other options for Thu 10a-2p:
2a Cedar Hollow, 14 min delay, declined (own district at risk).
2b Ask Dave again at 8am (usually yes on Thu).
Reply 2b to try, or 1 for Riverton.
```

### 2.4 Escalation

```
Millbrook VFC (escalated to Deputy): Chief has not replied in 2 hrs. Thu 10a-2p north CRITICAL. Riverton offer expires 6pm. Reply 1 approve, 3 leave open.
```

### 2.5 On-demand status (chief texts "status" or "gaps")

```
Millbrook VFC: Next 7 days: 2 gaps. Thu 10a-2p north CRITICAL (working on it). Fri 9a-12p north ELEVATED (swap proposed). Everything else covered.
```

### 2.6 Weekly summary (Sunday 18:00)

```
Millbrook VFC week: 168 hrs, 163 covered. 2 gaps closed by members, 1 by Riverton. You decided once. Ledger: owe Riverton 4 hrs. 1 cert expiring Oct 30 (Sam), refresher booked Oct 4.
```

---

## 3. The volunteer's messages (SMS)

### 3.1 Daily poll (06:30 local, only for the next high-risk day)

```
Millbrook VFC: Around Thu 8a-5p? Reply Y or N, or a time like "till 2".
```

### 3.2 Poll echo

```
Millbrook VFC: Got it: Thu until 2pm. Thanks.
```

### 3.3 Targeted ask (at most two per week, never in quiet hours)

```
Millbrook VFC: Thu 10a-2p needs a driver. You usually can. Reply Y or N. If Y, you are on the board and the chief is told.
```

### 3.4 Swap proposal (to both members)

```
Millbrook VFC: Swap idea: you take Fri 9a-12p, Maria takes your Sat 2-5p. Both of you must say Y. Reply Y or N.
```

### 3.5 Coverage arranged

```
Millbrook VFC: Thu 10a-2p north is covered by Riverton. Nothing needed from you. Thanks for replying.
```

### 3.6 Clarification (low parse confidence)

```
Millbrook VFC: Did you mean Thu morning only (reply 1) or Thu afternoon only (reply 2)?
```

### 3.7 STOP, HELP, LIMITS

```
STOP  -> Millbrook VFC: You are opted out. You will get no more texts. Reply START to rejoin.
HELP  -> Millbrook VFC: I ask about coverage once a day and at most twice a week for specific hours. Reply Y, N, or a time. Reply STOP to opt out, LIMITS to see your settings.
LIMITS-> Millbrook VFC: Your quiet hours 10pm-6am. Asks this week: 1 of 2. Change by telling the chief.
```

### 3.8 Cert reminder

```
Millbrook VFC: Your EMT card expires Oct 30. Refresher Sat Oct 4, 9am at Station 1 works with your availability. Reply Y to book, N for other dates.
```

---

## 4. Station Board (`/board`)

Purpose: the chief's glance. Desktop and phone.

### 4.1 Layout, phone (360 to 767)

1. Status line, 20 px, one sentence, top of screen. Green: "All windows covered through Sunday." Red: "1 critical gap. Thursday 10 to 2. Working on it." This is the calm-technology periphery: most days the chief reads one green line and closes the app.
2. Quiet meter: "Interrupted you 0 times this week. Budget 3." with InfoTip.
3. Gaps list: cards sorted by risk then time. Each card: window, district, level (word, shape, color), one-line explanation, status ("asking members", "asking neighbors", "needs you", "covered by Riverton"). Tap opens the decision sheet.
4. Coverage strip: seven days as horizontal bars, hour-resolution, colored by level. Tap a day to see hours.
5. Bottom bar: Board, Network, Phone, More.

### 4.2 Layout, desktop (1024 and up)

Two columns. Left: status line, quiet meter, gaps list. Right: 7-day by 24-hour heatmap per district with the risk formula on hover, then recent decisions, then cert warnings, then recent incidents.

### 4.3 Gap card anatomy

```
[octagon] CRITICAL   Thu 10:00 to 14:00   North
1 to 2 calls expected, no driver, ice storm warning   [i]
Riverton can cover, 9 min delay. Millbrook would owe 4 hours.
[ Approve Riverton ]  [ See options ]  [ Leave open ]
Status: waiting for you since 08:42
```

InfoTip on the explanation shows the formula and the four inputs with values, and the phrase "computed as code, see trace."

### 4.4 Decision sheet

Bottom sheet on phone, side panel on desktop. Repeats the card, adds the two alternatives, the ledger effect in words, and a link "Why this offer" that opens the trace step. Buttons are 48 px. Approve shows a 4-second confirmation with Undo.

### 4.5 States

- Empty: "No members yet. Paste your roster from a group text." Paste box; any format; preview of parsed members before saving.
- Loading: "Checking the next 7 days, usually under 5 seconds."
- Error: "Weather service did not answer. Risk shown without the storm factor. Retry."
- Offline: banner "Last synced 09:12. Texts still work."
- Success: green status line.

---

## 5. Network View (`/network`)

Purpose: show mutual aid as a living thing and show the A2A negotiation.

- Map with the three departments as labeled nodes (fictional coordinates on a plain map tile, no external map service required; an SVG schematic map is acceptable).
- Edges show ledger balance as a small label: "Millbrook owes Riverton 4 h."
- When a request goes out, an animated dot travels along the edge, and a message bubble appears at the peer: "Riverton: can cover, 9 min" or "Cedar Hollow: declined, own district at risk." Reduced motion replaces animation with a timeline list.
- Clicking an edge opens the exchange log with the raw A2A payloads, formatted.
- InfoTips on "mutual aid," "ledger," "A2A," "AgentCard."

---

## 6. Phones (`/phones`)

Purpose: let a judge play both sides.

Two phone frames side by side on desktop, tabbed on mobile: Chief and a selectable Member. Each shows the real SMS thread. Reply buttons under each phone send the exact reply text through the same inbound path as real SMS. A "Simulate real time" toggle speeds the clock. Every message shows a timestamp and, for delayed messages, a small "held for quiet hours" tag.

---

## 7. Trace Viewer (`/traces`)

Purpose: proof.

- Timeline of the current Graph run: nodes in order, each with duration.
- Expand any node to see tool calls with inputs and outputs, formatted; the risk engine call shows the four inputs and the score.
- A2A exchanges appear as their own rows with request and response payloads.
- Memory reads appear as rows: "Read: Dave says yes to Thursdays 71 percent."
- The interrupt decision appears as a row: "Decision: interrupt chief now. Reason: critical and starts within 26 hours."
- "Open in CloudWatch" link for the raw trace.

---

## 8. Incident review (`/incidents/{id}`)

- Left: audio player and transcript with timestamps.
- Right: the NERIS draft as a form, required fields marked, uncertain fields highlighted with the phrase the agent was unsure about. Each field has an InfoTip explaining the NERIS meaning.
- Buttons: "Save draft," "Submit to NERIS" (confirmation dialog states what is sent), "Ask for re-transcription."

---

## 9. Settings (`/settings`)

Global controls (G17), each with an InfoTip and a plain explanation of consequences:

- Minimum crew per apparatus type (three presets plus custom).
- Quiet hours default and per member.
- Weekly ask limit.
- Auto-approval rules for mutual aid: "Approve offers automatically when delay is under {n} minutes and the ledger stays within {h} hours." Off by default.
- Peers: add by name; exchange credentials; see their AgentCard.
- Pause the agent (shows a banner everywhere until resumed).
- Data: export everything, delete everything.

---

## 10. Onboarding (`/start`)

Three steps, under three minutes, with "Load the sample department" available on step one.

1. Roster. Paste any text. The agent extracts names and phones and shows a table to confirm. Roles are chosen by tapping chips per person.
2. Crew. Pick a preset: "Engine: 1 driver plus 2 firefighters," "Ambulance: 1 EMT plus 1 driver," or custom.
3. Neighbors. Type department names. If they are on Turnout, a credential exchange link is generated. If not, they are listed as "phone only" and the agent will draft a text for the chief to send.

Finish screen: "First poll goes out tomorrow at 6:30. You will hear from me only if something needs you."

---

## 11. Microcopy table

| Situation | Copy |
|---|---|
| All good | All windows covered through Sunday. |
| One gap, agent working | 1 critical gap. Thursday 10 to 2. Working on it. |
| Needs chief | 1 gap needs you. Thursday 10 to 2. |
| Approve button | Approve Riverton's offer |
| After approve | Done. Riverton covers Thursday 10 to 2. Undo |
| Leave open | Left open. I will check again at 11:42. |
| Peer declined | Cedar Hollow declined: their own district is at risk then. |
| No peers available | No neighbor can cover. This is the decision only you can make. |
| Paused | Turnout is paused. No texts will be sent. Resume |

---

## 12. Accessibility specifics

- Status line is an `aria-live="polite"` region.
- Gap level is announced as "Critical, octagon" for screen readers.
- Heatmap has a table alternative behind "View as table."
- Phones page threads are proper lists with sender names in text.
- All buttons 48 px, labels above fields, no dropdowns; peers and roles use radio cards and chips.
