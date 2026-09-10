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
matters**. In both scripts those are the first thirty five seconds, said plainly, before any feature
appears.

## The rule these scripts are written to

A judge is watching a lot of these, reading the interface and listening to the narration at the same
time. So the story has to be followable without any of the technology being understood:

> **Nobody may respond. Turnout knows before the emergency does. It tries the right volunteers. It
> still cannot fill the gap. Neighbouring agents negotiate. The chief makes one decision. Coverage
> is restored.**

Everything underneath stays sophisticated: Strands graphs, hooks, AgentCore, signed agent-to-agent
requests, deterministic scoring, refusal evaluations. **A judge should never have to understand any
of it to understand why this matters.** The interface can carry the technical proof while the
narration stays plain. Where a technical term earns its place, it arrives after the plain
explanation has already landed, never before.

Both come in around 3:20 against a five minute cap, at roughly 135 words a minute, which is a
comfortable read with room to breathe. **Reading faster to fit more in is the most common way a good
demo goes wrong.** If a take runs long, cut a sentence. Each script names which one to drop first.

---

# 1. Turnout

**Target 3:20. About 450 spoken words.** Press **Reset** first.

| Time | Point at | Then | Say |
|---|---|---|---|
| 0:00 | Black, then the empty apparatus bay. No interface yet. | Hold on the bay. | **This is a fire station at two in the afternoon on a Tuesday. The tone just dropped. Nobody is coming, and the chief is finding that out right now.** |
| 0:12 | The landing page. Let one stat card be readable, not all three. | Scroll slowly. Do not stop on each card. | **Most American firefighters are volunteers. Chief Dana Ortiz runs one of those departments. Her roster looks covered, right up until Tuesday afternoon, when everyone is at work. Today she finds out only when the call comes in. And in an emergency, that is not a scheduling inconvenience. Minutes matter.** |
| 0:34 | The hero line. | Click through to the demo. | **Turnout finds that gap before the emergency does.** |
| 0:40 | The **Phones** tab. The half past six roll call going out. | Let two or three replies land. Point at "till 10" and "morning only". | **Every morning it texts each of the fourteen volunteers one question about tomorrow. One character to answer. It reads "till ten" and "morning only" as easily as yes, and the moment anyone sends STOP it never texts them again.** |
| 0:58 | The **Station board**. Thursday ten to two, north, turning red. | Expand the numbers on that row. Hold. | **Before Thursday arrives, Turnout finds the dangerous gap. Ten to two, north district. Based on this department's own call history, who is actually available, and today's weather, there is no qualified crew. And every number behind that decision is right here on the screen.** |
| 1:17 | Back to **Phones**. The two targeted asks. Point at the one tagged as held. | Show the yes coming back. | **It asks the two people most likely to say yes for that exact window. One of them is asleep, so his message waits until his quiet hours end. That is enforced in code, not by asking a model politely. He says yes. They have a driver now, and they are still short a firefighter.** |
| 1:40 | The **Network** tab. The request leaving Millbrook. | **The winning sequence starts here. Slow down and protect it.** | **Turnout still cannot make a crew. So instead of waking the chief, its agent asks the neighbouring departments' agents directly.** |
| 1:49 | Riverton answering, then Cedar Hollow. | **Say nothing while the two answers arrive.** Then speak. | **Riverton can help. Cedar Hollow cannot, because helping would open a dangerous gap of its own, and it says so rather than going quiet.** |
| 2:00 | The signed request, and the line saying they verified who was asking. | Let it sit. | **These are two separate organisations. No shared database, no common employer. Each runs its own agent, and they negotiate over the open Agent-to-Agent protocol, every request signed, so nobody commits a fire truck on a message they cannot verify.** |
| 2:18 | Back to the board, still short. | Move to the chief's phone. | **Only now does Turnout need the chief.** |
| 2:22 | The chief's phone. One message covering both windows. | Tap 1. Let the board turn green. | **Turnout handled the roll call, found the gap, asked the right volunteers and negotiated mutual aid. It brings Dana exactly one decision, one text covering both open windows. She taps once, and Riverton's agent confirms without waking anybody. Eight seconds of her day.** |
| 2:42 | The **Incident report** tab. The two flagged fields. | Point at the flags, not the prose. Keep this short. | **Thursday there is a collision, Riverton responds, and afterwards Turnout drafts the federal report from the officer's voice note. It flags what it was unsure of rather than inventing it.** |
| 2:55 | Navigate to **/crew.html**. One volunteer's card. | Point at the asks-this-week count, then the held message. Keep this short. | **And volunteers are not invisible inputs. They can see what Turnout knows, how often it asks them, and when it deliberately left them alone.** |
| 3:06 | Back to the board, all green. | Hold. | **The chief did not spend her morning chasing fourteen people. Turnout found the risk, closed what it could, negotiated what it could not, and asked her once.** |
| 3:18 | Hold on the green board. | End. | **Turnout. So that there is always someone coming.** |

