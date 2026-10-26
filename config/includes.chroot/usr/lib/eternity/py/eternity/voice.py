"""Voice input for Eternity: push-to-talk capture from PipeWire, speech to text with whisper.cpp
(on this device, nothing leaves it), and a small set of direct voice commands that need no model.

    text = listen()                      # records until 0.8 s of silence, transcribes
    intent(text)                         # ("exec", "xfce4-terminal") for "open the terminal", else None

Capture: `pw-record` streams 16 kHz mono s16 PCM to stdout; `capture()` keeps the audio from the
first frame above the energy threshold until `silence_s` of quiet, or `max_s`. Transcription:
`whisper-cli -m /opt/eternity/models/stt.bin` (ggml-small.en-q5_1, bundled by ai/models.manifest).
"""
import array
import math
import os
import re
import shutil
import subprocess
import tempfile
import wave
from typing import Iterable, List, Optional, Tuple

RATE = 16000
FRAME_MS = 20
FRAME_BYTES = RATE * FRAME_MS // 1000 * 2       # 20 ms of s16 mono
THRESHOLD = 600.0                               # RMS above this is speech (quiet room noise is ~100-300)
MODELS_DIR = os.environ.get("ETERNITY_MODELS_DIR", "/opt/eternity/models")
STT_MODEL = os.path.join(MODELS_DIR, "stt.bin")


class VoiceError(Exception):
    pass


# ----------------------------------------------------------------------------- capture
def rms(frame: bytes) -> float:
    if len(frame) < 2:
        return 0.0
    a = array.array("h", frame[: len(frame) // 2 * 2])
    return math.sqrt(sum(x * x for x in a) / len(a))


def capture(frames: Iterable[bytes], max_s: float = 15.0, silence_s: float = 0.8, wait_s: float = 5.0,
            threshold: float = THRESHOLD, pre_ms: int = 300) -> bytes:
    """Audio from the first loud frame until `silence_s` of quiet (or `max_s`). Empty when nobody
    speaks within `wait_s`. Keeps `pre_ms` of lead-in so the first syllable is not clipped."""
    out = bytearray()
    lead = bytearray()
    lead_max = pre_ms * FRAME_BYTES // FRAME_MS
    speaking = False
    quiet_ms = 0
    total_ms = 0
    for frame in frames:
        total_ms += FRAME_MS
        loud = rms(frame) >= threshold
        if not speaking:
            lead += frame
            if len(lead) > lead_max:
                del lead[: len(lead) - lead_max]
            if loud:
                speaking = True
                out += lead
            elif total_ms >= wait_s * 1000:
                return b""
            continue
        out += frame
        quiet_ms = 0 if loud else quiet_ms + FRAME_MS
        if quiet_ms >= silence_s * 1000 or len(out) >= max_s * RATE * 2:
            break
    return bytes(out)


def write_wav(path: str, data: bytes) -> None:
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)


def record(max_s: float = 15.0, silence_s: float = 0.8, wait_s: float = 5.0) -> bytes:
    """Record from the default source through PipeWire until silence."""
    rec = shutil.which("pw-record") or shutil.which("pw-cat")
    if not rec:
        raise VoiceError("no microphone capture tool (pw-record is missing)")
    cmd = [rec] + (["--record"] if rec.endswith("pw-cat") else []) + \
          ["--rate", str(RATE), "--channels", "1", "--format", "s16", "--raw", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def frames():
        assert proc.stdout is not None
        while True:
            chunk = proc.stdout.read(FRAME_BYTES)
            if not chunk:
                return
            yield chunk
    try:
        return capture(frames(), max_s=max_s, silence_s=silence_s, wait_s=wait_s)
    finally:
        proc.kill()
        proc.wait()


# ----------------------------------------------------------------------------- transcription
def transcribe(wav_path: str, binary: Optional[str] = None, model: str = STT_MODEL, language: str = "en") -> str:
    binary = binary or shutil.which("whisper-cli") or shutil.which("whisper-cpp")
    if not binary or not os.path.exists(binary):
        raise VoiceError("voice input is not installed (whisper-cli missing)")
    if not os.path.exists(model):
        raise VoiceError(f"speech model missing: {model}")
    cmd = [binary, "-m", model, "-f", wav_path, "-l", language, "-nt", "-np", "--no-prints", "-t", str(max(1, min(8, os.cpu_count() or 4)))]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError) as e:
        raise VoiceError(f"whisper failed: {e}")
    lines = [ln.strip() for ln in out.splitlines() if ln.strip() and not ln.startswith("[")]
    text = " ".join(lines)
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)", "", text)      # [BLANK_AUDIO], (music)
    return " ".join(text.split()).strip()


