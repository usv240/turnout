# Demo script: what to point at, what to press, what to say

Both videos are here, so one file covers the whole recording session. This repository is
**Turnout**, so that script leads.

Record from the deployed URL in a clean browser profile at 1920 by 1080, light theme. **Press Reset
before each take.**

---

## Why the video is worth more than its share of the score

Rules.md lists **five equally weighted criteria**, so Presentation is a fifth of the score rather
than a third. The video is worth more than that fifth anyway, and the reason is one sentence at
line 549 of the rules:

> Judges are not required to test the Project and may choose to judge based solely on the text
> description, images, and video provided in the Submission.

So this is not a Presentation exhibit. It may be the only evidence a judge ever sees, for every one
of the five criteria. Both scripts are built on that, and each ends with a table naming which
criterion every beat is carrying. A beat that carries none is cut.

Rules.md also asks the pitch to cover three things by name: **the problem, who it is for, and why it
matters**. In both scripts those are the first forty seconds, said plainly, before any feature
appears.

## What changed from the first draft

The earlier scripts, kept in `DEMO_AND_VIDEO.md`, were accurate and too dense to land. Three
changes, all for the same reason, which is that a judge is watching a lot of these.

| Change | Why |
|---|---|
| The product is on screen inside the first minute, not after it | The old open spent thirty to forty seconds on statistics before anything ran |
| The beat each project wins on lands earlier, with silence around it | Burying the best moment past the halfway mark wastes it |
| Jargon is cut or explained in the same breath | Nobody should need to know what A2A stands for to follow what just happened |

Both come in around 3:40 against a five minute cap, at roughly 135 words a minute, which is a
comfortable read with room to breathe. **Reading faster to fit more in is the most common way a good
demo goes wrong.** If a take runs long, cut a sentence. Each script names which one to drop first.

---

# 1. Turnout

**Target 3:36. 487 spoken words.** Press **Reset** first.

| Time | Point at | Then | Say |
|---|---|---|---|
| 0:00 | Black, then the empty apparatus bay. No interface yet. | Hold on the bay. | **This is a fire station at two in the afternoon on a Tuesday. The tone just dropped. Nobody is coming, and the chief is finding that out right now.** |
| 0:14 | The landing page, the three stat cards. Let the sources under them be readable. | Scroll slowly across the three cards. | **Two out of every three American firefighters are volunteers. There are fewer of them than at any point in thirty five years, and calls have more than tripled. Chief Dana Ortiz runs one of these departments. Her entire system for this is a group text and a phone call to the next town, every week.** |
| 0:36 | The hero line, "Every other tool tells the chief who is coming." | Click through to the demo. | **Turnout is a background agent for each department. It does the chasing, and it only speaks up when there is a real decision.** |
| 0:50 | The **Phones** tab. The half past six roll call going out. | Let two or three replies land. Point at "till 10" and "morning only". | **At half past six it texts each of the fourteen volunteers one question about tomorrow. One character to answer. It reads "till ten" and "morning only" as easily as yes, and the moment anyone sends STOP it never texts them again.** |
| 1:12 | The **Station board**. Thursday ten to two, north, turning red. | Expand the numbers on that row. Hold. | **By half past seven, Thursday ten to two is critical. Not because a model had a feeling. Because the department's own twelve months of calls, who actually replied, and a National Weather Service ice storm warning together say there is a hundred percent chance nobody qualified turns out. Every number is on the screen, and that arithmetic is code, not the model.** |
| 1:45 | Back to **Phones**. The two targeted asks. Point at the one tagged as held. | Show the yes coming back. | **It asks the two people most likely to say yes for that exact window. One of them is asleep, so his message waits until his quiet hours end. That is enforced in code, not by asking a model politely. He says yes. They have a driver now, and they are still short a firefighter.** |
| 2:05 | The **Network** tab. The request leaving Millbrook. | **This is the shot. Slow down.** Let Riverton answer, then Cedar Hollow. | **Here is the part no scheduling app does. Millbrook's agent asks the neighbouring departments' agents directly. Not a shared database, and not one company's software. Two separate organisations, each running its own agent, talking over the open Agent-to-Agent protocol.** |
| 2:22 | Riverton green, nine minutes. Then Cedar Hollow's decline and its stated reason. | Point at the line saying they verified who was asking. | **Riverton's agent checks its own coverage and offers a truck, nine minutes out. Cedar Hollow's agent says no, because it is protecting its own critical window, and it says so rather than going quiet. Every request is signed, so nobody commits a fire truck on a message they cannot verify.** |
| 2:45 | The chief's phone. One message covering both windows. | Tap 1. Let the board turn green. | **The chief gets one text for both of Thursday's open windows, because the answer is the same for both. She taps once. Riverton's chief had already pre-approved short delays, so their agent confirms it without waking anybody. Eight seconds of her day.** |
| 3:02 | The **Incident report** tab. The voice note, then the draft with two flagged fields. | Point at the flags, not the prose. | **Thursday there is a collision, and Riverton responds. Afterwards the officer leaves a voice note, and the agent drafts the federal incident report. The two fields it was not sure about are flagged, not invented.** |
| 3:18 | Navigate to **/crew.html**. One volunteer's card. | Point at the asks-this-week count, then the held message. | **One last screen, which most scheduling tools do not have at all. Every volunteer can see what the agent knows about them, how often it has asked, and the messages it chose to hold back. An agent that asks something of a person should be answerable to that person.** |
| 3:34 | Hold on the board, all green. | End. | **Turnout. So that there is always someone coming.** |

