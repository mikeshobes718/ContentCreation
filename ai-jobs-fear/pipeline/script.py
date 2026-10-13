"""The script: narration lines plus the visual each scene shows.

Each scene is a dict:
  visual  - name of a draw function in render.py
  p       - params for that visual
  lines   - narration. A line is either a string (spoken + subtitled as-is)
            or a (spoken, subtitle) tuple when the TTS needs a phonetic spelling.
  hold    - optional seconds of silence (title cards have no narration)

Visual cues are keyed to line indices: an element tied to line 2 appears when
line 2 starts being spoken.
"""

TITLE = "The Machine Is Coming For Your Job"
SUBTITLE = "Is the fear of AI taking our jobs justified?"

SCENES = [
    # ---------------------------------------------------------------- cold open
    dict(visual="office", p=dict(off_from=1, off_frac=0.4, label="FEB 26, 2026"), lines=[
        ("On the twenty-sixth of February, twenty twenty-six, about four thousand people at one of America's "
         "best-known fintech companies found out they no longer had a job.",
         "On the 26th of February, 2026, about four thousand people at one of America's "
         "best-known fintech companies found out they no longer had a job."),
        "The company was Block, the business behind Square and Cash App.",
        "It wasn't in trouble. Its CEO, Jack Dorsey, said so himself. The business was strong.",
        "The reason he gave was artificial intelligence.",
    ]),
    dict(visual="stock", p=dict(name="BLOCK, INC.", ticker="XYZ", headcount=1), lines=[
        "Block went from more than ten thousand employees to fewer than six thousand.",
        "And that evening, its stock jumped more than twenty percent.",
        "Wall Street wasn't mourning. It was celebrating.",
    ]),
    dict(visual="dots", p=dict(frac=0.53, big="53%", cue=0,
                               caption="of Americans worry AI could cost them, or someone in their household, a job",
                               source="Reuters/Ipsos poll, June 2026"), lines=[
        "If you've felt a low hum of dread every time someone says the words AI agent in a meeting, you are not alone.",
        "Roughly half of Americans now say they worry AI could cost them, or someone in their household, a job.",
        "So, is the fear justified? Or is something else going on?",
        "To answer that, we have to go back about two hundred years. To a group of very angry men with very large hammers.",
    ]),
    dict(visual="title", p=dict(main=True, title=TITLE, sub=SUBTITLE), lines=[], hold=4.5),

    # ---------------------------------------------------------------- 1
    dict(visual="title", p=dict(num="01", title="The Oldest Fear"), lines=[], hold=3.2),
    dict(visual="timeline", p=dict(events=[
        ("1811", "Luddites smash knitting frames", 0),
        ("1812", "Machine-breaking made a capital crime", 1),
        ("1930", "Keynes: “technological unemployment”", 2),
        ("1964", "“Triple Revolution” memo to LBJ", 3),
        ("2022", "ChatGPT", 4),
    ]), lines=[
        ("In eighteen eleven, in the villages around Nottingham, England, textile workers began breaking into "
         "workshops at night and smashing the machines that were replacing them.",
         "In 1811, in the villages around Nottingham, England, textile workers began breaking into "
         "workshops at night and smashing the machines that were replacing them."),
        "They called themselves Luddites. Parliament's response was to make machine-breaking punishable by death.",
        ("In nineteen thirty, the economist John Maynard Keynes gave the fear a name. Technological unemployment.",
         "In 1930, the economist John Maynard Keynes gave the fear a name: technological unemployment."),
        ("In nineteen sixty-four, a group of scientists and activists sent President Lyndon Johnson a memo warning "
         "that cybernation would soon create mass joblessness.",
         "In 1964, a group of scientists and activists sent President Lyndon Johnson a memo warning "
         "that ‘cybernation’ would soon create mass joblessness."),
        "Every generation has had its version of this moment. And every generation, so far, has been wrong about the ending.",
    ]),
    dict(visual="atm", p=dict(), lines=[
        "Take the ATM. When cash machines spread across America, everyone assumed bank tellers were finished.",
        "Instead, ATMs made branches cheaper to run, banks opened more of them, and for decades the number of tellers actually grew.",
    ]),
    dict(visual="bignum", p=dict(value=60, suffix="%", caption="of US jobs today are in occupations that didn't exist in 1940",
                                 source="Autor, Chin, Salomons & Seegmiller (MIT), 2022"), lines=[
        ("Economists estimate that around sixty percent of Americans today work in jobs that didn't even exist in nineteen forty.",
         "Economists estimate that around sixty percent of Americans today work in jobs that didn't even exist in 1940."),
        "Technology destroys jobs. It also invents them. It just never asks permission, and it rarely hands the new ones to the same people.",
    ]),

    # ---------------------------------------------------------------- 2
    dict(visual="title", p=dict(num="02", title="This Time Is Different?"), lines=[], hold=3.2),
    dict(visual="muscle", p=dict(words=["Writing", "Coding", "Analysis", "Customer support"]), lines=[
        "Here's the problem with that comforting story. The machines of the past replaced muscle. This one is going after the mind.",
        "Writing. Coding. Analysis. Customer support. The work a college degree was supposed to protect.",
    ]),
    dict(visual="quote", p=dict(text="AI could wipe out half of all entry-level white-collar jobs.",
                                who="Dario Amodei, CEO of Anthropic", src="Axios, May 2025", extra="and push unemployment to 10–20%", extra_cue=1), lines=[
        ("In May twenty twenty-five, Dario Amodei, CEO of the AI company Anthropic, warned that AI could wipe out "
         "half of all entry-level white-collar jobs within five years.",
         "In May 2025, Dario Amodei, CEO of the AI company Anthropic, warned that AI could wipe out "
         "half of all entry-level white-collar jobs within five years."),
        "And push unemployment as high as ten to twenty percent.",
    ]),
    dict(visual="bignum", p=dict(value=30, suffix="%", caption="unemployment among new graduates: ServiceNow CEO Bill McDermott's warning",
                                 source="March 2026"), lines=[
        "This year, the CEO of ServiceNow suggested unemployment among new graduates could reach thirty percent.",
        "These aren't conspiracy theorists. These are the people building and selling the technology.",
        "Which, as we'll see, is part of the problem.",
    ]),

    # ---------------------------------------------------------------- 3
    dict(visual="title", p=dict(num="03", title="The Receipts"), lines=[], hold=3.2),
    dict(visual="bignum", p=dict(value=40, suffix="%", caption="of all announced US job cuts in May 2026 cited AI. A record.",
                                 source="Challenger, Gray & Christmas"), lines=[
        ("Since twenty twenty-three, the outplacement firm Challenger, Gray and Christmas has tracked how many "
         "announced layoffs companies blame on AI.",
         "Since 2023, the outplacement firm Challenger, Gray & Christmas has tracked how many "
         "announced layoffs companies blame on AI."),
        "In May this year, AI was cited in forty percent of all announced job cuts in the United States. The highest share ever recorded.",
    ]),
    dict(visual="bignum", p=dict(value=116175, suffix="", caption="job cuts blamed on AI in 2026, through August. Roughly 1 in 5.",
                                 source="Challenger, Gray & Christmas, August 2026 report"), lines=[
        ("Through August, companies blamed AI for more than a hundred and sixteen thousand cuts in twenty twenty-six. "
         "Roughly one in every five.",
         "Through August, companies blamed AI for more than 116,000 cuts in 2026. Roughly one in every five."),
        "That sounds enormous. Until you zoom out.",
    ]),
    dict(visual="compare", p=dict(small=116175, big=13_600_000,
                                  small_label="Announced cuts blamed on AI", big_label="All US layoffs & discharges",
                                  period="Jan–Aug 2026", source="Challenger; BLS JOLTS (approx. 1.7M per month)"), lines=[
        "In a typical month, the US government counts somewhere around one and a half to two million layoffs and discharges.",
        "Against that backdrop, the AI-attributed cuts for the entire year so far add up to less than one percent.",
    ]),
    dict(visual="statement", p=dict(word="AI WASHING", defn="Blaming the robots for cuts you wanted to make anyway."), lines=[
        "And it isn't even clear the companies mean it.",
        "Analysts have a name for it now. AI washing. Blaming the robots for cuts you wanted to make anyway.",
    ]),
    dict(visual="cards", p=dict(cards=[
        ("BLOCK", "~3,700 staff in 2019", "10,000+ before the cuts", 0),
        ("AMAZON", "14,000 corporate jobs cut, Oct 2025", "“not really AI-driven … it really is culture” — Andy Jassy", 1),
        ("KLARNA", "AI assistant “doing the work of 700 agents”", "then: hiring humans again", 2),
        ("FORRESTER", "prediction", "over half of AI layoffs quietly reversed", 3),
    ]), lines=[
        ("Block had grown from around thirty-seven hundred employees in twenty nineteen to more than ten thousand. Plenty of "
         "observers said that looked less like an AI revolution and more like a pandemic hiring hangover.",
         "Block had grown from around 3,700 employees in 2019 to more than 10,000. Plenty of "
         "observers said that looked less like an AI revolution and more like a pandemic hiring hangover."),
        ("When Amazon cut fourteen thousand corporate jobs in October twenty twenty-five, Andy Jassy later said the cuts "
         "weren't really about AI at all. They were about culture.",
         "When Amazon cut 14,000 corporate jobs in October 2025, Andy Jassy later said the cuts "
         "weren't really about AI at all. They were about culture."),
        "Klarna, which once boasted that its AI assistant was doing the work of seven hundred customer service agents, "
        "later admitted quality had suffered, and started hiring humans again.",
        "The research firm Forrester now predicts that more than half of AI-attributed layoffs will be quietly reversed.",
    ]),
    dict(visual="stock", p=dict(name="THE MAGIC WORDS", ticker="", headcount=None, again=True), lines=[
        "Saying AI in a layoff announcement does two things at once. It makes the cuts sound inevitable.",
        "And it makes investors very, very happy.",
    ]),

    # ---------------------------------------------------------------- 4
    dict(visual="title", p=dict(num="04", title="The Canaries"), lines=[], hold=3.2),
    dict(visual="canary", p=dict(src="Stylized from Brynjolfsson, Chandar & Chen, “Canaries in the Coal Mine” (Stanford, 2025)"), lines=[
        "But if the layoff numbers are mostly noise, there's one place where the signal is harder to dismiss.",
        ("In twenty twenty-five, researchers at Stanford dug into payroll data covering millions of American workers.",
         "In 2025, researchers at Stanford dug into payroll data covering millions of American workers."),
        "They found that workers aged twenty-two to twenty-five, in the jobs most exposed to AI, like software development "
        "and customer service, saw employment fall by about thirteen percent relative to everyone else.",
        "Older workers in the very same jobs? Mostly fine. Some groups were even growing.",
        "The authors called their paper, Canaries in the Coal Mine.",
    ]),
    dict(visual="split", p=dict(
        left=("AI IS ALREADY HITTING", "YOUNG WORKERS", ["Stanford / ADP: −13% for ages 22–25 in exposed jobs",
                                                     "US Census working paper: −12% early-career in most exposed industries"]),
        right=("IT'S A BROADER", "HIRING SLOWDOWN", ["UCLA / CESifo: recent-grad unemployment 7.3%, not unusual",
                                                  "Yale Budget Lab: no economy-wide AI disruption yet"]),
        right_cue=1), lines=[
        ("A working paper from the US Census Bureau this year found something similar. Early-career employment in the "
         "most AI-exposed industries, down around twelve percent since ChatGPT launched.",
         "A working paper from the US Census Bureau this year found something similar: early-career employment in the "
         "most AI-exposed industries, down around twelve percent since ChatGPT launched."),
        "Not everyone agrees. Economists at UCLA and the Yale Budget Lab find little sign of an AI-driven unemployment spike. "
        "They point to a broad hiring slowdown that's hitting young people everywhere, AI or not.",
    ]),
    dict(visual="ladder", p=dict(rungs=["Director", "Manager", "Senior", "Associate", "Junior", "Intern"], gone=2, cue=0), lines=[
        "But notice what both sides are describing. It isn't mass firing. It's the quiet disappearance of the first rung on the ladder.",
        "Nobody gets a layoff email for a job that was never posted.",
    ]),

    # ---------------------------------------------------------------- 5
    dict(visual="title", p=dict(num="05", title="Why It Feels So Bad"), lines=[], hold=3.2),
    dict(visual="megaphone", p=dict(items=["The people selling it", "The stock market", "The silence"]), lines=[
        "So why does the fear feel so much bigger than the data?",
        "Part of it is who's telling the story. The loudest voices on AI and jobs are the people raising billions of dollars "
        "on the promise that it will change everything.",
        "Part of it is the stock market, which has learned to reward any CEO who says the magic words.",
        "And part of it is that the damage, where it does exist, is invisible. A hiring freeze doesn't make headlines. "
        "A graduate sending their two-hundredth application doesn't trend.",
    ]),
    dict(visual="bars", p=dict(title="Worry their own job may become obsolete", bars=[("Apr 2025", 21), ("Mar 2026", 30)],
                               source="Quinnipiac University polls"), lines=[
        "In March, a Quinnipiac poll found thirty percent of Americans worry their own job may become obsolete. A year earlier, it was twenty-one.",
        "The fear is growing faster than the evidence. But that doesn't make the fear wrong. It might just be early.",
    ]),

    # ---------------------------------------------------------------- ending
    dict(visual="hammer", p=dict(), lines=[
        "The Luddites weren't actually wrong about the machines. The machines really did take their jobs. "
        "What they got wrong was thinking they could stop them.",
        "Their grandchildren ended up with jobs the Luddites couldn't have imagined. But the Luddites themselves didn't get those jobs. "
        "Dozens were hanged. Others were shipped off to Australia.",
    ]),
    dict(visual="end", p=dict(lines=["Not whether there will be work.", "Who pays for the transition.", "Is anyone planning for it?"]), lines=[
        ("That's the real question about AI. Not whether there'll be work in twenty years. There almost certainly will be.",
         "That's the real question about AI. Not whether there'll be work in twenty years. There almost certainly will be."),
        "It's who pays for the transition. And whether anyone is planning for it at all.",
        "Right now, the honest answer is, not really.",
    ], tail=4.0),
]
