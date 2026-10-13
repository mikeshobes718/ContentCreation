# The Machine Is Coming For Your Job

An 8.7-minute explainer in the style of Fern ("armchair documentary") about how scared people are of AI taking their jobs, and how much of that fear the data actually supports (as of October 2026).

| File | What |
|---|---|
| `out/the-machine-is-coming-for-your-job.mp4` | Final video, 1080p30, AAC 192k, loudness-normalized to -14 LUFS |
| `out/the-machine-is-coming-for-your-job.srt` | Captions (upload these to YouTube) |
| `out/thumbnail.png` | 1920x1080 thumbnail |
| `pipeline/script.py` | The script: every narration line and the visual it plays over |

## YouTube upload copy

**Title:** The Machine Is Coming For Your Job

**Description:**

> In February 2026, Block cut 40% of its staff and blamed AI. Its stock jumped 20%. One in five announced layoffs this year has been blamed on AI, and half of Americans now worry it could cost their household a job. But how much of that fear does the data actually back up?
>
> 0:00 One evening in February
> 1:12 The Oldest Fear
> 2:38 This Time Is Different?
> 3:33 The Receipts
> 5:37 The Canaries
> 7:04 Why It Feels So Bad
> 7:59 The Hammer

## Sources

- Block layoffs (Feb 26, 2026): [The Block](https://www.theblock.co/post/391520/block-inc-slashes-40-staff-jack-dorsey-pushes-smaller-flatter-ai-strategy), [Fortune](https://fortune.com/2026/02/27/block-jack-dorsey-ceo-xyz-stock-square-4000-ai-layoffs/), [LeadDev](https://leaddev.com/ai/blocks-40-ai-driven-layoff-is-a-warning) (2019 headcount)
- AI-attributed job cuts: [Challenger, Gray & Christmas, August 2026 report](https://www.challengergray.com/wp-content/uploads/2026/09/Challenger-Report-August-2026.pdf), [June 2026 report](https://www.challengergray.com/wp-content/uploads/2026/07/Challenger-Report-June2600986996.pdf)
- Polls: Reuters/Ipsos, June 2026 ([summary](https://allwork.space/2026/06/half-of-americans-fear-ai-could-cost-their-household-a-job-new-poll-finds/)); Quinnipiac, March 2026
- AI washing: [Fortune](https://fortune.com/2026/02/10/ai-washing-and-forever-layoffs-why-companies-keep-cutting-jobs-even-amid-rising-profits/), [Quartz](https://qz.com/ai-washing-layoffs-white-collar-jobs), Forrester 2026 predictions
- Young workers: Brynjolfsson, Chandar & Chen, "Canaries in the Coal Mine" (Stanford Digital Economy Lab, 2025); US Census Bureau working paper (April 2026); [EPI](https://www.epi.org/blog/class-of-2026-what-occupation-data-show-about-ai-and-the-young-college-graduate-workforce/); [Washington Post on the UCLA/CESifo study](https://www.washingtonpost.com/education/2026/09/28/is-ai-killing-jobs-college-grads-not-yet-new-study-says/); Yale Budget Lab
- History: Keynes, "Economic Possibilities for our Grandchildren" (1930); "The Triple Revolution" memo (1964); James Bessen, "Toil and Technology" (IMF, 2015); Autor, Chin, Salomons & Seegmiller, "New Frontiers: The Origins and Content of New Work" (2022)
- Amodei warning: Axios, May 2025. McDermott warning: [Fortune, March 2026](https://fortune.com/2026/03/17/servicenow-ceo-bill-mcdermott-gen-z-graduates-face-30-unemployment-next-couple-of-years-ai-takes-over/)

The ATM and "Canaries" charts are stylized (shape, not exact data points) and labeled that way on screen. The 13.6M layoffs figure is an estimate (about 1.7M JOLTS layoffs and discharges per month times 8 months).

## Rebuilding

Everything is generated from code: offline neural TTS (Kokoro, voice `bm_george`), Skia motion graphics, and a numpy-synthesized ambient score. No stock footage, no licensed music.

```bash
pip install kokoro-onnx soundfile skia-python numpy
apt-get install -y ffmpeg libegl1 libgl1
mkdir -p models && cd models
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
cd .. && ./build.sh
```

- Edit lines in `pipeline/script.py`; TTS lines are cached, so only changed lines are re-voiced.
- Swap the narrator with `VOICE=am_michael ./build.sh` (or record your own voice and drop the WAVs into `build/lines/`, keeping the filenames).
- Re-render specific scenes with `ONLY=26,27 ./build.sh`.
- `python3 pipeline/render.py --stills` writes one frame per scene to `build/stills/` for quick review.
