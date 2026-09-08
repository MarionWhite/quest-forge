// qfcapture.exe -- Windows audio capture for the QuestForge jukebox.
//
// Captures what another application is playing and writes it to stdout as raw PCM,
// so the mod can feed it into OpenAL and play it from a block in the world.
//
// Needs NO driver installed and triggers NO permission prompt -- WASAPI loopback is
// built into Windows. This is the easy platform; macOS is the awkward one.
//
// Two capture modes:
//
//   --pid <n>   Process loopback: capture ONLY that process and its children.
//               Requires Windows 10 build 20348 / Windows 11. This is the mode to
//               use. Because Minecraft is not in the target process tree, feeding
//               its own output back in is structurally impossible rather than
//               merely avoided, and Windows notification sounds stay out too.
//
//   (default)   Endpoint loopback on the default output device. Works on anything
//               since Vista, but captures EVERYTHING the machine plays -- including
//               Minecraft playing this very audio back, which is a feedback loop.
//               Only sane if the game is muted. Present as a fallback, not a plan.
//
// stdout: "QFPCM1", Int32LE sample rate, Int32LE channels(=1), then Int16LE mono.
// stderr: human-readable status. Never mix the two.
//
// Output is mono because OpenAL only spatialises mono sources; a stereo source
// plays flat in both ears with no position at all.
//
// Build (MSVC):  cl /O2 /EHsc qfcapture.cpp ole32.lib mmdevapi.lib
// Build (mingw): x86_64-w64-mingw32-g++ -O2 -o qfcapture.exe qfcapture.cpp -lole32 -lmmdevapi -static

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <initguid.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <mmreg.h>

// mingw-w64 has ActivateAudioInterfaceAsync and both COM interfaces in
// mmdeviceapi.h, but not <audioclientactivationparams.h>, which is Windows-SDK
// only. That header contributes nothing but a constant, two enums and a struct,
// so declare them when it is absent. Layout matches the documented ABI; MSVC
// builds pick up the real header instead and are unaffected.
#if defined(__has_include)
#  if __has_include(<audioclientactivationparams.h>)
#    include <audioclientactivationparams.h>
#    define QF_HAVE_ACTIVATION_HEADER 1
#  endif
#endif

#ifndef QF_HAVE_ACTIVATION_HEADER
#define VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK L"VAD\\Process_Loopback"

typedef enum {
    PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE = 0,
    PROCESS_LOOPBACK_MODE_EXCLUDE_TARGET_PROCESS_TREE = 1
} PROCESS_LOOPBACK_MODE;

typedef struct {
    DWORD                 TargetProcessId;
    PROCESS_LOOPBACK_MODE ProcessLoopbackMode;
} AUDIOCLIENT_PROCESS_LOOPBACK_PARAMS;

typedef enum {
    AUDIOCLIENT_ACTIVATION_TYPE_DEFAULT          = 0,
    AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK = 1
} AUDIOCLIENT_ACTIVATION_TYPE;

typedef struct {
    AUDIOCLIENT_ACTIVATION_TYPE ActivationType;
    union {
        AUDIOCLIENT_PROCESS_LOOPBACK_PARAMS ProcessLoopbackParams;
    };
} AUDIOCLIENT_ACTIVATION_PARAMS;
#endif

#ifndef AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY
#define AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY 0x08000000
#endif

#include <io.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string>
#include <vector>

// ---------------------------------------------------------------- utilities

static void note(const char* fmt, ...) {
    va_list args;
    va_start(args, fmt);
    vfprintf(stderr, fmt, args);
    va_end(args);
    fprintf(stderr, "\n");
    fflush(stderr);
}

static int fail(const char* what, HRESULT hr) {
    note("ERROR: %s failed: 0x%08lX", what, (unsigned long)hr);
    return 1;
}

