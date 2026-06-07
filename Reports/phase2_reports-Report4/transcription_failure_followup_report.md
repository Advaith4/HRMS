# Transcription Failure Follow-Up Report

## Current Error Path

The UI message:

`Unable to transcribe audio. You can type your answer instead.`

is triggered in:

`frontend/src/components/interview/InterviewWorkspaceShell.jsx`

inside the `catch` block of the effect that runs after `audioBlob` is set. Any failed upload, backend 500, Whisper error, prompt-echo rejection, or response parsing error reaches that same toast.

## Most Likely Rejection Trigger Found In Code

After the prompt-echo fix, the transcription service still had a hard minimum-size gate:

`src/services/transcription_service.py`

`if file_size < MIN_AUDIO_BYTES: raise RuntimeError(...)`

That rejection happened before Whisper, so no transcript could be returned and the frontend showed the generic toast.

## Fix Applied For Investigation

Minimum-size validation is temporarily disabled as requested:

- Small files now log `transcription_small_file_continue`.
- The request continues to Whisper.
- `whisper_request_start` is logged before every provider call.
- Raw Whisper responses are logged via `transcription_raw_response`.

## Runtime Values

No live browser recording logs were available in this coding session, so I did not fabricate an actual runtime file size or duration. The next recording attempt will log the actual values at each stage:

- Frontend blob size and duration:
  - `audio_recording_stop`
  - `audio_transcription_state_before_upload`
  - `audio_transcription_upload_start`
- Backend received size and MIME type:
  - `transcription_request_received`
- Whisper boundary:
  - `whisper_request_start`
  - `transcription_raw_response`
- Rejections:
  - `transcription_rejected reason=prompt_echo`
  - `transcription_rejected reason=whisper_failure`

## Proposed Permanent Fix

Keep the prompt removed. Replace the old static byte threshold with a combined validation policy:

- Warn for small blobs, but do not reject solely by size.
- Reject only when both file size is extremely small and duration is near zero.
- Surface backend `detail` in the frontend toast during development.
- Keep prompt-echo rejection permanently.
