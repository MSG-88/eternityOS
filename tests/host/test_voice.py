"""Voice input: silence-bounded capture, whisper.cpp transcription, direct voice commands.
Run: python3 -m unittest tests/host/test_voice.py"""
import array
import math
import os
import stat
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "config", "includes.chroot", "usr", "lib", "eternity", "py"))
os.environ["ETERNITY_NO_KEYRING"] = "1"

from eternity import voice as V  # noqa: E402


def pcm(seconds: float, amplitude: int, rate: int = V.RATE) -> bytes:
    """Mono 16-bit PCM: a 440 Hz tone at the given amplitude (0 = silence)."""
    n = int(seconds * rate)
    a = array.array("h", (int(amplitude * math.sin(2 * math.pi * 440 * i / rate)) for i in range(n)))
    return a.tobytes()


def frames(data: bytes, frame_bytes: int = V.FRAME_BYTES):
    for i in range(0, len(data), frame_bytes):
        yield data[i:i + frame_bytes]


class SegmentTest(unittest.TestCase):
    def test_capture_ends_after_silence_that_follows_speech(self):
        stream = pcm(0.3, 0) + pcm(1.0, 8000) + pcm(1.5, 0) + pcm(5.0, 8000)
        got = V.capture(frames(stream), max_s=10.0, silence_s=0.8)
        # the lead-in, the speech and the closing silence; never the second burst
        self.assertGreater(len(got), len(pcm(1.0, 8000)))
        self.assertLess(len(got), len(pcm(0.3, 0) + pcm(1.0, 8000) + pcm(1.5, 0)) + V.FRAME_BYTES)

    def test_capture_gives_up_when_nobody_speaks(self):
        self.assertEqual(V.capture(frames(pcm(6.0, 0)), max_s=10.0, silence_s=0.8, wait_s=3.0), b"")

    def test_capture_stops_at_max(self):
        got = V.capture(frames(pcm(20.0, 8000)), max_s=2.0, silence_s=0.8)
        self.assertLessEqual(len(got), len(pcm(2.0, 8000)) + V.FRAME_BYTES)

    def test_wav_file_is_16k_mono(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "a.wav")
            V.write_wav(p, pcm(0.5, 1000))
            import wave
            with wave.open(p) as w:
                self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate()), (1, 2, V.RATE))


class TranscribeTest(unittest.TestCase):
    def test_transcribe_returns_the_text_whisper_prints(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = os.path.join(tmp, "whisper-cli")
            with open(fake, "w") as f:
                f.write("#!/bin/sh\necho ' Open the terminal, please.'\necho ''\n")
            os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
            model = os.path.join(tmp, "stt.bin"); open(model, "wb").close()
            self.assertEqual(V.transcribe("/tmp/x.wav", binary=fake, model=model), "Open the terminal, please.")

    def test_transcribe_without_whisper_raises_not_installed(self):
        with self.assertRaises(V.VoiceError):
            V.transcribe("/tmp/x.wav", binary="/nonexistent/whisper-cli", model="/nonexistent/stt.bin")


class IntentTest(unittest.TestCase):
    def test_direct_commands_do_not_need_the_model(self):
        self.assertEqual(V.intent("Open the terminal."), ("exec", "xfce4-terminal"))
        self.assertEqual(V.intent("lock the screen"), ("exec", "eternity-lock"))
        self.assertEqual(V.intent("open settings"), ("exec", "eternity-settings"))
        self.assertEqual(V.intent("volume up"), ("exec", "wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ 5%+"))
        self.assertEqual(V.intent("mute"), ("exec", "wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"))
        self.assertEqual(V.intent("take a screenshot"), ("exec", "grim ~/Pictures/screenshot-$(date +%Y%m%d-%H%M%S).png"))

    def test_everything_else_is_a_question(self):
        self.assertIsNone(V.intent("how much disk space is left?"))
        self.assertIsNone(V.intent("open the terminal and list my files"))  # a compound request goes to the assistant


if __name__ == "__main__":
    unittest.main()
