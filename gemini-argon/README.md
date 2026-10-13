# Google Invented Modern AI. So Why Is It Still Catching Up?

A Fern-style explainer on Gemini 4 Argon (rolled out broadly Oct 13, 2026) and Google's decade-long AI arc: the Transformer paper, the ChatGPT "code red", Bard's $100B mistake, the Gemini 3 comeback, the Gemini 3.5 Pro stumble, and Argon's price war.

## Finish it with your ElevenLabs voice (new session)

1. Environment variables (either naming works): `ElevenLabsAPIKey` + `ElevenLabsMyVoiceID`, or `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID`. Model defaults to `eleven_v4`.
2. Network access → Allowed domains: `api.elevenlabs.io`.
3. In a new session: `cd gemini-argon && VOICE_BACKEND=elevenlabs ./build.sh`

Takes about 30 minutes, mostly the frame render. Outputs land in `out/`: the MP4, `.srt` captions, `thumbnail.png`, and `chapters.txt`.

Voice tuning knobs: `EL_STABILITY` (default 0.45; lower is more expressive), `EL_SIMILARITY` (0.85), `EL_STYLE` (0.15). Changing any of them re-voices every line.

**Your own recording or Qwen3-TTS instead:** run `./build.sh` once to get `build/lines_manifest.tsv`, record or generate one WAV per row with the listed filename into `build/lines/`, then run `VOICE_BACKEND=files ./build.sh`.

## How it's built

| Part | Tool | Cost |
|---|---|---|
| Script and narration lines | `script.py` | |
| Voice | ElevenLabs / Kokoro / your WAVs (`pipeline/tts.py`) | Creator plan |
| 3D shots (mannequins, vault, data center, crowds) | Blender Eevee, procedural (`blender/plates.py`), committed in `plates/` | $0 |
| Graphics, charts, overlays | Skia (`pipeline/render.py`) | $0 |
| Score | numpy synth with ducking (`pipeline/mix.py`) | $0 |

Edit a line in `script.py` and only that line is re-voiced. `python3 pipeline/render.py --stills` writes one frame per scene to `build/stills/` for a quick check.

## YouTube copy

**Title:** Google Invented Modern AI. So Why Is It Still Catching Up?

**Description:**
> On September 30, Google announced the most powerful AI model it had ever built, then refused to let almost anyone use it. Thirteen days later, Gemini 4 Argon is out for everyone. Here's how the company that invented the Transformer spent a decade losing, then winning, then chasing the AI race it started.

Chapters: generated into `out/chapters.txt` from the real timing.

## Sources

- Argon launch and access: [Logan Kilpatrick on X](https://x.com/OfficialLoganK/status/2110038940841545827), [VentureBeat](https://venturebeat.com/technology/google-makes-gemini-4-argon-broadly-available-with-limited-time-low-api-pricing-of-2-10-per-1m-token), [Android Headlines](https://www.androidheadlines.com/2026/10/google-rolls-out-gemini-4-argon-ai-model.html), [Google blog](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-argon/), [TechCrunch](https://techcrunch.com/2026/09/30/google-releases-gemini-4-argon-called-its-most-powerful-model-yet/)
- Cyber gating / Fairwind: [TechWire Asia](https://techwireasia.com/2026/10/google-gemini-4-argon-cybersecurity-access/), [Digital Watch](https://dig.watch/updates/google-gemini-4-argon-restricted-access)
- Benchmarks: [Emergent (Google table)](https://emergent.sh/learn/gemini-4-argon-benchmarks), Artificial Analysis Intelligence Index via [CNBC](https://www.cnbc.com/2026/10/02/tech-download-google-argon-frontier-openai-anthropic.html)
- Pricing reaction: [Benzinga (Jefferies)](https://www.benzinga.com/markets/tech/26/10/62129995/google-turns-up-ai-heat-with-gemini-4-argon-rivals-may-have-to-cut-prices-analyst), [Stocktwits (JPMorgan, Bloomberg employee doubts)](https://stocktwits.com/news-articles/markets/equity/googl-stock-gemini-4-argon-launch-reclaim-leadership/cZD05VWRBip)
- Gemini 3.5 Pro delays: [Outlook Business (Bloomberg/Reuters)](https://www.outlookbusiness.com/corporate/google-delays-gemini-35-pro-release-over-coding-issues), [Tech Insider](https://tech-insider.org/gemini-3-5-pro-delayed-2026/)
- Comeback: [PYMNTS ($4T, Apple/Siri)](https://www.pymnts.com/google/2026/google-parent-companys-market-cap-hits-4-trillion-amid-ai-gains/), [MarketBeat Q2 2026 call (950M MAU, capex)](https://www.marketbeat.com/instant-alerts/alphabet-q2-earnings-call-highlights-2026-07-22/)
- History: [Attention Is All You Need](https://en.wikipedia.org/wiki/Attention_Is_All_You_Need); Bard error [NPR](https://www.npr.org/2023/02/09/1155650909/google-chatbot--error-bard-shares); Gemini image pause [MPR/NPR](https://www.mprnews.org/story/2024/02/28/google-ceo-pichai-says-geminis-ai-image-results-offended-our-users); Google "code red" (New York Times, Dec 2022); Character.AI deal (Wall Street Journal, 2024); Alphabet FY2022 10-K (Search & other revenue $162.5B)

Benchmark figures marked "Google-reported" come from Google's launch table and have not been independently verified.