/// Raw write to fd 1. Returns false when the mod closes the pipe, which is normal.
static bool writeOut(const void* data, size_t bytes) {
    const char* p = (const char*)data;
    size_t off = 0;
    while (off < bytes) {
        int n = _write(1, p + off, (unsigned)(bytes - off));
        if (n <= 0) return false;
        off += (size_t)n;
    }
    return true;
}

static void writeHeader(int rate) {
    writeOut("QFPCM1", 6);
    int r = rate, c = 1;                 // x86 is little-endian, matching the format
    writeOut(&r, 4);
    writeOut(&c, 4);
}

// ---------------------------------------------------------------- state

static bool  g_selfTest = false;
static bool  g_toneMode = false;
static DWORD g_targetPid = 0;
static double g_testSeconds = 3.0;
static long long g_frames = 0;
static float g_peak = 0.0f;

// -------------------------------------------------- async activation handler

// ActivateAudioInterfaceAsync is the only route to process loopback, and it insists
// on a COM completion handler even though we immediately block on it.
class ActivationHandler : public IActivateAudioInterfaceCompletionHandler,
                          public IAgileObject {
public:
    HANDLE done = CreateEventW(nullptr, TRUE, FALSE, nullptr);
    HRESULT result = E_FAIL;
    IAudioClient* client = nullptr;

    STDMETHOD(QueryInterface)(REFIID riid, void** ppv) override {
        if (riid == __uuidof(IUnknown) ||
            riid == __uuidof(IActivateAudioInterfaceCompletionHandler) ||
            riid == __uuidof(IAgileObject)) {
            *ppv = static_cast<IActivateAudioInterfaceCompletionHandler*>(this);
            return S_OK;
        }
        *ppv = nullptr;
        return E_NOINTERFACE;
    }
    // Lifetime is the whole program; refcounting it properly buys nothing here.
    STDMETHOD_(ULONG, AddRef)() override { return 1; }
    STDMETHOD_(ULONG, Release)() override { return 1; }

    STDMETHOD(ActivateCompleted)(IActivateAudioInterfaceAsyncOperation* op) override {
        IUnknown* unk = nullptr;
        HRESULT hr = op->GetActivateResult(&result, &unk);
        if (SUCCEEDED(hr) && SUCCEEDED(result) && unk) {
            unk->QueryInterface(__uuidof(IAudioClient), (void**)&client);
            unk->Release();
        }
        SetEvent(done);
        return S_OK;
    }
};

// ---------------------------------------------------------------- capture

