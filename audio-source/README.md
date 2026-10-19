# Original sampled sound effects

The RH-93 7.02 firmware contains a RIFF/DLS bank at 0x01339c40. `assets/audio/original-rh93.dls` is that complete original bank (SHA256 4b7996245d608aca6e959e39e3691827ec64a2c38ce9ff28282253cc5cdce261).

The game's original table at 0xdd70 selects **note, instrument, duration**. Its native eight-parameter calls select program 120 (CRASH/Fret Noise), 12 (VIBAs4/Marimba), and 55 (ORCHC5D/Orchestra Hit). They are sampled instruments, not plain pitched oscillators or pitch sweeps.

The existing [Nokia 1110 SF2 conversion](https://www.anapan.ca/Anapan/FM/Full%20GM%20Soundfonts/Nokia%201110.sf2) supplies the SF2 region/envelope layout. `build_bank.py` replaces its used sample regions with the actual signed 8-bit PCM extracted from the original RH-93 DLS. The original reference SHA256 is ff75af29f5a26fd1a0559b8b9aaf57d256f9294c5487b5cdaae5b4e020f1097a. The resulting bank is `assets/audio/nokia-rh93.sf2`. Reapplying the extraction to that bank is idempotent; no new download is required.

[TinySoundFont](https://github.com/schellingb/TinySoundFont) is MIT-licensed; its header and license are included. It renders the five unique effect profiles offline. This avoids real-time synthesis CPU load. The application plays signed little-endian mono 16-bit PCM at 22050 Hz.

Rebuild from this game directory:

```sh
python audio-source/build_bank.py assets/audio/nokia-rh93.sf2
cc -O2 -std=c99 -I audio-source audio-source/render_effect.c -lm -o /tmp/render-nokia-effect
python audio-source/render_all.py /tmp/render-nokia-effect
```

The original game chooses when effects occur. Note-off timing and natural release are preserved; a new monophonic effect can interrupt an earlier one. Phone DSP/filter/speaker response is not claimed to be exactly emulated. Original Nokia bank/sample data is retained locally for personal use, not published as an open-source sound pack.
