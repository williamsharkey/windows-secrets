// speak.js in.txt out.wav - render text with XP's built-in SAPI 5.1 voice (Microsoft Sam)
var a = WScript.Arguments;
var fso = new ActiveXObject("Scripting.FileSystemObject");
var text = fso.OpenTextFile(a(0), 1).ReadAll();
var v = new ActiveXObject("SAPI.SpVoice");
var s = new ActiveXObject("SAPI.SpFileStream");
var fmt = new ActiveXObject("SAPI.SpAudioFormat");
fmt.Type = 22;                 // SAFT22kHz16BitMono
s.Format = fmt;
s.Open(a(1), 3, false);        // SSFMCreateForWrite
v.AudioOutputStream = s;
v.Rate = -1;
v.Speak(text, 0);
s.Close();
WScript.Echo("spoke " + text.length + " chars with " + v.Voice.GetDescription());
