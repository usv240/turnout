# Turnout: the shooting script

This is the one to record from. `DEMO_AND_VIDEO.md` section 4 is the longer reference version,
written while the system was being built; it carries more detail than a judge can absorb at speed.

**Target 3:40. Hard cap 5:00 by the rules.** About 500 words at a comfortable 140 a minute, which
leaves room to breathe. Reading faster to fit more in is the most common way a good demo goes wrong.

## Why it is shaped this way

Rules.md, line 549: **judges are not required to test the project and may judge on the video alone.**
So this is not a Presentation exhibit. It is the only evidence for all five criteria, and every beat
below is doing one of those jobs.

Rules.md also asks the pitch to cover three things by name: **the problem, who it is for, and why it
matters.** Those are the first 36 seconds, said plainly, before any feature appears.

Three changes from the earlier draft, all for the same reason, which is that a judge is watching a
lot of these:

- **The product is on screen at 50 seconds, not 1:10.** The old open spent 40 seconds on statistics
  before anything ran.
- **The neighbouring departments negotiating is the moment this project wins on, and it now lands at
  2:05 instead of 2:30**, with the setup trimmed so it arrives with more time around it.
- **Jargon is either cut or explained in the same breath.** A judge should not have to know what A2A
  or NERIS stands for to understand what just happened.

---

## The script

Press **Reset** before recording. Light theme. 1920 by 1080, clean browser profile.

| Time | Point at | Click next | Say |
|---|---|---|---|
| 0:00 | Black, then the empty apparatus bay. No UI yet. | Hold on the bay. | **This is a fire station at two in the afternoon on a Tuesday. The tone just dropped. Nobody is coming, and the chief is finding that out right now.** |
| 0:14 | The landing page, the three stat cards. Let the sources under them be readable. | Scroll slowly across the three cards. | **Two out of every three American firefighters are volunteers. There are fewer of them than at any point in thirty five years, and calls have more than tripled. Chief Dana Ortiz runs one of these departments. Her entire system for this is a group text and a phone call to the next town, every week.** |
| 0:36 | The hero line: "Every other tool tells the chief who is coming." | Click through to the demo. | **Turnout is a background agent for each department. It does the chasing, and it only speaks up when there is a real decision.** |
| 0:50 | The **Phones** tab. The 06:30 roll call going out. | Let two or three replies land. Point at "till 10" and "morning only". | **At half past six it texts each of the fourteen volunteers one question about tomorrow. One character to answer. It reads "till ten" and "morning only" as easily as yes, and the moment anyone sends STOP it never texts them again.** |
| 1:12 | The **Station board**. Thursday ten to two, north, turning red. | Expand the numbers on that row. Hold. | **By half past seven, Thursday ten to two is critical. Not because a model had a feeling. Because the department's own twelve months of calls, who actually replied, and a National Weather Service ice storm warning together say there is a hundred percent chance nobody qualified turns out. Every number is on the screen, and that arithmetic is code, not the model.** |
| 1:45 | Back to **Phones**. The two targeted asks. Point at the one tagged as held. | Show the yes coming back. | **It asks the two people most likely to say yes for that exact window. One of them is asleep, so his message waits until his quiet hours end. That is enforced in code, not by asking a model politely. He says yes. They have a driver now, and they are still short a firefighter.** |
| 2:05 | The **Network** tab. The request leaving Millbrook. **This is the shot. Slow down.** | Let Riverton answer, then Cedar Hollow. | **Here is the part no scheduling app does. Millbrook's agent asks the neighbouring departments' agents directly. Not a shared database, and not one company's software. Two separate organisations, each running its own agent, talking over the open Agent-to-Agent protocol.** |
| 2:22 | Riverton green, "9 min". Then Cedar Hollow's decline and its stated reason. | Point at the signature indicator. | **Riverton's agent checks its own coverage and offers a truck, nine minutes out. Cedar Hollow's agent says no, because it is protecting its own critical window, and it says so rather than going quiet. Every request is signed, so nobody commits a fire truck on a message they cannot verify.** |
| 2:45 | The chief's phone. One message covering both windows. | Tap 1. Let the board turn green. | **The chief gets one text for both of Thursday's open windows, because the answer is the same for both. She taps once. Riverton's chief had already pre-approved short delays, so their agent confirms it without waking anybody. Eight seconds of her day.** |
| 3:02 | The **Incident report** tab. The voice note, then the draft with two flagged fields. | Point at the flags, not the prose. | **Thursday there is a collision, and Riverton responds. Afterwards the officer leaves a voice note, and the agent drafts the federal incident report. The two fields it was not sure about are flagged, not invented.** |
| 3:18 | Navigate to **/crew.html**. One volunteer's card. | Point at the asks-this-week count, then the held message. | **One last screen, which most scheduling tools do not have at all. Every volunteer can see what the agent knows about them, how often it has asked, and the messages it chose to hold back. An agent that asks something of a person should be answerable to that person.** |
| 3:34 | Hold on the board, all green. | End. | **Turnout. So that there is always someone coming.** |

---

## What each beat is scoring

Say this to yourself while editing. If a beat is not doing one of these, cut it.

| Beat | Criterion it is for |
|---|---|
| 0:00 to 0:36 | Potential Impact. The problem, who it is for, why it matters, in that order |
| 1:12 numbers on screen | Technical Implementation, and the honesty the whole project rests on |
| 1:45 the held message | Technical Implementation. A promise kept in code, not in a prompt |
| 2:05 to 2:45 | Creativity and Originality. This is the beat that is hard to copy |
| 3:02 flagged fields | Creativity. An agent that declines to guess |
| 3:18 crew page | Design. A complete product, including the person it asks things of |

## Recording checklist

- Reset first, then play the five steps in one take and cut later.
- The Network beat at 2:05 is the shot. Give it room. Do not talk over the arrival of the two answers.
- Do not read faster to fit more in. Cut a sentence instead. The two candidates are the signature
  clause at 2:22 and the held message at 1:45.
- Export between 3:30 and 4:00. Upload to YouTube as **public**, then verify playback logged out.
- Captions: `video/turnout.srt` is timed to the earlier script. Re-run `make_captions.py` after the
  final cut rather than trusting the old timings.
