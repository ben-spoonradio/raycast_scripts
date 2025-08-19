from kittentts import KittenTTS
m = KittenTTS("KittenML/kitten-tts-nano-0.1")

audio = m.generate("Jacob Bennett really inspired me here. I get so much value out of the stories he writes, I want to share some of how I manage my own day-to-day.", voice='expr-voice-3-m' )

# available_voices : [  'expr-voice-2-m', 'expr-voice-2-f', 'expr-voice-3-m', 'expr-voice-3-f',  'expr-voice-4-m', 'expr-voice-4-f', 'expr-voice-5-m', 'expr-voice-5-f' ]

# Save the audio
import soundfile as sf
sf.write('kitten_tts.wav', audio, 24000)
 