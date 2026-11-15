"""The narration: Kayleigh (TEEN), an invented fifteen-year-old making a bored school-project video about the music
program her (equally invented) dad made. She is a mediocre reporter: she skims the important parts and fixates on the
irrelevant ones. The accurate facts live in the on-screen captions and labels (edit.py), not in her mouth.

Every line is read by TikTok's text-to-speech voice en_us_001 (tiktok_tts.py, cached); Kokoro is only the fallback.
Each line: (id, speaker, text, caption). The caption is what is burned in (None: the text itself).
"""

VOICES = {
    'TEEN': {'tiktok': 'en_us_001', 'lang': 'a', 'voice': ('af_heart', 1.0), 'speed': 1.0},   # Kokoro fallback only
}

LINES = [
    ('t_intro', 'TEEN', "ok hi. this is my computers project. my family's technology. period four.", None),
    ('t_desk', 'TEEN', "so this is apparently what computers looked like.", None),
    ('t_dad', 'TEEN', "my dad made this thing. it's like a music plugin. idk why.", None),
    ('t_what', 'TEEN', "it's Windows. from like nineteen ninety three. so like twenty years before I was born, deadass.",
     "it's Windows. from like 1993. so like twenty years before I was born, deadass."),
    ('t_what2', 'TEEN', "those little windows are sound recorders. there's a bunch. they turn into a synthesizer. lowkey weird.", None),
    ('t_maddie', 'TEEN', "wait this ding is literally Maddie's ringtone. hi Maddie.", None),
    ('t_anyway1', 'TEEN', "anyway.", None),
    ('t_real', 'TEEN', "ok so it's like, a real Windows. inside the plugin. this is the start menu but old.", None),
    ('t_about', 'TEEN', "ok there's a box with like, copyright and stuff. whatever.", None),
    ('t_free', 'TEEN', "it says sixteen percent free? free what.", "it says 16% free? free what."),
    ('t_license', 'TEEN', "licensed to: user. company one. ok so nobody.", "licensed to: user. company1. ok so nobody."),
    ('t_year', 'TEEN', "and everything says nineteen ninety three. that's so random.", "and everything says 1993. that's so random."),
    ('t_note1', 'TEEN', "ok my dad wrote this down for me to say.", None),
    ('t_note1b', 'TEEN', "it is a real Windows three point one one, running inside the plugin. and every note is played by the real Sound Recorder, from nineteen ninety three.",
     "\"it is a real Windows 3.11, running inside the plugin. and every note is played by the real Sound Recorder, from 1993.\""),
    ('t_ok', 'TEEN', "ok.", None),
    ('t_play', 'TEEN', "when you press a key, one of the recorders plays it. that's the whole thing.", None),
    ('t_packs', 'TEEN', "there's like a thousand sounds or whatever. you pick one and press load.", None),
    ('t_granite', 'TEEN', "this one's a flute but slow. it's giving elevator.", None),
    ('t_shaded', 'TEEN', "this is the Windows XP ding but slowed down. it's a bass now. no cap.", None),
    ('t_rounded', 'TEEN', "this one is also a Windows sound. they're all Windows sounds.", None),
    ('t_note2', 'TEEN', "he also wrote: it works in Ableton and other DAWs, as a VST3, AU, or CLAP. on Windows and Mac.",
     "he also wrote: \"it works in Ableton and other DAWs, as a VST3, AU or CLAP. on Windows and Mac.\""),
    ('t_idk', 'TEEN', "idk what any of that means.", None),
    ('t_vibe', 'TEEN', "if you make vaporwave, do slow chords and turn up the wobble. idk, it's on the screen.", None),
    ('t_song', 'TEEN', "ok this is the song tab. you put in a MIDI file and it makes a whole song. every track gets its own Windows. that seems like a lot.", None),
    ('t_export', 'TEEN', "then you export it.", None),
    ('t_kits', 'TEEN', "drums. with a calculator. ok.", None),
    ('t_maddie2', 'TEEN', "Maddie this is the calculator from math. you know which one.", None),
    ('t_steps', 'TEEN', "my dad's Minesweeper is broken. you can't even lose. it's like a beat thing now.", None),
    ('t_rec', 'TEEN', "it also records stuff. into the recorder. obviously.", None),
    ('t_note3', 'TEEN', "and: it's free, at william sharkey dot com, slash sound wave nineteen ninety three. you can also try it in your browser.",
     "and: \"it's free, at williamsharkey.com/sndwave1993. you can also try it in your browser.\""),
    ('t_web2', 'TEEN', "he made me say the website.", None),
    ('t_citypop', 'TEEN', "wait. ok. this part is actually kind of a vibe. it's city pop. I love city pop. he made a whole album on it.", None),
    ('t_citypop2', 'TEEN', "it plays inside the plugin in the next version. lowkey I'm stealing it.", None),
    ('t_anyway', 'TEEN', "anyway.", None),
    ('t_bye', 'TEEN', "so yeah that's my family's technology. sources: my dad.", None),
    ('t_tag', 'TEEN', "sound wave nineteen ninety three. total sound solutions for globalized audio. that's the slogan. I didn't write it.",
     "SNDWAVE1993. total sound solutions for globalized audio. that's the slogan. I didn't write it."),
]