def listen(max_s: float = 15.0, on_state=None) -> str:
    """Record one utterance and return its text ('' when nothing was said)."""
    if on_state:
        on_state("listening")
    data = record(max_s=max_s)
    if not data:
        return ""
    if on_state:
        on_state("transcribing")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    try:
        write_wav(path, data)
        return transcribe(path)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


# ----------------------------------------------------------------------------- speech (TTS)
# Eternity speaks its answers with piper (on this device, offline). The voice setting picks a model:
# calm and bright are two bundled piper voices (roles tts-calm / tts-bright in ai/models.manifest).
TTS_VOICES = {"calm": "tts-calm.onnx", "bright": "tts-bright.onnx"}
_MD = re.compile(r"```.*?```", re.S)          # fenced code blocks
_INLINE = re.compile(r"[`*_#>|]")             # markdown punctuation
_URL = re.compile(r"https?://\S+")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")   # [text](url) -> text


def clean_for_speech(text: str) -> str:
    """Turn a markdown answer into something worth hearing: drop code blocks, markdown punctuation
    and raw URLs so the voice does not read '`', '*' or a long link aloud."""
    text = _MD.sub(" (code) ", text)
    text = _LINK.sub(r"\1", text)
    text = _URL.sub(" a link ", text)
    text = _INLINE.sub("", text)
    return " ".join(text.split()).strip()


def tts_model(voice: str, models_dir: str = MODELS_DIR) -> Optional[str]:
    """Path to the piper voice for a setting (calm/bright), or None when off/unknown/missing."""
    name = TTS_VOICES.get((voice or "off").lower())
    if not name:
        return None
    path = os.path.join(models_dir, name)
    return path if os.path.exists(path) else None


def _player() -> Optional[List[str]]:
    for cand in (["pw-play"], ["paplay"], ["aplay", "-q"]):
        if shutil.which(cand[0]):
            return cand
    return None


def say(text: str, voice: str = "calm", piper: Optional[str] = None, player: Optional[str] = None,
        models_dir: str = MODELS_DIR, on_state=None) -> bool:
    """Speak text on this device with piper. Returns False when voice is off or there is nothing to
    say; raises VoiceError when the voice is on but piper or the model is missing."""
    text = clean_for_speech(text or "")
    model = tts_model(voice, models_dir)
    if not text or voice == "off" or model is None and voice not in TTS_VOICES:
        return False
    if model is None:
        raise VoiceError(f"speech voice '{voice}' is not installed (model missing in {models_dir})")
    binary = piper or shutil.which("piper")
    if not binary or not os.path.exists(binary):
        raise VoiceError("text-to-speech is not installed (piper missing)")
    play = [player] if player else _player()
    if not play:
        raise VoiceError("no audio player (pw-play/paplay/aplay missing)")
    if on_state:
        on_state("speaking")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav = f.name
    try:
        synth = subprocess.run([binary, "-m", model, "-f", wav], input=text, text=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        if synth.returncode != 0 or not os.path.exists(wav):
            raise VoiceError("piper failed to synthesize speech")
        subprocess.run(play + [wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        return True
    except (OSError, subprocess.SubprocessError) as e:
        raise VoiceError(f"speech failed: {e}")
    finally:
        try:
            os.unlink(wav)
        except OSError:
            pass


# ----------------------------------------------------------------------------- direct commands
_COMMANDS = [
    (r"^(open|launch|start)( the| a)? terminal$", ("exec", "xfce4-terminal")),
    (r"^lock( the)?( screen| computer| session)?$", ("exec", "eternity-lock")),
    (r"^(open|show)( the)? settings$", ("exec", "eternity-settings")),
    (r"^(open|show)( the)? (monitor|system monitor|performance)$", ("exec", "eternity-monitor")),
    (r"^(open|show)( the)? (files|file manager|finder)$", ("exec", "eternity-find")),
    (r"^(volume|sound) up$|^louder$", ("exec", "wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ 5%+")),
    (r"^(volume|sound) down$|^quieter$", ("exec", "wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-")),
    (r"^(mute|unmute|toggle mute)$", ("exec", "wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle")),
    (r"^(take a )?screenshot$", ("exec", "grim ~/Pictures/screenshot-$(date +%Y%m%d-%H%M%S).png")),
    (r"^(go )?home$", ("exec", "eternity-shell --home")),
]


def intent(text: str) -> Optional[Tuple[str, str]]:
    """A direct command for a short, unambiguous phrase; None sends the text to the assistant."""
    t = re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()
    t = re.sub(r"^(please |hey eternity |eternity |ok eternity )+", "", t).strip()
    t = re.sub(r"( please)+$", "", t).strip()
    for pat, action in _COMMANDS:
        if re.match(pat, t):
            return action
    return None