static int capture() {
    HRESULT hr = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    if (FAILED(hr)) return fail("CoInitializeEx", hr);

    IAudioClient* client = nullptr;

    // The format we ask Windows for. Loopback will convert to this for us, so the
    // only work left here is the stereo-to-mono mixdown.
    WAVEFORMATEX wf = {};
    wf.wFormatTag      = WAVE_FORMAT_PCM;
    wf.nChannels       = 2;
    wf.nSamplesPerSec  = 48000;
    wf.wBitsPerSample  = 16;
    wf.nBlockAlign     = wf.nChannels * wf.wBitsPerSample / 8;
    wf.nAvgBytesPerSec = wf.nSamplesPerSec * wf.nBlockAlign;

    if (g_targetPid != 0) {
        note("process loopback: capturing pid %lu and its children", (unsigned long)g_targetPid);

        AUDIOCLIENT_ACTIVATION_PARAMS params = {};
        params.ActivationType = AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK;
        params.ProcessLoopbackParams.TargetProcessId = g_targetPid;
        params.ProcessLoopbackParams.ProcessLoopbackMode =
            PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE;

        PROPVARIANT pv = {};
        pv.vt = VT_BLOB;
        pv.blob.cbSize = sizeof(params);
        pv.blob.pBlobData = (BYTE*)&params;

        ActivationHandler handler;
        IActivateAudioInterfaceAsyncOperation* op = nullptr;
        hr = ActivateAudioInterfaceAsync(VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK,
                                         __uuidof(IAudioClient), &pv, &handler, &op);
        if (FAILED(hr)) return fail("ActivateAudioInterfaceAsync", hr);

        WaitForSingleObject(handler.done, 5000);
        if (op) op->Release();
        if (FAILED(handler.result) || !handler.client) {
            note("process loopback unavailable (0x%08lX).", (unsigned long)handler.result);
            note("Needs Windows 10 build 20348 or Windows 11. Retry without --pid to");
            note("use endpoint loopback, but mute Minecraft first or it will feed back.");
            return 1;
        }
        client = handler.client;

        // Process loopback MUST be initialised with these flags together.
        hr = client->Initialize(AUDCLNT_SHAREMODE_SHARED,
                                AUDCLNT_STREAMFLAGS_LOOPBACK |
                                AUDCLNT_STREAMFLAGS_AUTOCONVERTPCM |
                                AUDCLNT_STREAMFLAGS_SRC_DEFAULT_QUALITY,
                                20 * 10000, 0, &wf, nullptr);
        if (FAILED(hr)) return fail("Initialize (process loopback)", hr);

    } else {
        note("endpoint loopback: capturing ALL system audio");
        note("WARNING: this includes Minecraft's own playback. Mute the game or");
        note("         use --pid <spotify pid> instead.");

        IMMDeviceEnumerator* enumerator = nullptr;
        hr = CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
                              __uuidof(IMMDeviceEnumerator), (void**)&enumerator);
        if (FAILED(hr)) return fail("CoCreateInstance(MMDeviceEnumerator)", hr);

        IMMDevice* device = nullptr;
        hr = enumerator->GetDefaultAudioEndpoint(eRender, eConsole, &device);
        if (FAILED(hr)) return fail("GetDefaultAudioEndpoint", hr);

        hr = device->Activate(__uuidof(IAudioClient), CLSCTX_ALL, nullptr, (void**)&client);
        if (FAILED(hr)) return fail("Activate(IAudioClient)", hr);

        // The endpoint dictates its own mix format; asking for ours would fail.
        WAVEFORMATEX* mix = nullptr;
        hr = client->GetMixFormat(&mix);
        if (FAILED(hr)) return fail("GetMixFormat", hr);

        hr = client->Initialize(AUDCLNT_SHAREMODE_SHARED, AUDCLNT_STREAMFLAGS_LOOPBACK,
                                20 * 10000, 0, mix, nullptr);
        if (FAILED(hr)) return fail("Initialize (endpoint loopback)", hr);

        wf = *mix;                       // remember what we actually got
        CoTaskMemFree(mix);
        device->Release();
        enumerator->Release();
    }

    IAudioCaptureClient* capture = nullptr;
    hr = client->GetService(__uuidof(IAudioCaptureClient), (void**)&capture);
    if (FAILED(hr)) return fail("GetService(IAudioCaptureClient)", hr);

    const int    channels   = wf.nChannels;
    const int    rate       = (int)wf.nSamplesPerSec;
    const bool   isFloat    = (wf.wFormatTag == WAVE_FORMAT_IEEE_FLOAT) ||
                              (wf.wFormatTag == WAVE_FORMAT_EXTENSIBLE && wf.wBitsPerSample == 32);
    note("format: %d Hz, %d ch, %d bit%s", rate, channels, wf.wBitsPerSample,
         isFloat ? " float" : "");

    if (!g_selfTest) writeHeader(rate);

    hr = client->Start();
    if (FAILED(hr)) return fail("Start", hr);
    note("capturing...");

    const DWORD startTick = GetTickCount();
    std::vector<short> mono;

    for (;;) {
        UINT32 packet = 0;
        hr = capture->GetNextPacketSize(&packet);
        if (FAILED(hr)) break;

        if (packet == 0) {
            Sleep(5);                    // nothing ready; do not spin a core
            if (g_selfTest && GetTickCount() - startTick > g_testSeconds * 1000) break;
            continue;
        }

        while (packet > 0) {
            BYTE* data = nullptr;
            UINT32 frames = 0;
            DWORD flags = 0;
            hr = capture->GetBuffer(&data, &frames, &flags, nullptr, nullptr);
            if (FAILED(hr)) break;

            mono.clear();
            mono.reserve(frames);

            const bool silent = (flags & AUDCLNT_BUFFERFLAGS_SILENT) != 0;
            for (UINT32 f = 0; f < frames; f++) {
                float sum = 0.0f;
                if (!silent) {
                    for (int c = 0; c < channels; c++) {
                        if (isFloat) {
                            sum += ((const float*)data)[f * channels + c];
                        } else {
                            sum += ((const short*)data)[f * channels + c] / 32768.0f;
                        }
                    }
                    sum /= (float)channels;
                }
                if (fabsf(sum) > g_peak) g_peak = fabsf(sum);
                if (sum >  1.0f) sum =  1.0f;    // captured audio can exceed unity
                if (sum < -1.0f) sum = -1.0f;
                mono.push_back((short)(sum * 32767.0f));
            }

            g_frames += frames;
            if (!g_selfTest && !mono.empty()) {
                if (!writeOut(mono.data(), mono.size() * sizeof(short))) {
                    note("pipe closed");
                    goto done;
                }
            }

            capture->ReleaseBuffer(frames);
            hr = capture->GetNextPacketSize(&packet);
            if (FAILED(hr)) break;
        }

        if (g_selfTest && GetTickCount() - startTick > g_testSeconds * 1000) break;
    }