### What each beat is scoring

| Beat | Criterion |
|---|---|
| 0:00 to 0:36 | Potential Impact. The problem, who it is for, why it matters, in that order |
| 1:12, the numbers on screen | Technical Implementation, and the honesty the whole project rests on |
| 1:45, the held message | Technical Implementation. A promise kept in code, not in a prompt |
| 2:05 to 2:45 | Creativity and Originality. This is the beat that is hard to copy |
| 3:02, the flagged fields | Creativity. An agent that declines to guess |
| 3:18, the crew page | Design. A complete product, including the person it asks things of |

### Recording notes

- Reset, then play the five steps in one take and cut later.
- **The Network beat at 2:05 is the shot.** Do not talk over the two answers arriving.
- If it runs long, cut the signature clause at 2:22 first, then the held message at 1:45.
- Every element named above was checked against the running deployment. The line saying a peer
  verified the request only renders when one really did, so that was confirmed live: Riverton
  offering nine minutes, Cedar Hollow declining with its reason, both verified.

---

# 2. Tally

**Target 3:42. 501 spoken words.** Press **Reset** first.

| Time | Point at | Then | Say |
|---|---|---|---|
| 0:00 | A kitchen at 7:38 am. A child's plate. A small hand reaching in. No interface yet. | Hold on the plate. | **Nine children before eight in the morning. Twelve by three in the afternoon. One adult, and she has no free hands.** |
| 0:12 | The landing page, the three stat cards. Let the sources be readable. | Scroll slowly across them. | **Rosa runs a child care home. Most infants, most rural families, and most parents working night shifts are looked after in homes like hers. Half of those homes closed in twelve years, and the reason providers give most often is the paperwork.** |
| 0:30 | Hold on the third card. | Then the hero line. | **Every meal, every child, every component, written down in order to be paid for. Usually at nine at night, from memory. Last month a snack was rejected because the log said one component. There were two. She forgot to write the second one down.** |
| 0:48 | The hero, "She feeds twelve kids and files paperwork for every bite." | Click through to the demo. | **Tally is a hands-free agent for the one professional who cannot touch a screen.** |
| 0:56 | The **Today** tab. Press **Say who is here**. | Let the sentence and the reply land, then press **Mateo arrives**. The line here already covers him, so do not stop for a separate one. | **She says who is here, in one sentence, out loud. That is attendance, the subsidy check, and the staffing ratio for the rest of the day. It hears the child who is off sick and the one arriving at noon.** |
| 1:14 | Press **Breakfast**. The components appearing as chips. | Let the chips finish. **Do not talk over what comes next.** | **She photographs the plate. Amazon Bedrock vision names the foods and maps each one to a food program component.** |
| 1:26 | The red allergy line. | **This is the shot. Hold two full seconds of silence before you speak.** Stay on it. | **Then this happens, and it is worth saying that nobody arranged it. The photograph really does contain peanut butter, and Leo really is allergic to peanuts. Every food is checked against every present child's allergies before a single thing is written down.** |
| 1:48 | The breakfast verdict, missing milk. | Press **Add the milk**. Let it turn green. | **It also notices the breakfast is short of milk, and says so while the bowl is still on the table. She adds milk, takes one more photograph, and it qualifies. The first record is replaced, not doubled.** |
| 2:06 | Press **Lunch**, then **Add milk and fruit**. | Point at the smallest fix, not the prose. | **That is the whole product. The difference between fixing a meal at the table, and losing it at claim time when nothing can be done about it. And the fix is computed, not written by a model, so it only ever names food she actually has.** |
| 2:26 | Press **Afternoon snack**. The yoghurt, not reimbursable. Point at the label check. | Point at the confidence chip. | **The afternoon snack is yoghurt on its own, so it will not be paid. Tally also flags that yoghurt has a sugar limit a photograph cannot establish, and refuses to guess it. It never estimates a portion either, because the program pays on components, and that is the half of food vision that actually works.** |
| 2:48 | Press **Evening digest**. Then the **Evening** tab. | Point at the two questions. | **At half past six a Strands Graph closes the day. It drafts a note home for each child in that family's language, checks the compliance clock, and puts exactly two questions to her, because that budget is enforced in code. It will not spend one on something she already settled, because those answers are held in AgentCore Memory.** |
| 3:10 | Navigate to **/sponsor.html**. | Point at one meal, its photograph, and the rule version. | **This is what her sponsor sees. Every meal, the photograph it was judged from, and the version of the rulebook that decided it, so a claim can still be defended years later. That same rulebook is published over MCP, so the sponsor's own agent can check a claim without having to trust ours.** |
| 3:30 | The **Month** tab. Hold on the money. | End. | **One month. A hundred and one dollars of meals caught at the table instead of lost at the claim. Tally. So the paperwork is done before the food is cold.** |

