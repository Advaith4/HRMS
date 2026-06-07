Recorder Configuration Investigation Report

## Runtime Evidence

The latest browser recording logs showed:

- durationMs: 4426
- fileSizeBytes: 1307

A 4.4 second recording producing only 1.3KB is not a valid speech payload. Backend upload, backend validation, and Whisper are no longer the primary suspect for this failure path. The recorder is creating a near-empty blob before upload.

## Change Applied

`frontend/src/hooks/useRecorder.js` now uses browser-default MediaRecorder configuration:

`new MediaRecorder(stream)`

The previous forced configuration has been disabled:

- mimeType: `audio/webm;codecs=opus`
- audioBitsPerSecond: `128000`

Those previous values are still logged as comparison context under `audio_recorder_config_selected`, but they are no longer passed to the browser.

## New Runtime Logs

The next recording attempt will log:

- `audio_recorder_support_matrix`
  - `audio/webm`
  - `audio/webm;codecs=opus`
  - `audio/mp4`
  - `audio/ogg`
- `audio_recording_microphone_ready`
  - track settings
  - enabled
  - muted
  - readyState
- `audio_signal_sample`
  - RMS samples from the live microphone stream
  - max RMS
  - average RMS
- `audio_recorder_config_selected`
  - browser-default mode
  - actual recorder MIME type
  - actual recorder bitrate if exposed by the browser
  - previous forced config for comparison
- `audio_recording_chunk`
  - chunk size
  - chunk type
  - chunk index
- `audio_recording_stop`
  - final blob size
  - duration
  - MIME type
  - final track state
  - signal stats
  - `sizeLooksRealistic`
- `audio_recording_suspiciously_small_blob`
  - emitted when a recording is at least 3 seconds but remains under 20KB

## Verification Criteria

For a 4-5 second recording, the default recorder path should produce at least tens of KB:

- suspicious: less than 20KB
- expected: 20KB-100KB+

If the next default-recorder run produces realistic blob sizes, the permanent fix is to keep browser defaults and remove the forced recorder configuration permanently.

If the next run still produces a tiny blob but `audio_signal_sample.maxRms` is greater than zero, the issue is likely MediaRecorder output/codec behavior in that browser.

If the next run still produces a tiny blob and `audio_signal_sample.maxRms` remains near zero, the issue is microphone signal capture, muted input, device selection, or track state rather than Whisper or upload.
