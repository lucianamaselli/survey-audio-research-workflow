"""Review a transcript and summarize the signal in a mono PCM WAV file."""

import argparse
from array import array
import json
import math
from pathlib import Path
import re
import sys
import wave


def normalized_words(text):
    return re.findall(r"\w+", text.casefold())


def audit(audio_path, transcript, reference=None):
    with wave.open(str(audio_path), "rb") as audio:
        if (audio.getnchannels(), audio.getsampwidth()) != (1, 2):
            raise ValueError("Expected mono, 16-bit PCM WAV audio.")
        sample_rate = audio.getframerate()
        samples = array("h", audio.readframes(audio.getnframes()))
    if sys.byteorder == "big":
        samples.byteswap()
    if not samples:
        raise ValueError("The audio file contains no samples.")

    frame_size = max(1, round(sample_rate * 0.02))
    quiet_samples = 0
    for start in range(0, len(samples), frame_size):
        frame = samples[start:start + frame_size]
        power = sum(sample * sample for sample in frame) / len(frame)
        if power <= (32768 * 10 ** (-40 / 20)) ** 2:
            quiet_samples += len(frame)
    rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
    reasons = []
    if not normalized_words(transcript):
        reasons.append("empty transcript")
    if reference is not None and normalized_words(transcript) != normalized_words(reference):
        reasons.append("differs from the known synthetic reference")
    return {
        "duration_seconds": round(len(samples) / sample_rate, 3),
        "rms_dbfs": round(20 * math.log10(rms / 32768), 2) if rms else None,
        "low_energy_fraction": round(quiet_samples / len(samples), 3),
        "review_reasons": reasons,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    reference = args.reference.read_text(encoding="utf-8") if args.reference else None
    print(json.dumps(audit(args.audio, args.transcript.read_text(encoding="utf-8"), reference),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
