# Transcription Root-Cause Report

## Symptom

Spoken audio such as `I am Advaith` could return unrelated text:

`Avoid hallucinations and noise`

## Trace Findings

Microphone and MediaRecorder were producing blobs, but the backend transcription service sent this prompt to Whisper:

`Candidate answer to interview question. Avoid hallucinations and noise.`

The exact incorrect transcript text existed only in `src/services/transcription_service.py` as part of that prompt. There is no frontend hardcoded fallback transcript with that value, and the axios cache only applies to GET requests, not the POST transcription endpoint.

## Root Cause

For silent, tiny, corrupt, or low-signal audio, the model could echo part of the prompt. The service then accepted the echoed prompt as valid speech and returned it to React as `transcript`.

This is why the transcript was unrelated to the spoken audio and matched prompt text exactly.

## Fix Implemented

- Removed the Whisper prompt from the transcription request.
- Added backend rejection for tiny audio files before calling transcription.
- Added prompt-echo detection so known prompt fragments cannot reach the UI.
- Added raw transcription response logging.
- Added cache-key logging with explicit `cache_hit=false` for transcription POSTs.
- Added frontend logs for recording reset, chunks, blob identity, blob size, duration, upload start/end, and React transcript state updates.
- Added axios GET cache hit/store logs to prove transcription is not served from that cache layer.

## Verification Notes

After the fix, the exact phrase remains only as a defensive marker in `PROMPT_ECHO_MARKERS`; it is no longer sent to the transcription provider.
