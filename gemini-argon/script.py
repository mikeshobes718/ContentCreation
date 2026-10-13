"""Google Invented Modern AI. So Why Is It Still Catching Up?

Scene format (same as ai-jobs-fear): visual, p, lines, optional hold/tail.
A line is "text" or ("spoken text", "subtitle text") when the TTS needs help.
Visual cues are keyed to line indices.
"""

TITLE = "Google Invented Modern AI."
TITLE2 = "So Why Is It Still Catching Up?"

SCENES = [
    # ------------------------------------------------------------ cold open
    dict(visual="plate", p=dict(plate="vault", label="SEPT 30, 2026",
                                caption=[(1, "Gemini 4 Argon"), (3, "Access: restricted")]), lines=[
        ("On the thirtieth of September, Google announced the most powerful AI model it had ever built.",
         "On the 30th of September, Google announced the most powerful AI model it had ever built."),
        "It was called Gemini 4 Argon. And almost nobody was allowed to use it.",
        "Google said Argon could hunt through software on its own, find security holes, prove they were real, and patch them.",
        "Which is exactly what you'd want from a defender. And exactly what you'd fear from an attacker.",
        "So, at first, it went only to a small circle of vetted cybersecurity partners.",
    ]),
    dict(visual="countdown", p=dict(days=13, date="OCT 13, 2026", price="$2 / $10", unit="per million tokens, input / output"), lines=[
        "Thirteen days later, today, Google flipped the switch.",
        "Argon is now open to Gemini Pro and Ultra subscribers, and to developers on Google's paid API, at a discounted launch price.",
        "It's a strange way to launch a model. Unless you know the last decade at Google.",
        "Because this is the company that invented modern AI. And then spent years losing the race it started.",
    ]),
    dict(visual="title", p=dict(main=True, title=TITLE, sub=TITLE2), lines=[], hold=4.5),

    # ------------------------------------------------------------ 1
    dict(visual="title", p=dict(num="01", title="The Paper"), lines=[], hold=3.2),
    dict(visual="paper", p=dict(), lines=[
        ("In twenty seventeen, eight researchers working at Google published a paper with an almost cocky title. Attention Is All You Need.",
         "In 2017, eight researchers working at Google published a paper with an almost cocky title: “Attention Is All You Need.”"),
        "It described a new kind of neural network called the Transformer.",
        "If that word sounds familiar, it's because it's the T in ChatGPT. Almost every major AI model today is built on it.",
        "Google didn't keep it secret. It published it, openly, for anyone to read and build on.",
    ]),
    dict(visual="plate", p=dict(plate="eight", label="ATTENTION IS ALL YOU NEED · 2017",
                                caption=[(1, "All eight authors eventually left Google")]), lines=[
        "And then, one by one, the people who wrote it walked out the door.",
        "Within a few years, every one of the eight authors had left Google. To start companies, or to join rivals.",
        ("One of them, Noam Shazeer, left to co-found Character dot A I. In twenty twenty-four, Google struck a deal reported at around two point seven billion dollars, largely to bring him back.",
         "One of them, Noam Shazeer, left to co-found Character.AI. In 2024, Google struck a deal reported at around $2.7 billion, largely to bring him back."),
    ]),
    dict(visual="search_money", p=dict(value=162, label="Google Search revenue, 2022", unit="billion"), lines=[
        "Google wasn't short of talent. It even had its own chatbot, internally, years before ChatGPT.",
        "But a chatbot that simply answers your question has an awkward side effect for a company like Google.",
        ("You don't click on the ads. And in twenty twenty-two, those search ads brought in more than a hundred and sixty billion dollars.",
         "You don't click on the ads. And in 2022, those search ads brought in more than $160 billion."),
        "So Google was careful. Some would say too careful.",
    ]),

    # ------------------------------------------------------------ 2
    dict(visual="title", p=dict(num="02", title="Code Red"), lines=[], hold=3.2),
    dict(visual="plate", p=dict(plate="codered", label="NOV 30, 2022",
                                caption=[(1, "ChatGPT: ~100 million users in two months")]), lines=[
        ("On the thirtieth of November, twenty twenty-two, a much smaller company called OpenAI released a free research preview. ChatGPT.",
         "On the 30th of November, 2022, a much smaller company called OpenAI released a free research preview: ChatGPT."),
        "It reached an estimated hundred million users in about two months. At the time, the fastest-growing consumer app ever recorded.",
        "According to The New York Times, Google's management declared a code red.",
    ]),
    dict(visual="bard", p=dict(), lines=[
        ("In February twenty twenty-three, Google rushed out its answer. A chatbot called Bard.",
         "In February 2023, Google rushed out its answer: a chatbot called Bard."),
        "In its very first promotional demo, Bard claimed the James Webb Space Telescope took the first ever picture of a planet outside our solar system.",
        ("It hadn't. That happened in two thousand four, with a different telescope.",
         "It hadn't. That happened in 2004, with a different telescope."),
        "Alphabet's stock fell around eight percent. Roughly one hundred billion dollars of value, gone, because of one wrong sentence.",
    ]),
    dict(visual="quote", p=dict(text="Completely unacceptable.", who="Sundar Pichai, CEO of Google",
                                src="Internal memo, February 2024"), lines=[
        ("A year later, it happened again. Gemini's new image generator produced historically inaccurate pictures of people, and Google had to switch the feature off.",
         "A year later, it happened again. Gemini's new image generator produced historically inaccurate pictures of people, and Google had to switch the feature off."),
        "Sundar Pichai called some of the responses completely unacceptable.",
        "The company that invented the technology now had a reputation for something else entirely. Not being able to ship it.",
    ]),

    # ------------------------------------------------------------ 3
    dict(visual="title", p=dict(num="03", title="The Comeback"), lines=[], hold=3.2),
    dict(visual="merge", p=dict(left="Google Brain", right="DeepMind", merged="Google DeepMind", lead="Led by Demis Hassabis · April 2023"), lines=[
        ("But behind the embarrassments, Google was reorganising. In twenty twenty-three, it merged its two rival AI labs, Google Brain and DeepMind, into one, under Demis Hassabis.",
         "But behind the embarrassments, Google was reorganising. In 2023, it merged its two rival AI labs, Google Brain and DeepMind, into one, under Demis Hassabis."),
        "A year later, Hassabis shared a Nobel Prize, for using AI to predict the structure of proteins.",
    ]),
    dict(visual="plate", p=dict(plate="datacenter", label="TENSOR PROCESSING UNITS",
                                caption=[(1, "Google designs its own AI chips")]), lines=[
        "And Google had something almost nobody else did. Its own AI chips.",
        "While its rivals queued up to buy from Nvidia, Google had spent a decade designing its own, called Tensor Processing Units.",
    ]),
    dict(visual="timeline", p=dict(events=[
        ("NOV 2025", "Gemini 3 tops the LMArena leaderboard", 0),
        ("JAN 2026", "Apple picks Gemini to power Siri", 1),
        ("JAN 2026", "Alphabet hits a $4 trillion valuation", 2),
    ], label="The comeback"), lines=[
        ("In November twenty twenty-five, Gemini 3 went to the top of the most-watched AI leaderboard.",
         "In November 2025, Gemini 3 went to the top of the most-watched AI leaderboard."),
        "Two months later, Apple announced that Gemini would help power Siri.",
        "And Alphabet became only the fourth company in history to be worth four trillion dollars.",
    ]),
    dict(visual="plate", p=dict(plate="crowd", label="GEMINI APP",
                                caption=[(0, "950 million monthly users"), (1, "$195–205 billion: 2026 capex forecast")]), lines=[
        "By the summer of this year, the Gemini app had nine hundred and fifty million monthly users.",
        ("And Google told investors it would spend somewhere between a hundred and ninety-five and two hundred and five billion dollars this year, mostly on AI infrastructure.",
         "And Google told investors it would spend somewhere between $195 and $205 billion this year, mostly on AI infrastructure."),
        "The company that couldn't ship had become the company nobody could ignore.",
    ]),

    # ------------------------------------------------------------ 4
    dict(visual="title", p=dict(num="04", title="The Stumble"), lines=[], hold=3.2),
    dict(visual="missed", p=dict(promise="Gemini 3.5 Pro", said="Promised for June", windows=["JUN", "JUL", "AUG", "SEP"]), lines=[
        "And then it slipped again.",
        ("At its developer conference in May, Pichai said the next model, Gemini three point five Pro, would arrive in June.",
         "At its developer conference in May, Pichai said the next model, Gemini 3.5 Pro, would arrive in June."),
        "June came and went. Bloomberg reported the model was months behind schedule, with problems in one area in particular. Coding.",
        "Some of Google's own engineers reportedly worried that OpenAI and Anthropic were pulling ahead.",
        "Deadline after deadline passed. Gemini three point five Pro never shipped. Argon replaced it.",
    ]),

    # ------------------------------------------------------------ 5
    dict(visual="title", p=dict(num="05", title="Argon"), lines=[], hold=3.2),
    dict(visual="bench", p=dict(title="DeepSWE v1.1 (coding)", src="Google-reported, launch table",
                                bars=[("Gemini 4 Argon", 77.9), ("Claude Opus 5.5", 74.2), ("GPT-6 Astra", 74.1)]), lines=[
        "Which brings us back to today.",
        "On Google's own launch charts, Argon wins most of the tests. On one coding benchmark it scores seventy-eight percent, ahead of Anthropic's Claude Opus and OpenAI's GPT-6 Astra.",
    ]),
    dict(visual="bench", p=dict(title="Artificial Analysis Intelligence Index", src="Independent testing, Artificial Analysis",
                                bars=[("Claude Opus 5.5", 58), ("Gemini 4 Argon", 53), ("GPT-6 Astra", 53)], hl=1), lines=[
        "But every lab picks the tests that flatter it.",
        "On a widely followed independent index, Argon ties with OpenAI's model, and sits behind Anthropic's.",
        "Good. Very good, even. But not the runaway leader Google needed.",
    ]),
    dict(visual="price", p=dict(now=("$2", "$10"), later=("$4", "$20"), until="Nov 30"), lines=[
        "So Google is competing on something else. Price.",
        "For launch, Argon costs two dollars per million tokens going in, and ten coming out. After November, that doubles.",
        "Analysts at Jefferies say rivals may be forced to cut their prices in response.",
    ]),

    # ------------------------------------------------------------ ending
    dict(visual="plate", p=dict(plate="crowd2", label="DISTRIBUTION",
                                caption=[(1, "Search · Android · Chrome · Gmail · YouTube")]), lines=[
        "And that may be the real story. Google doesn't need the smartest model in the world.",
        "It needs a model that's good enough, cheap enough, and already sitting inside the search bar, the phone, the browser, and the inbox of billions of people.",
        "Nobody else has that. Not OpenAI. Not Anthropic.",
    ]),
    dict(visual="end", p=dict(lines=["2017: gave the idea away.", "2026: paying to win it back."]), lines=[
        "In twenty seventeen, Google gave the world the idea that started all of this, for free.",
        "Now it's spending around two hundred billion dollars this year trying to win it back.",
        "Whether that's a comeback, or just a very expensive catch-up, we're about to find out.",
    ], tail=4.0),
]