### What each beat is scoring

| Beat | Criterion |
|---|---|
| 0:00 to 0:48 | Potential Impact. The problem, who it is for, why it matters, in that order |
| 1:26, the allergy | Creativity and Originality, and Impact. This is the beat nobody forgets |
| 2:06, the smallest fix | Technical Implementation. Computed rather than generated, and it says why |
| 2:26, the refusal | Creativity. An agent defined by what it declines to do |
| 2:48, two questions | Technical Implementation. A budget kept in code, and Memory doing real work |
| 3:10, the sponsor page | Design. A complete product, including the organisation that pays the claim |

### Recording notes

- Reset, then play the eight steps in one take and cut later.
- **The allergy line at 1:26 is the shot.** Two full seconds of silence on it before you speak. It
  is the only moment in either video a judge will still remember an hour later.
- If it runs long, cut the label check at 2:26 first, then the note home at 2:48.
- Every button, tab and screen this names was checked against the running deployment, including the
  step the narration deliberately does not stop for.

---

## Before you upload

- Export between 3:30 and 4:00. The rules cap it at five minutes.
- Upload to YouTube as **public**, then open it in a logged-out window and confirm it plays.
- Captions in `video/` are timed to the earlier, longer script. Regenerate them from the final cut
  rather than trusting the old timings.
- The recorded visual tracks are from 5 September, before the interface fixes. Record fresh rather
  than narrating over them, or the video will not match the site a judge opens.