done:
    client->Stop();
    if (capture) capture->Release();
    if (client) client->Release();
    CoUninitialize();

    if (g_selfTest) {
        double seconds = rate > 0 ? (double)g_frames / rate : 0.0;
        note("captured %.2fs, %lld frames, peak amplitude %.4f", seconds, g_frames, g_peak);
        if (g_peak < 0.0001f) {
            note("RESULT: SILENCE -- ran fine but captured nothing. Is the target playing?");
            return 2;
        }
        note("RESULT: OK -- real audio captured.");
    }
    return 0;
}

// ---------------------------------------------------------------- tone mode

static int tone() {
    const int rate = 44100;
    writeHeader(rate);
    note("tone mode: 440 Hz, %d Hz mono -- no capture, pipe test only", rate);

    double phase = 0.0;
    const double inc = 2.0 * 3.14159265358979 * 440.0 / rate;
    const int chunkFrames = 4410;                 // 100 ms
    std::vector<short> chunk(chunkFrames);

    for (;;) {
        for (int i = 0; i < chunkFrames; i++) {
            phase += inc;
            if (phase > 2 * 3.14159265358979) phase -= 2 * 3.14159265358979;
            chunk[i] = (short)(sin(phase) * 9000);
        }
        if (!writeOut(chunk.data(), chunk.size() * sizeof(short))) {
            note("pipe closed");
            return 0;
        }
        Sleep(90);                                 // just ahead of real time
    }
}

// ---------------------------------------------------------------- main

int main(int argc, char** argv) {
    // Without this, Windows mangles \n into \r\n and corrupts every audio buffer.
    _setmode(1, _O_BINARY);

    for (int i = 1; i < argc; i++) {
        std::string a = argv[i];
        if (a == "--pid" && i + 1 < argc)          g_targetPid = (DWORD)atoi(argv[++i]);
        else if (a == "--selftest")                g_selfTest = true;
        else if (a == "--tone")                    g_toneMode = true;
        else if (a == "--seconds" && i + 1 < argc) g_testSeconds = atof(argv[++i]);
        else if (a == "--help" || a == "-h") {
            note("qfcapture [--pid <n>] [--selftest] [--tone] [--seconds N]");
            note("  --pid       capture only this process and its children (preferred)");
            note("  (no --pid)  capture all system audio -- will feed back if the game is unmuted");
            note("  --selftest  capture briefly and report signal level instead of writing PCM");
            note("  --tone      emit a generated tone, to test the pipe without capturing");
            return 0;
        }
        else note("ignoring unknown argument: %s", argv[i]);
    }

    return g_toneMode ? tone() : capture();
}
