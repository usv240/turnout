# Turnout: demo video script

**Runs 3:50.** 449 spoken words at a comfortable 135 a minute, plus the 31 seconds of pauses the beats below ask for. The rules cap the video at five minutes.

Record from the deployed URL, clean browser profile, 1920 by 1080, light theme. **Press Reset before every take.**

Each beat gives three things: what to point at, what to do next, and the line to say. **Read only the quoted line out loud.** Everything else is a direction to you.

The timecodes are computed from the words plus those pauses, not estimated, so a beat that asks for six seconds of silence has six seconds in the clock. If a take runs long, cut a sentence rather than reading faster. The recording notes say which one to drop first.

---

## 0:00  The cold open

**Point at:** Black, then the empty apparatus bay. No interface yet.

**Then:** Hold on the bay. Do not show the product yet.

**Say:**

> This is a fire station at two in the afternoon on a Tuesday. The tone just dropped. Nobody is coming, and the chief is finding that out right now.

## 0:14  The problem

**Point at:** The landing page. Let one stat card be readable, not all three.

**Then:** Scroll slowly. Do not stop on each card.

**Say:**

> Most American firefighters are volunteers. Chief Dana Ortiz runs one of those departments. Her roster looks covered, right up until Tuesday afternoon, when everyone is at work. Today she finds out only when the call comes in. And in an emergency, that is not a scheduling inconvenience. Minutes matter.

## 0:37  What Turnout is

**Point at:** The hero line.

**Then:** Click through to the demo. Press Reset if you have not already.

**Say:**

> Turnout finds that gap before the emergency does.

## 0:43  Roll call

**Point at:** The Phones tab. The half past six roll call going out.

**Then:** Let two or three replies land before you speak. Point at the ones saying till 10 and morning only.

**Say:**

> Every morning it texts each of the fourteen volunteers one question about tomorrow. One character to answer. It reads till ten and morning only as easily as yes, and the moment anyone sends STOP it never texts them again.

## 1:02  The gap

**Point at:** The Station board. Thursday ten to two, north, turning red.

**Then:** Expand the numbers on that row and hold there while you speak.

**Say:**

> Before Thursday arrives, Turnout finds the dangerous gap. Ten to two, north district. Based on this department's own call history, who is actually available, and today's weather, there is no qualified crew. And every number behind that decision is right here on the screen.

## 1:24  The two asks

**Point at:** Back to the Phones tab. The two targeted asks. Point at the one tagged as held.

**Then:** Show the yes coming back.

**Say:**

> It asks the two people most likely to say yes for that exact window. One of them is asleep, so his message waits until his quiet hours end. That is enforced in code, not by asking a model politely. He says yes. They have a driver now, and they are still short a firefighter.

## 1:50  Asking the neighbours

**Point at:** The Network tab. The request leaving Millbrook.

**Then:** This is the sequence the whole video is for. Slow down.

**Say:**

> Turnout still cannot make a crew. So instead of waking the chief, its agent asks the neighbouring departments' agents directly.

## 2:05  The answers

**Point at:** Riverton answering, then Cedar Hollow.

**Then:** Say nothing at all while the two answers arrive. Six seconds of silence, and it is the most valuable silence in the video. (6 seconds before you speak.)

**Say:**

> Riverton can help. Cedar Hollow cannot, because helping would open a dangerous gap of its own, and it says so rather than going quiet.

## 2:17  Why this is different

**Point at:** The signed request, and the line saying they verified who was asking.

**Then:** Let it sit on screen.

**Say:**

> These are separate departments, each running its own agent. The agents negotiate directly over the open Agent-to-Agent protocol. Every request is signed, so nobody commits a fire truck to a message they cannot verify.

## 2:33  Handing it over

**Point at:** Back to the board, still short a firefighter.

**Then:** Move to the chief's phone.

**Say:**

> Only now does Turnout need the chief.

## 2:38  One decision

**Point at:** The chief's phone. One message covering both windows.

**Then:** Tap 1. Let the board turn green.

**Say:**

> Turnout handled the roll call, found the gap, asked the right volunteers and negotiated mutual aid. It brings Dana exactly one decision, one text covering both open windows. She taps once, and Riverton's agent confirms without waking anybody. Eight seconds of her day.

## 3:00  The volunteers

**Point at:** Navigate to /crew.html. One volunteer's card.

**Then:** Point at the asks-this-week count, then the held message. Keep this beat short.

**Say:**

> And volunteers are not invisible inputs. They can see what Turnout knows, how often it asks them, and when it deliberately left them alone.

## 3:14  Try it yourself

**Point at:** Navigate to /try.html, Score your own window. Then /start.html for a moment.

**Then:** Type a window, press the button, let a real score come back. Do not narrate the form. (4 seconds before you speak.)

**Say:**

> And none of this is a canned demo. Score your own window with your own numbers, paste your own roster to set up a department, or call the same API with the public sandbox key on the landing page.

## 3:34  What changed

**Point at:** Back to the board, all green.

**Then:** Hold here.

**Say:**

> The chief did not spend her morning chasing fourteen people. Turnout found the risk, closed what it could, negotiated what it could not, and asked her once.

## 3:47  Close

**Point at:** Hold on the green board.

**Then:** End the recording.

**Say:**

> Turnout. So that there is always someone coming.

---

## Recording notes

- Play the five steps in one take and cut later.
- **Asking the neighbours through One decision is the whole video.** The six second silence while the two answers arrive is a direction, not a gap to fill.
- The protocol is named only after the plain explanation. Never before it.
- If a take runs long, cut the signature sentence in Why this is different, then the held message in The two asks.
- Everything named above was checked against the live deployment. The line saying a peer verified the request only appears when one really did.
- The incident report and the drafted federal form are not in this script. They are real, and the story ends when the chief approves, so a second workflow after that dilutes it. They stay in the README and on the site.

## Before you upload

- Export near 3:50. Anything under four minutes is comfortable.
- Upload to YouTube as **public**, then open it in a logged-out window and confirm it plays.
- Captions in `video/` are timed to an earlier, longer script. Regenerate them from the final cut.
- The recorded visual tracks are from 5 September, before the interface fixes. Record fresh rather than narrating over them, or the video will not match the site a judge opens.

## Why each beat is here

Rules.md scores five equally weighted criteria, and says judges may judge on the video alone. So this is not a Presentation exhibit: it may be the only evidence a judge ever sees, for all five. If a beat is not doing one of these jobs, cut it.

| Beat | What it is carrying |
|---|---|
| 0:14 The problem | Potential Impact. The problem, who it is for, and why minutes matter |
| 1:02 The gap | Technical Implementation. Every number behind the decision is on screen |
| 1:24 The two asks | Technical Implementation. A promise kept in code, not in a prompt |
| 1:50 Asking the neighbours | Creativity and Originality. The sequence nobody else will have |
| 2:38 One decision | The hackathon's own theme. Autonomous work, one human decision |
| 3:00 The volunteers | Design. A complete product, including the person it asks things of |
| 3:14 Try it yourself | Technical Implementation. Proof it is live, and an invitation to test it |
| 3:34 What changed | Presentation. The change stated once, plainly, before the tagline |
