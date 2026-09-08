// qfcapture -- macOS system audio capture for the QuestForge jukebox.
//
// Captures audio that other applications are playing and writes it to stdout as
// raw PCM, so the mod can feed it into OpenAL and play it from a block in the world.
//
// Uses Core Audio process taps (macOS 14.2+). This matters: it needs NO virtual
// audio driver installed -- no BlackHole, no Soundflower -- because the tap reads
// from the process itself rather than from a fake output device.
//
// Two capture shapes:
//   --exclude <pid>   everything the machine plays EXCEPT that process
//   --include <pid>   only that process (target Spotify, ignore notifications)
//
// The exclude form exists for a specific reason: Minecraft is itself playing the
// captured audio back, so capturing globally without excluding it is a feedback loop.
//
// Output is mono on purpose. OpenAL only spatialises mono sources -- a stereo source
// plays flat in both ears with no position at all -- so the mixdown happens here
// rather than costing the game thread work every buffer.
//
// stdout: "QFPCM1" magic, then Int32LE sample rate, Int32LE channels(=1),
//         then continuous Int16LE mono samples.
// stderr: human-readable status. Never mix the two.
//
// Build: swiftc -O -o qfcapture qfcapture.swift

import Foundation
import CoreAudio
import AudioToolbox

// ---------------------------------------------------------------- utilities

func note(_ s: String) {
    FileHandle.standardError.write((s + "\n").data(using: .utf8)!)
}

func fail(_ s: String) -> Never {
    note("ERROR: " + s)
    exit(1)
}

func check(_ status: OSStatus, _ what: String) {
    if status != noErr {
        // Core Audio codes are usually four-char strings; show both readings.
        let bytes = withUnsafeBytes(of: status.bigEndian) { Array($0) }
        let chars = String(bytes.map { b -> Character in
            (b >= 32 && b < 127) ? Character(UnicodeScalar(b)) : "."
        })
        fail("\(what) failed: \(status) '\(chars)'")
    }
}

// ---------------------------------------------------------------- arguments

var includePIDs: [pid_t] = []
var excludePIDs: [pid_t] = []
var selfTest = false
var toneMode = false
var testSeconds = 3.0

var i = 1
let argv = CommandLine.arguments
while i < argv.count {
    switch argv[i] {
    case "--include":
        i += 1
        if i < argv.count, let p = pid_t(argv[i]) { includePIDs.append(p) }
    case "--exclude":
        i += 1
        if i < argv.count, let p = pid_t(argv[i]) { excludePIDs.append(p) }
    case "--selftest":
        selfTest = true
    case "--tone":
        // Emits a generated tone in the exact wire format instead of capturing.
        // Lets the whole pipe -- process launch, header, streaming, shutdown -- be
        // verified end to end without depending on capture permissions at all.
        toneMode = true
    case "--seconds":
        i += 1
        if i < argv.count, let s = Double(argv[i]) { testSeconds = s }
    case "--help", "-h":
        note("""
        qfcapture [--include <pid>] [--exclude <pid>] [--selftest] [--seconds N]
          --include  capture only these processes
          --exclude  capture everything except these processes
          --selftest capture briefly and report signal level instead of writing PCM
        """)
        exit(0)
    default:
        note("ignoring unknown argument: \(argv[i])")
    }
    i += 1
}

// ---------------------------------------------------------------- writing

/// Raw write(2) rather than FileHandle: when the mod closes the pipe, FileHandle
/// raises an exception that kills the process untidily, whereas this just reports
/// the broken pipe and lets us shut down cleanly.
@discardableResult
func writeOut(_ d: Data) -> Bool {
    return d.withUnsafeBytes { raw -> Bool in
        guard let base = raw.baseAddress else { return true }
        var off = 0
        while off < d.count {
            let n = write(1, base.advanced(by: off), d.count - off)
            if n <= 0 { return false }
            off += n
        }
        return true
    }
}

func writeHeader(rate: Int32) {
    var header = Data("QFPCM1".utf8)
    var r = rate.littleEndian
    var c = Int32(1).littleEndian
    withUnsafeBytes(of: &r) { header.append(contentsOf: $0) }
    withUnsafeBytes(of: &c) { header.append(contentsOf: $0) }
    writeOut(header)
}

// ---------------------------------------------------------------- tone mode