### What each beat is scoring

| Beat | Criterion |
|---|---|
| 0:00 to 0:34 | Potential Impact. The problem, who it is for, and why minutes matter |
| 0:58, the numbers on screen | Technical Implementation, and the honesty the whole project rests on |
| 1:17, the held message | Technical Implementation. A promise kept in code, not in a prompt |
| 1:40 to 2:18 | Creativity and Originality. The sequence nobody else will have |
| 2:22, one decision | The hackathon's own theme. Autonomous work, one human decision |
| 2:42, the flagged fields | Creativity. An agent that declines to guess |
| 2:55, the crew page | Design. A complete product, including the person it asks things of |
| 3:06, the summary | Presentation. The transformation stated once, plainly, before the tagline |

### Recording notes

- Reset, then play the five steps in one take and cut later.
- **1:40 to 2:18 is the whole video.** Four beats instead of two, with a silence at 1:49 while the
  two answers arrive. The protocol is named at 2:00, after the plain explanation has landed, never
  before it.
- The incident report is deliberately thirteen seconds. The story climaxes when the chief approves,
  and a long section afterwards starts a second product. It stays because flagging rather than
  inventing is a real differentiator, but it is a footnote now, not a chapter.
- If it runs long, cut the signature clause at 2:00 first, then the held message at 1:17.
- Every element named above was checked against the running deployment. The line saying a peer
  verified the request only renders when one really did, so that was confirmed live: Riverton
  offering nine minutes, Cedar Hollow declining with its reason, both verified.

---

# 2. Tally

**Target 3:28. About 470 spoken words.** Press **Reset** first.

