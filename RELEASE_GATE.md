# CineForge Release Gate

This checklist is a manual release gate. Do not mark an item complete without running it against the current checkout and recording the result.

## Automated checks
- [ ] Run `python run_tests.py` in an environment with project dependencies installed.
- [ ] Record any failing or skipped tests and address them.
- [ ] Confirm test expectations match the actual function signatures and behavior.
- [ ] Run the PyAV integration tests with PyAV and a compatible encoder available.

## MP4 export
- [ ] Generate a short synthetic video from test clips.
- [ ] Confirm expected resolution and frame rate.
- [ ] Decode the full video and audio streams.
- [ ] Check duration against the timeline with transitions.
- [ ] Confirm audio synchronization and that the audio track is present.
- [ ] Open and play the exported MP4 in a separate player.

## Application review
- [ ] Verify report generation is actually connected to the final export flow.
- [ ] Confirm the ComfyUI workflow is configured and reachable.
- [ ] Test the app from a fresh project and a resumed checkpoint.

## Release record
- Date/environment:
- Python version:
- PyAV version:
- Test result:
- MP4 playback result:
- Known issues:

**Do not claim release-ready or verified MP4 output until these checks are run.**