if toneMode {
    signal(SIGPIPE, SIG_IGN)
    let rate: Int32 = 44100
    writeHeader(rate: rate)
    note("tone mode: 440 Hz, \(rate) Hz mono -- no capture, pipe test only")

    var phase = 0.0
    let inc = 2.0 * Double.pi * 440.0 / Double(rate)
    let chunkFrames = 4410                       // 100 ms

    while true {
        var chunk = Data(capacity: chunkFrames * 2)
        for _ in 0..<chunkFrames {
            phase += inc
            if phase > 2 * Double.pi { phase -= 2 * Double.pi }
            var s = Int16(sin(phase) * 9000).littleEndian
            withUnsafeBytes(of: &s) { chunk.append(contentsOf: $0) }
        }
        if !writeOut(chunk) { note("pipe closed"); exit(0) }
        Thread.sleep(forTimeInterval: 0.09)      // just ahead of real time
    }
}

// ---------------------------------------------------------------- the tap

// A mono mixdown, so no downmixing is needed downstream.
let tapDescription: CATapDescription
if !includePIDs.isEmpty {
    let objs = includePIDs.map { pidToAudioObject($0) }.filter { $0 != 0 }
    if objs.isEmpty { fail("none of the --include pids have audio objects (are they playing?)") }
    tapDescription = CATapDescription(monoMixdownOfProcesses: objs)
    note("capturing only pids \(includePIDs)")
} else {
    let objs = excludePIDs.map { pidToAudioObject($0) }.filter { $0 != 0 }
    tapDescription = CATapDescription(monoGlobalTapButExcludeProcesses: objs)
    note("capturing all system audio, excluding pids \(excludePIDs)")
}
tapDescription.uuid = UUID()
tapDescription.isPrivate = true
tapDescription.muteBehavior = .unmuted     // let the user still hear it normally

/// Core Audio addresses processes by AudioObjectID, not pid, so translate.
func pidToAudioObject(_ pid: pid_t) -> AudioObjectID {
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyTranslatePIDToProcessObject,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain)
    var inPid = pid
    var object = AudioObjectID(0)
    var size = UInt32(MemoryLayout<AudioObjectID>.size)
    let status = AudioObjectGetPropertyData(
        AudioObjectID(kAudioObjectSystemObject), &address,
        UInt32(MemoryLayout<pid_t>.size), &inPid, &size, &object)
    if status != noErr { note("warning: could not resolve pid \(pid) (\(status))") }
    return object
}

var tapID = AudioObjectID(kAudioObjectUnknown)
check(AudioHardwareCreateProcessTap(tapDescription, &tapID), "AudioHardwareCreateProcessTap")
note("tap created: \(tapID)")

// ------------------------------------------------- aggregate device wrapping it

// A tap is not readable on its own; it has to be a sub-object of an aggregate
// device, which is what actually delivers callbacks.
/// The system's current output device -- the thing actually playing audio.
func defaultOutputDevice() -> AudioObjectID {
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDefaultOutputDevice,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain)
    var device = AudioObjectID(0)
    var size = UInt32(MemoryLayout<AudioObjectID>.size)
    check(AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject),
                                     &address, 0, nil, &size, &device),
          "get default output device")
    return device
}

func deviceUID(_ device: AudioObjectID) -> String {
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyDeviceUID,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain)
    var uid: CFString = "" as CFString
    var size = UInt32(MemoryLayout<CFString>.size)
    check(AudioObjectGetPropertyData(device, &address, 0, nil, &size, &uid), "get device UID")
    return uid as String
}

let outputDevice = defaultOutputDevice()
let outputUID = deviceUID(outputDevice)
note("output device: \(outputDevice) \(outputUID)")

// The aggregate needs the real output device as a sub-device, and as its main one.
// A tap on its own has no clock: without this the IOProc still fires at the right
// rate but every buffer comes back empty, which looks exactly like a permissions
// problem and is not one.
let aggregateUID = UUID().uuidString
let aggregateDescription: [String: Any] = [
    kAudioAggregateDeviceNameKey as String: "QuestForge Capture",
    kAudioAggregateDeviceUIDKey as String: aggregateUID,
    kAudioAggregateDeviceIsPrivateKey as String: true,
    kAudioAggregateDeviceIsStackedKey as String: false,
    kAudioAggregateDeviceTapAutoStartKey as String: true,
    kAudioAggregateDeviceMainSubDeviceKey as String: outputUID,
    kAudioAggregateDeviceSubDeviceListKey as String: [
        [ kAudioSubDeviceUIDKey as String: outputUID ]
    ],
    kAudioAggregateDeviceTapListKey as String: [
        [ kAudioSubTapUIDKey as String: tapDescription.uuid.uuidString,
          kAudioSubTapDriftCompensationKey as String: true ]
    ]
]

