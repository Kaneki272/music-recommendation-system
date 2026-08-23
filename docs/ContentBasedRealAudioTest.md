# Real Audio Content-Based Recommendation Test

## Test A: Song-to-Song Similarity

**Source Song:** `soundhelix_song1.mp3` (ID: e9322fe0-d0f9-563c-a5dc-34150a8656db)
- Rank 1: `soundhelix_song2.mp3` (Score: 0.9972)
- Rank 2: `soundhelix_song3.mp3` (Score: 0.9952)
- Rank 3: `synth_ambient.wav` (Score: 0.7708)

**Source Song:** `soundhelix_song2.mp3` (ID: f74bd2e1-b0c1-5d22-8332-55a18b1db34c)
- Rank 1: `soundhelix_song1.mp3` (Score: 0.9972)
- Rank 2: `soundhelix_song3.mp3` (Score: 0.9954)
- Rank 3: `synth_ambient.wav` (Score: 0.7689)

**Source Song:** `soundhelix_song3.mp3` (ID: f5d6038d-5d06-511e-bcf2-1dc365a8374c)
- Rank 1: `soundhelix_song2.mp3` (Score: 0.9954)
- Rank 2: `soundhelix_song1.mp3` (Score: 0.9952)
- Rank 3: `synth_ambient.wav` (Score: 0.8021)

**Source Song:** `synth_ambient.wav` (ID: dc62f917-1141-5800-b11d-1c9f2b9a3a88)
- Rank 1: `soundhelix_song3.mp3` (Score: 0.8021)
- Rank 2: `soundhelix_song1.mp3` (Score: 0.7708)
- Rank 3: `soundhelix_song2.mp3` (Score: 0.7689)

**Source Song:** `synth_ballad.wav` (ID: 5f1737ad-3d24-52ab-840e-f5959a6b2e2f)
- Rank 1: `synth_upbeat.wav` (Score: 0.8763)
- Rank 2: `synth_ambient.wav` (Score: 0.7495)
- Rank 3: `soundhelix_song3.mp3` (Score: 0.5584)

**Source Song:** `synth_upbeat.wav` (ID: 6562b304-570c-5420-84bb-c56bd17e22dc)
- Rank 1: `synth_ballad.wav` (Score: 0.8763)
- Rank 2: `synth_ambient.wav` (Score: 0.6873)
- Rank 3: `soundhelix_song1.mp3` (Score: 0.6264)

## Test B: User Taste Profile Recommendation
DEBUG: Dataset interactions length = 3
DEBUG: first interaction user_id = U_TEST_001, req user_id = U_TEST_001
DEBUG: first int timestamp = 2026-08-22 12:41:22.035541+00:00, ref_time = 2026-08-23 12:41:22.035541+00:00
DEBUG: fetched 3 audio features for test songs.
DEBUG: fetched keys: ['e9322fe0-d0f9-563c-a5dc-34150a8656db', 'f74bd2e1-b0c1-5d22-8332-55a18b1db34c', 'f5d6038d-5d06-511e-bcf2-1dc365a8374c']
DEBUG: interaction keys: ['e9322fe0-d0f9-563c-a5dc-34150a8656db', 'f74bd2e1-b0c1-5d22-8332-55a18b1db34c', 'f5d6038d-5d06-511e-bcf2-1dc365a8374c']

User `U_TEST_001` interacting with `soundhelix_song1.mp3` (LIKE), `soundhelix_song2.mp3` (PLAY), `soundhelix_song3.mp3` (COMPLETE)
Profile State: `NORMAL`
- Rank 1: `soundhelix_song1.mp3` (Score: 0.9994)
- Rank 2: `soundhelix_song2.mp3` (Score: 0.9983)
- Rank 3: `soundhelix_song3.mp3` (Score: 0.9978)

## Test C: Exclusion Test

Excluding the top recommendation: `soundhelix_song1.mp3`
- Rank 1: `soundhelix_song2.mp3` (Score: 0.9983)
- Rank 2: `soundhelix_song3.mp3` (Score: 0.9978)
- Rank 3: `synth_ambient.wav` (Score: 0.7804)

[PASS] Exclusion successful: Explicitly excluded song was not recommended.

## Test D: Cold-Start Behavior

User `U_COLD_001` with NO history.
Profile State: `COLD_START`
Recommendations returned: 0
[PASS] Cold-start successful: No fabricated recommendations returned.