| Time | Point at | Then | Say |
|---|---|---|---|
| 0:00 | A kitchen at 7:38 am. A child's plate. A small hand reaching in. No interface yet. | Hold on the plate. | **Nine children before eight in the morning. Twelve by three in the afternoon. One adult, and she has no free hands.** |
| 0:12 | The landing page. Let one stat card be readable, not all three. | Scroll slowly. Do not stop on each card. | **Rosa runs a child care home. Most infants, and most parents working night shifts, are cared for in homes like hers, and half of those homes closed in twelve years. The reason providers give most often is the paperwork. Every meal, every child, every component, written down in order to be paid for, at nine at night, from memory.** |
| 0:36 | The hero line. | Click through to the demo. | **Tally does the counting, hands free, for the one professional who cannot touch a screen.** |
| 0:44 | The **Today** tab. Press **Say who is here**. | Let the sentence and the reply land, then press **Mateo arrives**. The line here already covers him, so do not stop for a separate one. | **She says who is here, in one sentence, out loud. That is attendance, the subsidy check, and the staffing ratio for the rest of the day. It hears the child who is off sick, and the one arriving at noon.** |
| 1:02 | Press **Breakfast**. The components appearing as chips. | Let the chips finish. **Do not talk over what comes next.** | **She photographs the plate. Amazon Bedrock vision names the foods and maps each one to a food program component.** |
| 1:14 | The red allergy line. | **This is the shot. Hold two full seconds of silence before you speak.** Stay on it. | **Then this happens, and it is worth saying that nobody arranged it. The photograph really does contain peanut butter, and Leo really is allergic to peanuts. Every food is checked against every present child's allergies before a single thing is written down.** |
| 1:36 | The breakfast verdict, missing milk. | Press **Add the milk**. Let it turn green. | **It also notices the breakfast is short of milk, and says so while the bowl is still on the table. She adds milk, takes one more photograph, and it qualifies.** |
| 1:50 | Press **Lunch**, then **Add milk and fruit**. | Point at the smallest fix, not the prose. | **Last month a snack of Rosa's was rejected because the log said one component. There were two. She forgot to write the second one down, and by the time anyone noticed, the money was gone. That is the whole product. Fixing a meal at the table, instead of losing it at claim time when nothing can be done.** |
| 2:14 | Press **Afternoon snack**. The yoghurt, not reimbursable. Point at the label check. | Point at the confidence chip. | **The afternoon snack is yoghurt on its own, so it will not be paid. Tally also flags that yoghurt has a sugar limit a photograph cannot establish, and refuses to guess it. It never estimates a portion either, because the program pays on components, and that is the half of food vision that actually works.** |
| 2:36 | Press **Evening digest**. Then the **Evening** tab. | Point at the two questions. | **At half past six the day closes itself. A note home for each child in that family's language, the compliance clock checked, and exactly two questions put to her, because that budget is enforced in code. It will not spend one on something she already settled.** |
| 2:56 | Navigate to **/sponsor.html**. | Point at one meal, its photograph, and the rule version. | **This is what her sponsor sees. Every meal, the photograph it was judged from, and the version of the rulebook that decided it, so a claim can still be defended years later.** |
| 3:10 | The **Month** tab. Hold on the money. | Hold. | **Rosa did not spend her evening reconstructing the day. Tally logged every meal as it happened, caught the ones that would not have been paid, and asked her twice. One month, a hundred and one dollars she would have lost.** |
| 3:26 | Hold on the month. | End. | **Tally. So the paperwork is done before the food is cold.** |

### What each beat is scoring

| Beat | Criterion |
|---|---|
| 0:00 to 0:36 | Potential Impact. The problem, who it is for, and what it costs her |
| 1:14, the allergy | Creativity and Originality, and Impact. The beat nobody forgets |
| 1:50, the rejected snack | Potential Impact. The real anecdote, placed where it explains the feature |
| 2:14, the refusal | Creativity. An agent defined by what it declines to do |
| 2:36, two questions | The hackathon's own theme. Autonomous work, the smallest possible interruption |
| 2:56, the sponsor page | Design. A complete product, including the organisation that pays the claim |
| 3:10, the summary | Presentation. The transformation stated once, plainly, before the tagline |

### Recording notes

- Reset, then play the eight steps in one take and cut later.
- **The allergy line at 1:14 is the shot.** Two full seconds of silence on it before you speak. It
  is the only moment in either video a judge will still remember an hour later. It now arrives
  twelve seconds earlier than the first draft, because the opening was cut.
- The rejected snack moved out of the opening and into the lunch beat, where it explains why fixing
  at the table matters instead of being one more statistic before anything has run.
- If it runs long, cut the label check at 2:14 first, then the note home at 2:36.
- Every button, tab and screen this names was checked against the running deployment, including the
  step the narration deliberately does not stop for.

---

## Before you upload

- Export between 3:15 and 4:00. The rules cap it at five minutes.
- Upload to YouTube as **public**, then open it in a logged-out window and confirm it plays.
- Captions in `video/` are timed to an earlier, longer script. Regenerate them from the final cut
  rather than trusting the old timings.
- The recorded visual tracks are from 5 September, before the interface fixes. Record fresh rather
  than narrating over them, or the video will not match the site a judge opens.
