"""Tests for audio converters and provider utilities."""

import struct
import unittest

from agents_voice.providers import _is_mp3, pcm_to_wav


class TestProviders(unittest.TestCase):
    def test_pcm_to_wav(self):
        # 100 samples of 16-bit silence (200 bytes)
        raw_pcm = b"\x00\x00" * 100
        wav = pcm_to_wav(raw_pcm, sample_rate=24000, channels=1, bits_per_sample=16)

        self.assertEqual(len(wav), 44 + 200)
        self.assertEqual(wav[:4], b"RIFF")
        self.assertEqual(wav[8:12], b"WAVE")
        self.assertEqual(wav[12:16], b"fmt ")
        self.assertEqual(wav[36:40], b"data")

        # Check sample rate in header
        sr = struct.unpack("<I", wav[24:28])[0]
        self.assertEqual(sr, 24000)

        # Check data length
        data_len = struct.unpack("<I", wav[40:44])[0]
        self.assertEqual(data_len, 200)

    def test_is_mp3_id3(self):
        id3_data = b"ID3\x03\x00\x00\x00\x00\x00\x00"
        self.assertTrue(_is_mp3(id3_data))

    def test_is_mp3_sync(self):
        mp3_sync = b"\xff\xfb\x90\x00"
        self.assertTrue(_is_mp3(mp3_sync))

    def test_is_not_mp3(self):
        riff = b"RIFF$\x00\x00\x00WAVE"
        self.assertFalse(_is_mp3(riff))
        self.assertFalse(_is_mp3(b""))


if __name__ == "__main__":
    unittest.main()
