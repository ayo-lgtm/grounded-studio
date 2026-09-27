# craft: video-edit
version: 1.0.0
source: OpenMontage ffmpeg pattern, source-faithful
used_by: product-walkthrough, sop-training, feature-delta

allowed: cut dead air, chapter on cuts, zoom on click box, captions, local TTS ducking, 1080p scale, concat dirty+kept chapters
forbidden: text-to-video B-roll, avatars, generated UI, cloud music
Keep an EDL json next to the artifact so refresh is diffable.