var aggregateID = AudioObjectID(kAudioObjectUnknown)
check(AudioHardwareCreateAggregateDevice(aggregateDescription as CFDictionary, &aggregateID),
      "AudioHardwareCreateAggregateDevice")
note("aggregate device: \(aggregateID)")

// ---------------------------------------------------------------- input format

func inputFormat(_ device: AudioObjectID) -> AudioStreamBasicDescription {
    var address = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyStreamFormat,
        mScope: kAudioObjectPropertyScopeInput,
        mElement: kAudioObjectPropertyElementMain)
    var asbd = AudioStreamBasicDescription()
    var size = UInt32(MemoryLayout<AudioStreamBasicDescription>.size)
    check(AudioObjectGetPropertyData(device, &address, 0, nil, &size, &asbd),
          "get stream format")
    return asbd
}

let format = inputFormat(aggregateID)
let sampleRate = Int32(format.mSampleRate)
let srcChannels = Int(format.mChannelsPerFrame)
note("tap format: \(sampleRate) Hz, \(srcChannels) ch, flags \(format.mFormatFlags)")
if sampleRate <= 0 { fail("tap reported no sample rate; is anything playing?") }

// ---------------------------------------------------------------- output

let out = FileHandle.standardOutput
var frameCount = 0
var peak: Float = 0

if !selfTest {
    writeHeader(rate: sampleRate)
}

// Core Audio hands us deinterleaved Float32 buffers. Mix to one channel and
// convert to Int16, which is what OpenAL wants and half the bytes to pipe.
let ioBlock: AudioDeviceIOBlock = { _, inputData, _, _, _ in
    let buffers = UnsafeMutableAudioBufferListPointer(UnsafeMutablePointer(mutating: inputData))
    guard buffers.count > 0 else { return }

    let framesPerBuffer = Int(buffers[0].mDataByteSize) / MemoryLayout<Float>.size
    if framesPerBuffer == 0 { return }

    var pcm = Data(capacity: framesPerBuffer * 2)
    var localPeak: Float = 0

    for frame in 0..<framesPerBuffer {
        var sum: Float = 0
        var contributing = 0
        for buffer in buffers {
            guard let raw = buffer.mData else { continue }
            let samples = raw.assumingMemoryBound(to: Float.self)
            let count = Int(buffer.mDataByteSize) / MemoryLayout<Float>.size
            if frame < count {
                sum += samples[frame]
                contributing += 1
            }
        }
        let mono = contributing > 0 ? sum / Float(contributing) : 0
        if abs(mono) > localPeak { localPeak = abs(mono) }

        // Clamp before scaling: captured audio can exceed 1.0 and wrap otherwise.
        let clamped = max(-1.0, min(1.0, mono))
        var s = Int16(clamped * 32767.0).littleEndian
        withUnsafeBytes(of: &s) { pcm.append(contentsOf: $0) }
    }

    frameCount += framesPerBuffer
    if localPeak > peak { peak = localPeak }

    if !selfTest {
        writeOut(pcm)
    }
}

var procID: AudioDeviceIOProcID?
check(AudioDeviceCreateIOProcIDWithBlock(&procID, aggregateID, nil, ioBlock),
      "AudioDeviceCreateIOProcIDWithBlock")
check(AudioDeviceStart(aggregateID, procID), "AudioDeviceStart")
note("capturing...")

// ---------------------------------------------------------------- shutdown

func teardown() {
    if let procID = procID {
        AudioDeviceStop(aggregateID, procID)
        AudioDeviceDestroyIOProcID(aggregateID, procID)
    }
    AudioHardwareDestroyAggregateDevice(aggregateID)
    AudioHardwareDestroyProcessTap(tapID)
}

signal(SIGINT)  { _ in teardown(); exit(0) }
signal(SIGTERM) { _ in teardown(); exit(0) }
signal(SIGPIPE, SIG_IGN)      // the mod closing the pipe is normal, not fatal

if selfTest {
    Thread.sleep(forTimeInterval: testSeconds)
    teardown()
    let seconds = Double(frameCount) / Double(sampleRate)
    note(String(format: "captured %.2fs, %d frames, peak amplitude %.4f",
                seconds, frameCount, peak))
    if peak < 0.0001 {
        note("RESULT: SILENCE -- the tap ran but captured nothing. Play audio and retry.")
        exit(2)
    }
    note("RESULT: OK -- real audio captured.")
    exit(0)
}

// Stream until the parent goes away.
RunLoop.current.run()
