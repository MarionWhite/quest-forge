# Proximity voice chat

Positional voice chat in `com.questforge.content.voice`, with push-to-talk or open
mic. Built on the audio path the jukebox already proved, and reusing the same OpenAL
approach rather than a second engine.

## What talks to what

```
 mic  ->  VoiceCapture  ->  gate  ->  VoiceCodec  ->  PacketVoice  ->  VoiceServer
        (own thread, 20ms frames)                                     (proximity cut)
                                                                            |
   speakers  <-  VoiceStream  <-  VoicePlayback  <-  PacketVoiceFrame  <----+
              (one OpenAL source    (client tick,
               per speaker)          jitter buffer)
```

## The decisions, and why

**Audio is 24 kHz mono, IMA ADPCM, 243 bytes per 20 ms frame — 12 KB/s per speaker.**
Raw PCM would be 48 KB/s for no quality the transport can deliver; mu-law is half
that and audibly telephone-grade. Opus would beat both and exists as a pure-Java port,
but `mp3spi`/`vorbisspi` are declared in `build.gradle.kts` and are **not** in the
built jar — shading is unsolved in this build, so adding a dependency means solving
that first. ADPCM needs no dependency at all.

**Voice rides the normal Minecraft connection, not a side UDP socket.** No port to
open, no second listener to secure, and it inherits the server's existing whitelist
and auth for free. The cost is head-of-line blocking: a chunk-load stall delays voice
along with everything else, which is what the jitter buffer absorbs.

Those two choices reinforce each other. ADPCM's real weakness is that its predictor is
stateful, so on a lossy transport one dropped frame corrupts everything after it. On an
ordered, reliable one that cannot happen — and each frame carries its own 3-byte
predictor seed anyway, which `checkVoiceCodec` verifies by dropping a frame and
confirming the rest is bit-identical to a clean stream.

**The proximity cut is server-side.** `VoiceServer` only relays to players within
`VoiceFormat.MAX_RANGE` (40 blocks) in the same dimension. A modified client cannot
listen in from across the map because the audio never leaves the server. Clients fade
from full volume at 6 blocks to silence at 40, so the two constants must agree.

**Voice packets are handled on the netty thread, not queued to the server tick.** This
deliberately breaks the convention `ServerTasks` sets, and the reason is arithmetic:
that queue drains 64 tasks/tick = 1280/sec, while voice alone is 50 frames/sec per
speaker. Three people talking would eat a quarter of the budget and start dropping
other mods' work. It is safe here because the relay reads player positions — plain
fields — and writes nothing.

**Capture runs on its own thread.** `VoiceCapture.readFrame` blocks until the sound
card has produced exactly 20 ms, so the thread is paced by the audio clock. Driving it
from the 20 Hz client tick would send bursts every 50 ms and go silent entirely during
a lag spike — exactly when a conversation most needs to keep working.

**`VoiceStream` is `DirectAudio` made instanceable.** Same OpenAL approach, including
the two findings that were expensive to learn: PaulsCode cannot play buffers a mod
creates, and OpenAL's distance model is switched off so gain can be computed by hand
while position is used purely to steer direction. `DirectAudio` is static throughout,
which is right for one jukebox and impossible for several people talking at once.

**Push-to-talk is the default, and the mic is opened lazily.** A hot microphone nobody
opted into is a bad surprise for someone who just installed the pack. The device is not
opened until the talk key is first pressed, and is released after 60 s idle so the
operating system's in-use indicator goes out.

## Platforms

Written to be portable, and audited for it: nothing in the package calls native code,
loads a library, spawns a process, or hardcodes a path or separator. Capture is
`javax.sound.sampled` and playback is LWJGL OpenAL — both already load on every
platform Minecraft runs on, because the game itself depends on them.

Byte order is pinned rather than inherited. The capture format is requested as
`AudioFormat(rate, 16, 1, signed=true, bigEndian=false)`, the codec packs and unpacks
bytes by hand, and netty's `ByteBuf` is big-endian on both ends — so nothing changes
on a big-endian host or a different JVM.

Three things are genuinely different between macOS and Windows, and each is handled:

- **Sample rate.** Few devices offer 24 kHz directly. `VoiceCapture` tries 24000,
  48000, 44100 then 16000 and linearly resamples whatever it gets. The probe on this
  Mac offered 16 kHz and 44.1 kHz but not 24.
- **`isLineSupported` lies.** Windows DirectSound reports formats it then refuses to
  open — another application holding the device exclusively is enough. So a failure
  on one rate falls through to the next rate, and with no explicit device chosen, on
  to the next device, rather than aborting.
- **Silent-but-open microphones.** Windows can deny desktop apps the microphone
  (Privacy → Microphone → "Allow desktop apps to access your microphone") and macOS
  can withhold the TCC grant. Neither throws: the line opens, reads succeed, and every
  sample is zero. `VoiceClient` counts consecutive frames of *exact* digital silence
  and says so after three seconds, in the log and in `/voice`. Exact zero is the test
  because a working microphone always has a noise floor.

`build.gradle.kts` now pins `options.encoding = "UTF-8"`. Several sources contain the
section sign for Minecraft colour codes, and javac would otherwise read them in the
platform default — UTF-8 here, windows-1252 on Windows — so the same source would
build to different string constants depending on who ran it.

Only macOS is actually tested. Nothing above is a Windows *workaround* discovered by
running it there; they are known differences handled defensively.

## Latency budget

| stage | ms |
|---|---|
| capture frame | 20 |
| jitter prebuffer (4 frames) | 80 |
| client tick granularity | ~50 |
| **local total** | **~150** |
| network round trip | + server ping |

## Controls

`B` push to talk, `N` mute microphone, deafen unbound. All rebindable under
Controls -> QuestForge Voice.

`/voice` shows status; `mode ptt|open`, `devices`, `device <n>`, `level`,
`threshold <n>`, `volume <n>`, `mute <player>`, `on`, `off`.

Tune open mic with `/voice level` while speaking, then set `threshold` just below the
reading. The default 0.020 is deliberately low — RMS over 20 ms of ordinary speech
sits well under a tenth of full scale.

## Verified

- Microphone capture works under the exact JVM the pack uses (Oracle 8u162 x86_64),
  probed directly: peak 1716/32767 over 3 s. Devices seen were Default Audio Device,
  MacBook Pro Microphone, Teams and Zoom.
- `./gradlew checkVoiceCodec` — 35 dB SNR on speech-like input, exact silence in and
  out, and a dropped frame costs exactly that frame.
- `./gradlew build` passes with all four existing ASM transformer checks intact.

## NOT yet verified

- **Anything involving two players.** The whole network path — relay, proximity cut,
  jitter buffer, positional playback — has never been exercised with real audio
  between two clients. This is the big one.
- **macOS microphone permission under Prism.** The probe ran from a terminal that
  already holds mic permission; the responsible process for a Prism-launched JVM is
  different, so expect a one-time prompt and confirm it is actually granted.
- **Echo.** There is no acoustic echo cancellation and there will not be one without
  native code. Speakers feeding back into an open mic will loop. Headphones are
  effectively required, especially in open-mic mode.
- Whether 40 blocks and the 6-block full-volume radius feel right in play.

## Known separate bug

`mp3spi` and `vorbisspi` are declared as `implementation` dependencies but no shadow
plugin is configured, and the built jar contains no `javazoom`, `tritonus` or
`META-INF/services` entries. The jukebox's mp3/ogg playback will work in `runClient`
and fail in the pack — the trap the comment in `build.gradle.kts` predicted. Unrelated
to voice, but it is also what rules Opus out until it is fixed.
