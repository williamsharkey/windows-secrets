# Electromechanical computation and its sounds: research, sources and designs for the `electromech` category

Status: research plus a sound collection for BASILISK SYNTH (XP) and BASILISK 16 (3.11). Lane date 2026-11-13.

- The sounds: `library/sources/electromech/*.wav` (git-ignored). The originals: `library/sources-raw/electromech/`.
- The provenance: `library/catalog/electromech.json`, one entry per sound, with `source_url`, `author`, `license`
  and `license_proof_url`. Synthesized sounds have `"origin": "synth"`; hybrids of a recording and synthesis
  have `"origin": "synth+recording"` and list their `parents`.
- The generators: `library/tools/synth_sources.py` (numpy, deterministic, seeded by crc32 of each id).
- The preset designs: `library/research/electromech-presets.json`, with 40 instruments as DNA v2 strings and 12
  percussion kits as DNA v3 kit maps (PRESET-ENGINE-2.md §15.2).

Every sound is played by a real Sound Recorder. The plugin never synthesizes. So everything synthetic here was
rendered offline into a WAV that becomes a library source, like a recording.

The owner asked for extra weight on three things, and this file follows that order of priority:

1. electromechanical **actuators** (solenoids, relays, steppers, hammers, magnets, clutches, escapements);
2. **line noise and signalling** (current loops, FSK, modems, telegraph, dial pulses, hum, crackle, dropouts);
3. **message events** on printers and terminals: what you hear when a message arrives, is stored and is displayed.

Contents

1. The physics of the sound: what makes an electromechanical noise
2. Relay computers
3. Unit-record (punched card) equipment
4. Telegraph, teletype, Telex and ticker
5. Telephone switching, dialling and line signals
6. Mechanical calculators, cash registers and typewriters
7. Memory and output: drums, tape, paper tape and line printers
8. Displays: split-flap, flip-disc, nixie
9. Early computer music
10. Message events: arrive, store, display
11. What was collected (counts, licences, provenance)
12. Synthesized sources (methods and the list)
13. Presets and kits
14. Gaps and next steps
15. Sources and further reading

---

## 1. The physics of the sound: what makes an electromechanical noise

Every machine in this file makes its sound from one of a few mechanisms. Knowing which one is at work tells you
how to cut a recording and how to model it.

| Mechanism | What happens | What you hear | How to cut or model it |
|---|---|---|---|
| **Armature pull-in** (relay, solenoid, magnet) | The coil current rises in 1 to 10 ms (L/R). The pull grows like 1/gap², so the armature speeds up and hits the pole face hard. | A sharp, bright "tick" or "clack" with a body of 1 to 5 kHz plate modes. Often 1 to 4 **bounces** within 1 to 5 ms (contact bounce). | Attack slice from the first transient. Model: mass, spring and restitution (section 12.1). |
| **Armature release** | The coil current decays, a return spring throws the armature back onto its back stop. | A softer, duller, often higher "tick" than the pull. It comes a few ms after the current stops (the release delay). | Release slice. Keep pull and release as separate files: the pair is the relay's "voice". |
| **AC chatter** | An AC coil without a shading ring lets go twice per mains cycle. | A buzz at 100 or 120 Hz with a metallic edge, heard in tired contactors and doorbells. | Loop. Model: an impact per half cycle. |
| **Stepping / ratchet** | A pawl driven by a magnet advances a ratchet wheel one tooth per pulse. | A row of identical "chunks" at the pulse rate (10 per second from a dial; 30 to 200 per second when hunting). | Slice one step; also keep a run as a loop. |
| **Hammer or typebar strike** | A hammer flies (cam or magnet) and hits type, ribbon, paper and platen. | A hard broadband "thwack" damped by the paper. The platen and frame add a low thud. | One-shot. |
| **Punch** | A die shears card or paper tape. | A thud plus a short paper "tear" noise. | One-shot; runs as loops. |
| **Clutch trip and cycle** | A latch magnet releases a single-revolution clutch; a cam shaft turns once. | Click, then a whirr or a rattle of linkages, then a stop "clunk". This is the *rhythm* of tabulators, adding machines and teletypes. | Phrase or loop at the machine's cycle rate. |
| **Motor and gearing** | Universal or induction motors; line shafts; gears. | A steady hum at twice the mains frequency, rotation partials (shaft rpm / 60), gear-mesh whine (teeth × rps), bearing hiss. | Drones; pitched. |
| **Bells and gongs** | A clapper or hammer strikes a shell. | Inharmonic partials (shell ratios about 1 : 2.6 : 4.9 : 7.7) with long decay. | Pitched one-shots; estimate the root. |
| **Line signals** | Current pulses, tones (FSK, call progress), induced hum, impulse noise. | Tones, warbles, clicks, hiss, hum, crackle, dropouts. | Loops; tones are pitched. |

Two facts matter for an instrument built on Sound Recorder:

- **Attack and release pairs.** A relay is two sounds, not one. A kit pad can play the pull on note-on and a
  gated release pad can be its partner. The kit spec's velocity windows and mute groups make "a relay that
  operates and releases" playable.
- **Rhythm comes from the machine cycle.** A teletype at 10 characters per second, a tabulator at 150 cards per
  minute (one cycle every 0.4 s = 150 BPM) and a sorter at 1000 cards per minute (16.7 Hz) each have a tempo.
  Loops were cut and generated at those authentic rates, so they lock to a DAW tempo when the tempo matches.

## 2. Relay computers

### Zuse Z3 and Z4

- **Z3** (Konrad Zuse, Berlin, finished 1941): about 2,600 telephone relays (about 600 in the arithmetic unit,
  1,400 in a 64-word memory of 22-bit floating-point words). The clock ran at about 5 to 10 Hz. The program came
  from punched 35 mm film. It was destroyed in an air raid in 1943; working replicas exist (the Konrad Zuse
  Museum in Hünfeld and the Deutsches Museum in Munich).
- **Z4** (1945; in service at ETH Zürich 1950 to 1955): about 2,200 relays and a mechanical memory of sliding
  sheet-metal pins (64 words of 32 bits). It was the first commercially delivered computer.
- **Sound:** a relay computer is a room of relays clicking at the clock rate. Each operation is a *cascade*: one
  relay's contacts energize the next, so a single addition is a fast ripple of pulls and releases, repeated at
  the clock. The Z3 replica's sound is a dense, even clatter at a few hertz, with no motor. In the memory, each
  access rattles a row of relays.
- **Used for:** wing-flutter calculations at the Henschel aircraft works (Z3), and engineering calculations at
  ETH (Z4).

### Harvard Mark I and Mark II

- **Mark I** (IBM ASCC; Howard Aiken and IBM; working 1944): 51 feet long, about 765,000 parts. It had 72
  accumulators built from **rotating decimal counter wheels** and about 3,500 relays, all driven by a 50-foot
  line shaft turned by a 5 hp electric motor. An addition took 0.3 s, a multiplication 6 s and a division about
  15 s. The program came from punched paper tape; the results went to card punches and electric typewriters.
- **Sound:** a continuous mechanical roar from the shaft and clutches, with the clicking of counter wheels
  engaging and relays operating over it. Observers famously likened it to a roomful of people knitting. Unlike the
  relay-only machines, it has a **motor bed**: a pitched drone with clicks on top.
- **Mark II** (1947): about 13,000 relays, faster. Its logbook holds the moth "first actual case of bug being
  found", taped in on 9 September 1947 (relay #70, panel F).
- **Used for:** ballistics tables and Manhattan Project calculations (Mark I); Navy work (Mark II).

### Bell Labs relay calculators, Models I to VI

- George Stibitz built the "Model K" binary adder from telephone relays on his kitchen table in 1937.
- **Model I, the Complex Number Calculator** (1940): about 450 relays, with teletypes as terminals. On 11
  September 1940, at the American Mathematical Society meeting at Dartmouth, it was used remotely over a telegraph
  line from New Hampshire to New York: the first remote use of a computer. That makes it the origin of the
  "message arrives on a teletype" idea in section 10.
- **Models II to VI** (1943 to 1949): the Relay Interpolator (II), the Ballistic Computer (III), IV, and the large
  Model V (two built, about 9,000 relays each) and Model VI. They used paper tape for programs and data, and
  teletypes for output.
- **Sound:** telephone-exchange relays (the same parts as the switching offices of section 5), plus teletypes and
  tape readers.

### Atanasoff–Berry Computer (ABC)

- John Atanasoff and Clifford Berry, Iowa State, 1937 to 1942. Its logic was electronic (about 300 vacuum tubes).
  Its memory was electromechanical: two **rotating drums** of 1,600 capacitors that turned once per second
  (60 rpm), refreshed on every turn.
- Its card system burned binary holes into cards with **electric sparks** (arcing), and read them back.
- **Sound:** the drum motor's steady turning, the card feed, and the snap and crackle of the spark writer. That
  is why an "arc / spark" source is in this collection.

## 3. Unit-record (punched card) equipment

- **Hollerith's tabulator** (1890 US census). An operator pressed a pin box onto a card; pins that passed through
  holes dipped into mercury cups and closed circuits. Each closed circuit advanced a dial counter by one, and
  **a bell rang** to confirm that the card had been read. A sorting-box lid also sprang open to show where the card
  should go. The rhythm: press, ding, lid slap, card drop.
- **Keypunches, IBM 026 (1949) and 029 (1964).** Each key press punches one column: a magnet-driven punch bail
  and dies make a hard "chunk", and the card escapes one column. **Duplication** copies a master card at about
  20 columns per second (a rattling burst); skipping is faster. Feeding, registering and releasing a card add a
  whoosh, a thud and the stacker's slap. The sound of a keypunch room is many of these staccato chunks.
- **Sorters, IBM 082 (650 cards per minute), 083 (1000 per minute) and 084 (2000 per minute).** A sorter reads one
  column per pass with a brush and drops each card into one of 13 pockets by opening a chute blade. At 1000 cards
  per minute the rhythm is 16.7 Hz, a buzzing clatter over the feed motor.
- **Collators, IBM 077, 085, 087 and 088,** merge and match two decks, with two feeds clattering at once.
- **Accounting machines (tabulators), IBM 405 and 407.** The 407 (1949) read 150 cards per minute and printed with
  120 **type wheels**, programmed by a plugboard (control panel). Each machine cycle is a heavy rhythmic unit, a
  "chunk-chunk-ka-chunk", at 150 per minute, which is 150 BPM. Accumulator wheels add a clicking tick under it;
  the print line is a volley of type wheels striking together; carriage skips (tape-controlled) add a whirr.
- **Reproducers and interpreters, IBM 514, 519 and 557.**
- **Used for:** censuses, payroll, inventory and billing; scientific tables (the Columbia/Watson lab); and the
  input and output of the first stored-program computers.

## 4. Telegraph, teletype, Telex and ticker

- **The Morse telegraph** (from 1844). A key opens and closes a DC current loop. At the receiving end a **sounder**
  (an electromagnet pulling an armature against two stops) makes two different sounds: a "click" on the down
  stroke and a "clack" on the up stroke. Operators read the *interval* between the click and the clack. **Relays**
  repeated a weak line current into a local sounder circuit; that is where the word "relay" comes from.
- **Teletype, Model 15 (1930).** A page printer using 5-unit Baudot/Murray code (ITA2) at 60 words per minute,
  which is 45.45 baud. A **selector magnet** follows the start-stop signal. A single-revolution clutch trips on the
  start bit; the selector picks up the five code levels; then a **typebar** strikes. Its sound is dense, with
  bars and linkages: "chack-chack-chack" over a motor hum, with a heavy carriage return and a bell on BEL.
- **Model 28 (1951)** used a typebox; **Model 33 ASR (1963)** became the minicomputer console (ASCII, 110 baud, 10
  characters per second). The 33 prints with a cylindrical typewheel struck by a hammer. Its sound is a steady
  motor hum, a quick "chunka" per character, a carriage-return thump and the bell. The ASR added a paper-tape punch
  (a high "brrrrp") and a reader (a steady stepping tick).
- **Telex** (from 1933 in Germany; international at 50 baud ITA2). Teleprinters were connected through
  automatic exchanges. An incoming call **starts the motor**. The machines exchange **answerbacks**: a mechanical
  drum sends the station's ID when it receives "WRU" (who are you, FIGS+D). Then the message prints, and at the end
  the motor runs on and stops.
- **Current-loop line sound.** The telegraph and teletype line itself is DC pulses (20 or 60 mA). Heard on a
  speaker or through induction into a telephone line, it is a harsh rhythmic clicking, the "telegraph chatter" of
  crosstalk. On radio (RTTY) the same code is FSK: two tones 170 Hz apart (2125/2295 Hz audio), the warble of
  RTTY.
- **Stock tickers** (Edison's Universal Stock Printer, 1869/1871). Two typewheels (letters and figures) step
  round under a stepping magnet, and a printing magnet presses the tape on the right character. The sound is a
  fast ticking with print strikes, the "ticker".
- **Hellschreiber** (Rudolf Hell, 1929) sent text as a facsimile-like pixel stream; **radiofax** (120 lines
  per minute) sent weather maps. Both are characteristic radio-line sounds.

## 5. Telephone switching, dialling and line signals

- **Strowger step-by-step** (Almon Strowger's patent of 1891; first exchange at La Porte, Indiana, 1892). Each dial
  pulse steps a two-motion selector **vertically** (one level per pulse); then it **hunts rotary**, stepping
  across the level at its own rate until it finds a free line. Every step is a magnet, a pawl and a ratchet: a
  "chunk". A big step-by-step office during the busy hour is a roar of thousands of selectors stepping, a sea of
  clicks with rhythmic 10 Hz pulse trains inside. On release, the wipers spin back home and drop with a clatter.
- **Panel** (Bell System, 1920s, motor-driven elevators) and **crossbar** (No. 1 crossbar 1938, No. 5 crossbar
  1948). A crossbar switch closes a crosspoint with a **select magnet** (rocking a horizontal bar) and a **hold
  magnet** (vertical). It makes a "chunk-CHUNK" pair, quieter than Strowger. Common-control **markers** are racks
  of relays operating in fast sequences, a burst of relay chatter per call. The **kiss-off** is the release of a
  completed setup.
- **Rotary dial.** Winding the dial is a ratchet of clicks; letting go runs it down under a centrifugal governor at
  **10 pulses per second**, breaking the loop with a break/make ratio of about 60/40 (US) or 66/33 (UK). The
  pulses are heard on the line as clicks and are seen in the exchange as relays and steppers moving.
- **Ringers.** 20 Hz ringing current (about 90 V AC in the US) drives a polarized ringer whose clapper trills
  between two gongs: about two seconds on and four off in North America. In the exchange, **ringing machines**
  (motor-generators with interrupters) made the current and the cadence.
- **Call-progress tones.** These come from the Bell System's precise tone plan: dial tone is 350 + 440 Hz;
  ring-back is 440 + 480 Hz, 2 s on and 4 s off; busy is 480 + 620 Hz, 0.5 s on and 0.5 s off; reorder is the same
  pair at 0.25 s on and off. The special information tones are 913.8, 1370.6 and 1776.7 Hz. Earlier offices made
  their tones with motor-driven **tone alternators and interrupters**, so old dial tones hum and growl.
- **Data over the line.** The Bell 101 (1958, for SAGE) and **Bell 103** (1962) used 300-baud FSK: 1070/1270 Hz
  from the originating side and 2025/2225 Hz from the answering side. The **Bell 202** used 1200 baud at
  1200/2200 Hz. **Acoustic couplers** (1960s and 70s; the Carterfone decision of 1968 opened the network to
  them) pushed the tones through the carbon microphone of an ordinary handset.
- **Line noise.** Long lines picked up **power-line hum** (60 or 50 Hz and odd harmonics) and **crosstalk** (faint
  other conversations, or the clicking of telegraph circuits on the same route). Bad joints gave **crackle**.
  Carrier systems gave **dropouts** and **hits**. Electromechanical offices were notorious sources of **impulse
  noise**: every stepping switch and relay induced clicks into nearby pairs. That impulse noise was the main cause
  of errors on early data circuits.

## 6. Mechanical calculators, cash registers and typewriters

- **Comptometer** (Dorr Felt, 1887): key-driven adding. Each key press adds directly, so it makes a crisp
  "click-clack" with a spring return; trained operators played it like a rhythm instrument.
- **Arithmometers and pinwheel machines** (Odhner, Brunsviga): a hand crank turns a pinwheel. Every turn is a
  ratcheting whirr with a detent click; carriage shifts clack.
- **Curta** (Curt Herzstark, 1948 to 1972): a hand-held stepped-drum (Leibniz wheel) calculator. The crank
  turn has a fine ratchet buzz and a click at the end; the carriage lifts and turns with small detents.
- **Motor calculators** (Friden, Marchant, Monroe, from the 1930s): an electric motor drives the stepped drums or
  proportional gears through repeated add or subtract cycles. **Division** is the famous one: a long, accelerating
  clatter of cycles and carriage shifts, ending with a clunk. Friden's square-root models (SRQ) were even more
  dramatic.
- **Adding and listing machines** (Burroughs, 1888, and many others): a handle pull drives a rack of
  ratchets, then the print strike and the paper advance.
- **Cash registers** (James Ritty's "Incorruptible Cashier", 1879; National Cash Register): the keys set up a
  sale, a crank or a motor cycles the mechanism, and the drawer springs open and **rings a bell**, so the owner
  hears every sale. That is the "ka-ching".
- **Typewriters.** The Sholes and Glidden (1873) started the line. The sounds: typebar strikes on a hard platen,
  the escapement ticking the carriage on, the **margin bell** a few characters before the right margin, and the
  carriage return (the lever, a zip of the carriage, the slam). Electric typewriters added a motor hum and a
  power-driven strike. The **IBM Selectric** (1961) replaced typebars with a "golf ball" element positioned by
  **tilt** (4 rows) and **rotate** (11 positions on each half); the ball turns 180° for shift. Every character is a
  tiny whirr-click followed by the strike, a sound unlike any typebar machine.
- **Friden Flexowriter:** an electric typewriter with a paper-tape punch and reader, used as the console of early
  computers (the LGP-30, for example).

## 7. Memory and output: drums, tape, paper tape and line printers

- **Drum memory** (ERA 1101/1103, IBM 650, LGP-30 and others). A magnetized drum spins under fixed heads. The
  IBM 650's drum turned at 12,500 rpm, which is 208 Hz: the machine had a **pitched whine** near G#3, with
  bearing noise and the clicks of head-select relays and the card units on top.
- **Magnetic tape:** UNIVAC Uniservo (1951, metal tape) and the IBM 726/727/729 vacuum-column drives. Their sound
  is the vacuum blowers' hiss and the reels' jerky start-stop bursts as blocks are read. It is the "computer" of
  every 1960s film.
- **Paper tape.** Mechanical readers step at 10 to 20 characters per second (Teletype). Photoelectric readers
  read hundreds to thousands per second (Ferranti and Elliott readers; Colossus read 5,000 per second from its
  "bedstead") and made a whirr and a flapping of tape bins. **Tape punches** (Teletype BRPE, about 110 per second)
  buzz.
- **Line printers.** The **IBM 1403** (1959) printed 132 columns with a moving chain (later a train) of type
  slugs. A hammer behind each column fires when the right character passes. The Model 2 printed 600 lines per
  minute and the Model 3/N1 up to 1100. Each line is a dense volley of hammer hits followed by a paper-space
  "thump". A page eject (slew) is a loud "brrrp". Because the hammer timing depends on which characters are
  printed, programmers wrote **1403 music**: lines chosen so that the hammers fire at audio rates, giving buzzy
  pitched notes. The Computer History Museum's 1401 restoration team still demonstrates it.

## 8. Displays: split-flap, flip-disc, nixie

- **Split-flap** (Solari di Udine boards from 1956; also clocks and departure boards). Flaps on a drum are
  released one at a time; each falls with a light plastic "tick". A board update is a cloud of fluttering ticks
  that thins out as units reach their characters: the sound of an arrival or departure.
- **Flip-disc** (Ferranti-Packard, invented by Kenyon Taylor around 1961; used on buses, scoreboards and
  signs). Each disc has a permanent magnet and is flipped by a coil pulse. It makes a crisp snap, and a whole sign
  rewrites with a rippling cascade of snaps.
- **Nixie tubes** (Burroughs, 1955) are silent, but the relay and stepper counters that drove early numeric
  displays were not. In this collection the "display" sounds are the flap, the disc, the line printer and the
  teletype.

## 9. Early computer music

- **CSIRAC** (Australia; in 1951 the first computer to play music in public). Programmers sent pulses straight
  to a loudspeaker. Pitch came from loop timing, so the notes were raw pulse trains with slightly off pitches.
  Geoff Hill programmed the repertoire (for example the "Colonel Bogey March").
- **Ferranti Mark 1** (Manchester, 1951). The **hoot** instruction pulsed the speaker. Christopher Strachey and
  others programmed tunes ("God Save the King", "Baa Baa Black Sheep", "In the Mood"), and a BBC crew recorded them
  in 1951. The pitches are bound to multiples of the machine's 240 µs beat, so many notes are audibly out of tune.
  The University of Canterbury restored the recording in 2016.
- **IBM 704 / 7094 at Bell Labs.** Max Mathews wrote MUSIC I in 1957. In 1961 John Kelly, Carol Lochbaum and
  Mathews made a 7094 **sing "Daisy Bell"** with vocal-tract synthesis and an accompaniment; Arthur C. Clarke heard
  it, and HAL 9000 sings it in *2001*.
- Others: tunes played on BINAC, UNIVAC and many machines through their speakers and radios; line-printer music
  (section 7).
- **Licensing note:** the historical recordings (Ferranti 1951, CSIRAC, "Daisy Bell") are **not public domain**,
  or their status is unclear. None were collected. Instead the synthesis models their *method*: Ferranti's
  quantized-period hoot, CSIRAC's raw pulses and a 1961-style buzz-plus-formant vowel (section 12).

## 10. Message events: arrive, store, display

The owner's focus: "the way early printers or terminals might have clicks or other sounds when getting a
message or storing it or displaying it". These are the usual event sequences, with the times that the synthesis
uses. Each row is also a row (four to six adjacent pads) in the "Message Center" kit.

| Event | Machine | Sequence (time from the start) |
|---|---|---|
| **Arrive** | Telex / teletype | ring or bell (0 ms); motor-start relay and contactor (~500 ms); motor spins up (0.5 to 1.2 s); answerback burst; print burst at 10 or 6.7 characters per second; CR (~200 ms whirr and slam) plus LF (ratchet); at the end the motor runs on, then stops |
| **Arrive** | Telegraph office | sounder clicks (the call letters); the operator answers with the key; the message as a click/clack rhythm |
| **Arrive** | Telephone | ringer trill (20 Hz clapper, 2 s); off-hook relay click; then line sounds (dial tone, crosstalk, hum) |
| **Arrive** | Modem / terminal | ring; relay "off-hook" click; answer tone (2100 Hz with phase reversals); FSK carrier; the terminal's printing |
| **Store** | Paper tape (ASR 33 / BRPE) | the punch motor starts; a "brrrp" burst of punch hits (10 to 110 rows per second); tape feed; tear-off |
| **Store** | Card punch | card feed whoosh; a punch "chunk" per column (or a duplicating rattle); release; stacker thump |
| **Store** | Drum / tape | write-current bursts synchronized with the drum's turn; a tape reel jerk |
| **Display** | Line printer | a hammer volley per line (55 to 100 ms); paper space; a slew for page eject |
| **Display** | Split-flap / flip-disc | a cascade of flaps or snaps that thins out to silence |
| **Display** | Selectric / Flexowriter | a whirr-click (tilt and rotate) followed by the strike, per character |

## 11. What was collected

**261 sounds, 22.3 MB, 505 s** of converted audio (PCM 16-bit mono 22050 Hz, trimmed, peak -1 dBFS, 10 ms fades:
the existing `build_library.py` rules). Of these, 153 are slices of recordings, 100 are synthesized and 8 are hybrids.
The raw originals take 163 MB in `sources-raw/electromech/` (the largest is the 370 s film excerpt).

### Licences and provenance

| Source | Files used | Slices | Licence | Proof kept per entry |
|---|---|---|---|---|
| Freesound | 76 sounds | 123 | CC0-1.0 (`fetch.py` refuses any page whose licence links are not exactly `publicdomain/zero`) | the sound page URL |
| archive.org SSE Library (13 files from the COMMUNICATIONS, MECHANICAL, MACHINES, BELLS, CLOCKS, ALARMS and ELECTRICITY items) | 13 | 22 | CC0-1.0 (the items' `licenseurl`) | the item URL |
| Wikimedia Commons | 7 | 7 | Public domain (RTTY, AMTOR, Hellschreiber, PSK31 samples; NWS radiofax, a US government work) and CC0 (typewriter ding, Psalm 118 CW) | the file page and licence template |
| archive.org Prelinger-style film: *The Coming of the Dial* (GPO Film Unit, 1933) | 1 | 1 | Public Domain Mark 1.0 on the item | the item URL |
| `synth_sources.py` | - | 108 | CC0-1.0 (generated here). Hybrids inherit only CC0/PD parents. | the tool path, the method and the seed |

Each catalog entry keeps `source_url`, `download_url`, `author`, `license`, `license_proof_url`, `raw_sha256`,
`start` and `dur` (the slice) and `origin`. Convert or rebuild with:

```
python3 library/tools/synth_sources.py                 # synthesized + hybrid sources (hybrids need the recordings built)
python3 library/tools/build_library.py --only electromech --no-manifest
```

(`sources/manifest.json` does not exist in this checkout; a full `build_library.py` run writes it for every
category, electromech included. `build_library.py` now also copies `origin`, `kind`, `tags`, `parents`,
`synth_method` and `seed` into the manifest.)

What was **not** collected, on purpose: the 1951 Ferranti recording, CSIRAC, "Daisy Bell", Computer History Museum
1401/1403 videos and the BBC sound effects on Freesound (their underlying RemArc licence is not CC0). They are
copyrighted or unclear.

### Counts by sound type

| Group | Recordings | Synth | Hybrid | Total |
|---|---|---|---|---|
| Actuators: relays, solenoids, contactors, magnets, hammers | 38 | 18 | 0 | 56 |
| Switching: Strowger, crossbar, switchboards | 7 | 5 | 1 | 13 |
| Line and signalling: tones, modems, RTTY, noise | 27 | 25 | 1 | 53 |
| Telegraph, teletype, ticker | 11 | 11 | 0 | 22 |
| Telephones and dials | 11 | 2 | 1 | 14 |
| Printers, punches, tape, displays | 18 | 19 | 1 | 38 |
| Typewriters | 15 | 2 | 0 | 17 |
| Calculators, registers, meters | 13 | 4 | 0 | 17 |
| Bells and buzzers | 6 | 3 | 1 | 10 |
| Motors, drones, computers, tonal synthesis | 7 | 11 | 3 | 21 |
| **Total** | **153** | **100** | **8** | **261** |

**Actuators: relays, solenoids, contactors, magnets, hammers.**

`em_clockwork_timer_a` (oneshot, 0.40 s); `em_clockwork_timer_loop` (loop, 2.00 s); `em_contactor_a` (oneshot, 0.29 s); `em_contactor_b` (oneshot, 0.26 s); `em_contactor_c` (oneshot, 0.24 s); `em_crossbar_timing_a` (oneshot, 0.39 s); `em_crossbar_timing_b` (oneshot, 0.40 s); `em_crossbar_timing_loop` (loop, 3.00 s); `em_jukebox_a` (oneshot, 0.40 s); `em_kontaktor_a` (oneshot, 0.47 s); `em_kontaktor_b` (oneshot, 0.29 s); `em_mech_timer_loop` (loop, 2.00 s); `em_metal_click_a` (oneshot, 0.12 s); `em_metal_click_b` (oneshot, 0.14 s); `em_metal_click_c` (oneshot, 0.20 s); `em_metal_click_d` (oneshot, 0.23 s); `em_phone_buzzer_loop` (loop, 2.00 s, root: none found); `em_relay_click_a` (oneshot, 0.05 s); `em_relay_click_b` (oneshot, 0.13 s); `em_relay_click_c` (oneshot, 0.11 s); `em_relay_hs_a` (oneshot, 0.61 s); `em_relay_hs_b` (oneshot, 0.24 s); `em_relay_hs_loop` (loop, 2.00 s); `em_relay_large_a` (oneshot, 0.39 s); `em_relay_large_b` (oneshot, 0.39 s); `em_relay_large_c` (oneshot, 0.68 s); `em_relays_fast_loop` (loop, 2.00 s); `em_selector500_a` (oneshot, 0.62 s); `em_selector500_b` (oneshot, 0.06 s); `em_selector500_c` (oneshot, 0.07 s); `em_selector500_loop` (loop, 3.00 s); `em_solenoid12v_a` (oneshot, 0.10 s); `em_solenoid12v_b` (oneshot, 0.10 s); `em_solenoid_sw_a` (oneshot, 0.62 s); `em_solenoid_sw_b` (oneshot, 0.61 s); `em_stamp_a` (oneshot, 0.62 s); `em_stamp_b` (oneshot, 0.25 s); `em_switch_a` (oneshot, 0.17 s); `ems_clutch_trip` [synth] (oneshot, 0.35 s); `ems_contactor_pull` [synth] (oneshot, 0.25 s); `ems_contactor_release` [synth] (oneshot, 0.20 s); `ems_escapement` [synth] (oneshot, 0.33 s); `ems_flipdot` [synth] (oneshot, 0.09 s); `ems_print_hammer` [synth] (oneshot, 0.09 s); `ems_punch_magnet` [synth] (oneshot, 0.25 s); `ems_relay_bouncy` [synth] (oneshot, 0.10 s); `ems_relay_buzz_ac` [synth] (loop, 1.60 s); `ems_relay_pair` [synth] (oneshot, 0.21 s); `ems_relay_pull` [synth] (oneshot, 0.17 s); `ems_relay_rack_chatter` [synth] (loop, 2.40 s); `ems_relay_release` [synth] (oneshot, 0.10 s); `ems_relay_tiny` [synth] (oneshot, 0.12 s); `ems_rotary_dial` [synth] (phrase, 1.42 s); `ems_selector_magnet` [synth] (oneshot, 0.13 s); `ems_stepper_step` [synth] (oneshot, 0.20 s); `ems_telegraph_sounder` [synth] (oneshot, 0.17 s).

**Switching: Strowger, crossbar, switchboards.**

`em_crossbar_kissoff` (oneshot, 1.01 s); `em_exchange_box_a` (oneshot, 0.62 s); `em_stepper_steps` (phrase, 4.09 s); `em_switchboard_click_a` (oneshot, 0.17 s); `em_switchboard_click_b` (oneshot, 0.21 s); `em_switchboard_relays` (loop, 3.00 s); `em_gpo_alarm_bell` (phrase, 9.00 s, root: none found); `emh_switchroom_drone` [hybrid] (loop, 3.00 s); `ems_crossbar_release` [synth] (oneshot, 0.20 s); `ems_crossbar_select` [synth] (phrase, 0.40 s); `ems_stepper_release` [synth] (phrase, 0.41 s); `ems_stepper_rotary_hunt` [synth] (phrase, 0.64 s); `ems_stepper_vertical` [synth] (phrase, 0.79 s).

**Line and signalling: tones, modems, RTTY, noise.**

`em_amtor` (phrase, 13.65 s); `em_answering_machine_a` (oneshot, 0.62 s); `em_answering_machine_loop` (loop, 3.00 s); `em_arc_a` (oneshot, 0.07 s); `em_arc_b` (oneshot, 0.55 s); `em_arc_c` (oneshot, 0.06 s); `em_arc_loop` (loop, 2.00 s); `em_busy_us` (phrase, 0.55 s); `em_cw_psalm_loop` (loop, 4.00 s); `em_data_tones` (phrase, 10.68 s); `em_dialtone_b` (phrase, 4.00 s, root ~A2 (113 Hz, yin)); `em_hellschreiber_loop` (loop, 4.00 s); `em_hum_mains_loop` (loop, 3.00 s, root ~A#1 (60 Hz, yin)); `em_hum_tube_loop` (loop, 3.00 s, root ~B1 (60 Hz, yin)); `em_modem1200` (phrase, 5.63 s); `em_modem_beep` (oneshot, 0.23 s, root ~E7 (2696 Hz, fft peak)); `em_modem_dial_tones` (phrase, 1.86 s); `em_modem_dialup` (phrase, 14.76 s); `em_offhook_howler` (phrase, 3.73 s); `em_psk31_loop` (loop, 4.00 s); `em_qrm_loop` (loop, 3.00 s); `em_radiofax` (phrase, 10.63 s); `em_ringback_b` (phrase, 5.83 s); `em_ringback_old_us` (phrase, 2.05 s); `em_rtty_wiki` (phrase, 13.63 s); `em_static_elec_loop` (loop, 3.00 s); `em_wwv_loop` (loop, 4.00 s); `emh_modem_crush` [hybrid] (oneshot, 14.76 s); `ems_acoustic_coupler` [synth] (loop, 1.67 s); `ems_busy` [synth] (loop, 3.00 s); `ems_crosstalk` [synth] (loop, 3.50 s); `ems_crushed_line_noise` [synth] (loop, 2.50 s); `ems_dial_tone` [synth] (oneshot, 3.00 s, root A4 (label)); `ems_fm_bell103_lead` [synth] (oneshot, 2.50 s, root ~G#3 (213 Hz, yin)); `ems_fsk_bell103_ans` [synth] (loop, 2.00 s); `ems_fsk_bell103_orig` [synth] (loop, 2.00 s); `ems_fsk_bell202` [synth] (oneshot, 1.10 s); `ems_hum_buzz_50` [synth] (oneshot, 3.00 s, root ~G1 (50 Hz, yin)); `ems_line_crackle` [synth] (loop, 3.00 s); `ems_line_dropout` [synth] (loop, 3.00 s); `ems_line_hiss` [synth] (loop, 3.00 s); `ems_line_hit` [synth] (oneshot, 0.38 s); `ems_mains_hum` [synth] (oneshot, 3.00 s, root ~B1 (60 Hz, yin)); `ems_modem_answer_tone` [synth] (oneshot, 2.70 s); `ems_modem_handshake` [synth] (phrase, 5.69 s); `ems_morse_cw` [synth] (phrase, 2.51 s); `ems_pulse_dial_digit` [synth] (phrase, 1.10 s); `ems_reorder` [synth] (loop, 3.00 s); `ems_ringback` [synth] (loop, 3.00 s); `ems_ringmod_dial_tone` [synth] (oneshot, 3.00 s, root A4 (label)); `ems_rtty_baudot` [synth] (loop, 4.39 s); `ems_rtty_idle` [synth] (oneshot, 2.50 s, root ~C7 (2130 Hz, yin)); `ems_sit_tones` [synth] (oneshot, 0.99 s).

**Telegraph, teletype, ticker.**

`em_cw_click_a` (oneshot, 0.61 s); `em_morse_buzzer_a` (oneshot, 2.39 s, root: none found); `em_morse_buzzer_loop` (loop, 3.00 s, root: none found); `em_ticker_a` (oneshot, 0.08 s); `em_ticker_b` (oneshot, 0.10 s); `em_ticker_loop` (loop, 2.00 s); `em_tty_machine_hit_a` (oneshot, 0.17 s); `em_tty_machine_hit_b` (oneshot, 0.22 s); `em_tty_machine_loop` (loop, 3.00 s); `em_tty_police_loop` (loop, 3.00 s); `em_tty_sse_loop` (loop, 3.00 s); `ems_telegraph_message` [synth] (phrase, 2.06 s); `ems_ticker` [synth] (loop, 3.00 s); `ems_tty_bell` [synth] (oneshot, 1.26 s, root ~F#6 (1483 Hz, yin)); `ems_tty_burst` [synth] (loop, 3.00 s); `ems_tty_char` [synth] (oneshot, 0.17 s); `ems_tty_cr` [synth] (oneshot, 0.41 s); `ems_tty_lf` [synth] (oneshot, 0.12 s); `ems_tty_message_received` [synth] (phrase, 7.50 s); `ems_tty_motor` [synth] (loop, 3.00 s); `ems_tty_motor_start` [synth] (phrase, 1.60 s); `ems_tty_motor_stop` [synth] (phrase, 1.40 s).

**Telephones and dials.**

`em_coin_return_a` (oneshot, 0.93 s); `em_fetap_hangup` (phrase, 0.61 s); `em_fetap_ring` (phrase, 5.53 s, root ~F6 (1395 Hz, yin)); `em_magneto_crank` (phrase, 6.36 s); `em_ring_stromberg` (phrase, 6.00 s, root ~C4 (256 Hz, yin)); `em_ring_w48` (phrase, 4.64 s, root ~G1 (48 Hz, yin)); `em_ring_we500` (phrase, 4.23 s, root ~G#5 (826 Hz, fft peak)); `em_rotary_dial_a` (oneshot, 0.49 s); `em_rotary_dial_b` (oneshot, 0.44 s); `em_rotary_dial_loop` (loop, 3.00 s); `em_wallphone_ring_loop` (loop, 3.00 s, root ~D8 (4706 Hz, fft peak)); `emh_dial_ring_mod` [hybrid] (oneshot, 0.49 s); `ems_exchange_bell_c4` [synth] (oneshot, 3.25 s, root C4 (label)); `ems_phone_ring_trill` [synth] (phrase, 2.80 s).

**Printers, punches, tape, displays.**

`em_daisywheel_a` (oneshot, 0.07 s); `em_daisywheel_b` (oneshot, 0.07 s); `em_dotmatrix_b_loop` (loop, 3.00 s); `em_dotmatrix_burst_a` (loop, 2.50 s); `em_dotmatrix_hit_a` (oneshot, 0.15 s); `em_papertape_a` (oneshot, 0.21 s); `em_papertape_b` (oneshot, 0.24 s); `em_printing_press_a` (oneshot, 0.31 s); `em_printing_press_b` (oneshot, 0.62 s); `em_printing_press_loop` (loop, 3.00 s); `em_slip_printer_a` (oneshot, 0.47 s); `em_splitflap_a` (oneshot, 0.48 s); `em_splitflap_b` (oneshot, 0.38 s); `em_splitflap_c` (oneshot, 0.78 s); `em_splitflap_loop` (loop, 2.00 s); `em_tape_recorder_a` (oneshot, 0.11 s); `em_tape_recorder_b` (oneshot, 0.26 s); `em_taxi_meter_a` (oneshot, 0.50 s); `emh_cardpunch_thump` [hybrid] (oneshot, 0.62 s); `ems_card_feed` [synth] (oneshot, 0.24 s); `ems_card_punch_col` [synth] (oneshot, 0.10 s); `ems_card_punch_dup` [synth] (loop, 3.20 s); `ems_card_stack` [synth] (oneshot, 0.28 s); `ems_drum_memory` [synth] (oneshot, 3.00 s, root ~G#3 (208 Hz, yin)); `ems_drum_write` [synth] (phrase, 1.00 s); `ems_flipdot_wipe` [synth] (phrase, 1.15 s); `ems_lineprinter_line` [synth] (oneshot, 0.19 s); `ems_lineprinter_page` [synth] (loop, 3.00 s); `ems_lineprinter_tone_a3` [synth] (oneshot, 2.50 s, root A3 (label)); `ems_selectric_char` [synth] (oneshot, 0.10 s); `ems_sorter_run` [synth] (loop, 3.00 s); `ems_splitflap` [synth] (phrase, 0.54 s); `ems_splitflap_board` [synth] (phrase, 2.16 s); `ems_tabulator_cycle` [synth] (loop, 0.40 s); `ems_tabulator_run` [synth] (loop, 3.20 s); `ems_tape_drive_shuttle` [synth] (loop, 3.00 s); `ems_tape_punch_burst` [synth] (loop, 2.00 s); `ems_tape_reader` [synth] (loop, 2.00 s).

**Typewriters.**

`em_etypewriter_loop` (loop, 3.00 s); `em_ibm_typewriter_fast_loop` (loop, 3.00 s); `em_selectric_key_a` (oneshot, 0.22 s); `em_selectric_key_b` (oneshot, 0.23 s); `em_selectric_key_c` (oneshot, 0.20 s); `em_selectric_key_d` (oneshot, 0.29 s); `em_selectric_typing_loop` (loop, 3.00 s); `em_typewriter_bell_a` (oneshot, 0.89 s, root ~D#2 (77 Hz, yin)); `em_typewriter_bell_b` (phrase, 2.98 s, root ~C#6 (1092 Hz, yin)); `em_typewriter_bell_c` (oneshot, 0.96 s, root ~G#6 (1689 Hz, yin)); `em_typewriter_bell_return` (phrase, 2.90 s); `em_typewriter_key_a` (oneshot, 0.28 s); `em_typewriter_return_a` (oneshot, 0.23 s); `em_typewriter_return_b` (oneshot, 0.13 s); `em_typewriter_return_c` (oneshot, 0.13 s); `ems_typebar` [synth] (oneshot, 0.10 s); `ems_typewriter_bell` [synth] (oneshot, 0.95 s, root ~G6 (1572 Hz, yin)).

**Calculators, registers, meters.**

`em_adder_drawer_a` (oneshot, 0.20 s); `em_adder_drawer_b` (oneshot, 0.21 s); `em_adder_ratchet_a` (oneshot, 0.35 s); `em_adder_ratchet_b` (oneshot, 0.35 s); `em_adding_crank` (phrase, 2.55 s); `em_calc_mech_a` (oneshot, 0.11 s); `em_calc_mech_loop` (loop, 3.00 s); `em_cash_register_a` (oneshot, 0.27 s); `em_cash_register_b` (oneshot, 2.17 s); `em_cash_register_c` (oneshot, 0.98 s); `em_energy_meter_loop` (loop, 3.00 s); `em_time_clock_a` (oneshot, 1.53 s); `em_time_clock_b` (oneshot, 0.77 s); `ems_adding_machine_pull` [synth] (oneshot, 0.58 s); `ems_calculator_division` [synth] (loop, 3.00 s); `ems_cash_register` [synth] (phrase, 1.75 s); `ems_punch_clock` [synth] (oneshot, 0.81 s).

**Bells and buzzers.**

`em_bell_ding` (phrase, 1.35 s, root ~F5 (692 Hz, yin)); `em_buzzer_clock_loop` (loop, 1.99 s, root: none found); `em_electric_bell_a` (oneshot, 1.51 s, root ~D#6 (1235 Hz, yin)); `em_electric_bell_loop` (loop, 2.00 s, root ~C8 (4214 Hz, fft peak)); `em_service_bell` (phrase, 6.93 s, root ~C#8 (4526 Hz, fft peak)); `em_signal_bell` (phrase, 4.32 s, root ~A#6 (1883 Hz, yin)); `emh_tty_bell_fm` [hybrid] (oneshot, 3.00 s); `ems_crushed_tty_bell` [synth] (oneshot, 0.64 s, root ~F#6 (1477 Hz, yin)); `ems_fm_register_bell_c6` [synth] (oneshot, 1.71 s, root C6 (label)); `ems_ttybell_g5` [synth] (oneshot, 1.67 s, root G5 (label)).

**Motors, drones, computers, tonal synthesis.**

`em_computer_1960s_loop` (loop, 3.00 s); `em_computer_console_loop` (loop, 3.00 s); `em_machine_fast_loop` (loop, 3.00 s); `em_motor_hum_small_loop` (loop, 3.00 s, root ~B1 (60 Hz, yin)); `em_news_keyer` (phrase, 2.91 s, root ~G5 (764 Hz, yin)); `em_office_machines_a` (oneshot, 0.05 s); `em_office_machines_loop` (loop, 3.00 s); `emh_crossbar_gong_c3` [hybrid] (oneshot, 3.50 s, root C3 (label)); `emh_relay_ping_e5` [hybrid] (oneshot, 1.19 s, root E5 (label)); `emh_typewriter_ks` [hybrid] (oneshot, 1.80 s, root D4 (label)); `ems_704_vowel_a3` [synth] (oneshot, 2.50 s, root A3 (label)); `ems_csirac_pulse_e4` [synth] (oneshot, 2.50 s, root E4 (label)); `ems_ferranti_hoot_c4` [synth] (oneshot, 2.50 s, root C4 (label)); `ems_fm_sounder_c4` [synth] (oneshot, 0.92 s, root C4 (label)); `ems_ks_spring_g3` [synth] (oneshot, 2.50 s, root G3 (label)); `ems_ks_wire_c3` [synth] (oneshot, 3.00 s, root C3 (label)); `ems_motor_drone_c3` [synth] (oneshot, 4.00 s, root C3 (label)); `ems_motor_whine_a4` [synth] (oneshot, 4.00 s, root A4 (label)); `ems_relay_mallet_c5` [synth] (oneshot, 1.52 s, root C5 (label)); `ems_relay_marimba_c4` [synth] (oneshot, 0.92 s, root C4 (label)); `ems_ringmod_relay_bell` [synth] (oneshot, 1.03 s).


"kind": `oneshot` is a single hit, `loop` a steady section cut where the 100 ms RMS varies least (`no_trim`, so it
keeps its length), `phrase` a whole event or sequence. Tonal roots are the build's YIN estimate (a spectral peak
for short sounds), or the generator's label. Roots of noisy recordings are rough; the preset designs fold high
roots into the keyboard range by octaves.

How the slices were cut: the onset detector in the lane's scratch tools (`~/em-work/autoslice.py`, not in the
repo) takes the strongest isolated transients (quiet for 40 ms before, at least 8 to 14 dB below the hit; the
slice ends where the hit falls 35 dB or to the noise floor), keeps them at least 150 ms apart, and picks loop
windows by least RMS variation. Counts per source were then pruned by hand to keep the total near 150.

## 12. Synthesized sources

`library/tools/synth_sources.py` renders 100 sounds and 8 hybrids at 44.1 kHz. Each sound is seeded with the
crc32 of its id, so the output is the same on every run. `--list` prints them all. The methods:

### 12.1 The solenoid model (actuators)

The plunger (armature) moves in mm and seconds between a back stop (0) and the pole face (1 mm):

```
a = pull * coil(t) / (1 - x + g0)^2  -  preload  -  k x  -  damp v
coil(t): rises with tau_on while energized, decays with tau_off after the drive stops (the release delay)
at each stop: v -> -e v  (restitution e_front, e_back), a hit is recorded with its speed; below vmin it sticks
```

Each recorded impact excites a **modal bank** chosen for the part: front-stop modes for the pole face, back-stop
modes for the release, and frame modes for the body. Velocity scales the level and the brightness. Changing the
parameters gives every actuator in the collection:

| Parameter | Effect | Used for |
|---|---|---|
| `pull`, `g0` | how hard and fast the armature closes; the 1/gap² law makes the last 10 % violent | tiny reed relay (high pull) to contactor (low pull, heavy modes) |
| `e_front`, `e_back` | the bounce train (0.25 dull to 0.6 long chatter) | `ems_relay_bouncy` |
| `preload`, `k` | return speed: how bright the release is | release slices |
| `tau_on`, `tau_off` | coil rise and release delay | contactors (slow), print hammers (fast) |
| `on` | drive length: separates pull and release into a pair | `ems_relay_pair`, `part="pull"` / `"release"` |

Attack and release are separate files (`ems_relay_pull` / `ems_relay_release`, `ems_contactor_pull` /
`ems_contactor_release`, crossbar select / release, Strowger step / release), as the owner asked. Chatter comes
from many runs (`ems_relay_rack_chatter`) or from an impact per AC half-cycle (`ems_relay_buzz_ac`).

### 12.2 The other methods

| Method | How | Sounds |
|---|---|---|
| modal | sums of decaying partials struck by band-limited clicks; banks for relays, hammers, typebars, platens, steppers, punches, cabinets, flaps, flip-discs and sounders; bells with shell (1 : 2.61 : 4.86 : 7.68 : 10.9) and church (hum, prime, tierce, quint, nominal) ratios; free-free and undercut bars | bells, mallets, sounders, typebars, escapement, split-flap |
| ks | Karplus-Strong, vectorized per delay block, with a pick-position comb | contact spring, governor spring, the typewriter hybrid |
| fm | two operators with a decaying index | register bell, sounder tone, Bell 103 lead, the FM bell over a teletype |
| additive | harmonic and inharmonic partial stacks, motor models (2x-mains hum, shaft partials, gear whine, bearing noise, spin-up and spin-down) | drum memory, motors, gear whine, call-progress tones |
| fsk | phase-continuous FSK: Bell 103 originate and answer, Bell 202, ITA2 Baudot RTTY at 45.45 baud with 1.5 stop bits, a 2100 Hz answer tone with 450 ms phase reversals, a sketched handshake, an acoustic coupler (carbon-mic band and saturation) | line and modem |
| line | mains hum with odd harmonics, 50 Hz magnetostriction buzz, band-limited hiss, crackle (Pareto-sized clicks), dropouts with clicks, crosstalk (a glottal pulse train through moving formants, band-limited), line hits, pulse-dial breaks at 10 pps 61/39 | the Line kit |
| ringmod / bitcrush | ring modulation; sample-and-hold plus bit reduction; the Ferranti 240 µs period quantization; CSIRAC one-sample pulses | lo-fi bells, computer-music voices |
| phrase | event sequences built from the models: message received (bell, motor start, two lines with CR/LF), print bursts, tape punch, keypunch duplication, sorter and tabulator rhythms at authentic rates, line-printer lines and pages, split-flap boards, flip-disc wipes, telegraph 'CQ', modem connect | the Message Center kit |
| hybrid | a converted recording plus a synthesized layer: relay click + E5 bar ping, crossbar kiss-off + C3 gong, recorded teletype + FM bell, typewriter key + KS tail, rotary dial x 220 Hz ring mod, dial-up modem bitcrushed + hum, stamp + modelled punch thud, switchboard relays + 50 Hz drone | `emh_*` |

## 13. Presets and kits

All designs are in `research/electromech-presets.json`. Every DNA was checked with the design/v3 parser
(`parse3`, `canonical3`) linked against main's `core/dna.cpp` (`-DCORE_KEEPS=1`), with the whole library name list
loaded: every source and Insert File name resolves, every pad's layer and segment exist, every DNA is at most 1024
bytes and is already in canonical form. 52 DNAs, 0 errors. Each kit uses all 16 recorders; strips stay under the
30 s buffer limit.

### 13.1 Instruments (40, DNA v2)

K is the root of the first pitched layer (folded into C1..C6 by octaves); other pitched layers get T so that they
are in tune; unpitched layers (clicks, motors, noise) are `F`.

| Category | Name | DNA (v2) | What it is |
|---|---|---|---|
| Mallets | Relay Mallet | `ems_relay_mallet_c5#12/ems_relay_pull#4L55Q-25F;K72A0R450V90` | A relay armature striking a tuned steel bar; the modelled pull-in click rides on every note. |
| Mallets | Relay Marimba | `ems_relay_marimba_c4#12U2~4/ems_relay_release#4L40Q25F;R350V95` | Undercut-bar ratios struck by a relay; the release tick follows as a second, softer click. |
| Mallets | Relay Ping | `emh_relay_ping_e5#14U2~6;K76R500V90` | Hybrid: a recorded relay click plus a tuned resonator ping. |
| Mallets | Strowger Glock | `ems_relay_mallet_c5#10H0,12L80/ems_stepper_step#6L45F;K72R600` | Octave-doubled steel bar with a stepping-switch 'chunk' as the mallet. |
| Mallets | Crossbar Gong | `emh_crossbar_gong_c3#12/ems_crossbar_select#4L50O0F;K48R1500V80` | Hybrid: a crossbar operation with a struck gong body tuned to the key. |
| Bells | Teletype Bell Keyboard | `ems_ttybell_g5#12/ems_selector_magnet#4L45F;K79R900V85` | The BEL bell as a keyboard; each note is preceded by the selector magnet's code clicks. |
| Bells | Exchange Ringer | `ems_exchange_bell_c4#12H0,12L85/ems_relay_pull#4L35F;R1800V80` | Subscriber-set gong partials, octave-doubled, with the ringer relay's pull. |
| Bells | Register Drawer Bell | `ems_fm_register_bell_c6#10/em_adder_drawer_a#6L50Q30F;K84R700V90` | FM drawer bell with a recorded drawer/mechanism hit. |
| Bells | Typewriter Bell Keys | `em_typewriter_bell_b#12;K73R600V90` | A recorded typewriter margin bell, key-tracked. |
| Bells | Margin Bell Lo-Fi | `ems_crushed_tty_bell#10U2~8/ems_typebar#6L40F;K78R700` | Bitcrushed teletype bell over a typebar strike. |
| Bells | GPO Alarm Bell | `em_gpo_alarm_bell#8Ja0,100.4000,80;R600V70` | The exchange alarm bell from the 1933 GPO film, playable as a sustained pitched bell. |
| Bells | Signal Bell | `em_signal_bell#12/ems_clutch_trip#4L30F;K82R1200` | A recorded signal bell with a clutch-trip click. |
| Bells | Phone Ring Keys | `em_ring_we500#12Ja0,100.1500,70;K80R500V80` | Western Electric 500 ringer as a pitched trill. |
| Leads | Line Printer Lead | `ems_lineprinter_tone_a3#12/ems_print_hammer#4L45F;K57A5R180V80` | Hammer volleys repeating at the note's rate (1403 'music'); a single hammer adds the attack. |
| Leads | 1403 Chorus | `ems_lineprinter_tone_a3#16H0,12U2~12;K57A20R300V70` | Octave-stacked, detuned printer-hammer buzz. |
| Leads | Ferranti Hoot | `ems_ferranti_hoot_c4#16;A3R60V60` | Square pulses quantized to a 240 us beat, the Mark 1's out-of-tune hoot. |
| Leads | CSIRAC Pulse | `ems_csirac_pulse_e4#16;K64A2R80V60` | One-sample speaker pulses from a timing loop, crushed to 4 bits. |
| Leads | Modem Lead | `ems_fm_bell103_lead#12U2~10;K56A10R200` | FM built from the Bell 103 mark/space pair, through a telephone band. |
| Leads | RTTY Carrier Lead | `ems_rtty_idle#12;K84A20R150V70` | The steady RTTY mark carrier as a pure, drifting lead. |
| Leads | Morse Buzzer Lead | `em_morse_buzzer_a#14;A5R100V60` | A recorded Morse practice buzzer, key-tracked. |
| Leads | Modem Beep Lead | `em_modem_beep#16;K76R80V70` | A recorded modem beep. |
| Voices | 1961 Vowel | `ems_704_vowel_a3#12U3~8;K57A40R400V70` | Buzz source through 'ah' formants, a nod to the IBM 7094's 'Daisy Bell'. |
| Plucks | Contact Spring | `ems_ks_spring_g3#12U2~5/ems_relay_release#4L35F;K55R350V90` | Karplus-Strong relay contact spring with a release tick. |
| Plucks | Governor Spring Bass | `ems_ks_wire_c3#12/ems_rotary_dial@10]#4L25F;K48R300V90` | A long, dark Karplus-Strong spring; a slice of the dial's wind-up for the attack. |
| Plucks | Typewriter Pluck | `emh_typewriter_ks#14;K62R400V95` | Hybrid: a recorded typewriter key with a plucked spring tail. |
| Keys | Sounder Keys | `ems_fm_sounder_c4#12/ems_telegraph_sounder#4L50F;R300V90` | A hollow FM tone with the sounder's click/clack on every key. |
| Keys | Tabulator Arp | `ems_relay_mallet_c5#4/ems_relay_mallet_c5#4O133Q-40T7/ems_relay_mallet_c5#4O267Q40T12/ems_tabulator_cycle#4L55F;K72R250V90` | One key plays a three-step arpeggio (root, fifth, octave) at the 407's 150-per-minute cycle (133 ms steps), over the tabulator's own cycle. The transposes of layers 2 and 3 are set below. |
| Drones | Drum Memory Drone | `ems_drum_memory#10Ja0,0.300,100;K56R900V50` | Drum whine, bearing hiss and head-select relays (IBM 650 drum at 12,500 rpm). |
| Drones | Motor Room | `ems_motor_drone_c3#10U2~10Ja0,0.600,100/ems_tty_motor#6L35Ja0,0.800,100F;K48R1200V40` | Additive motor drone tuned to the key, over a teletype motor bed. |
| Drones | Gear Whine Pad | `ems_motor_whine_a4#16U4~18Ja0,0.800,100;K69R1500V40` | Gear and capstan whine with speed hunting, four-voice unison. |
| Drones | Hum Bass | `ems_mains_hum#8Ja0,0.30,100/ems_line_crackle#4L25F;K35R200V60` | 60 Hz line hum and its odd harmonics as a bass; crackle underneath. |
| Drones | Transformer Bass | `ems_hum_buzz_50#12Ja0,0.40,100;K31R250V60` | 50 Hz magnetostriction buzz as a growling bass. |
| Drones | Tube Hum Pad | `em_hum_tube_loop#12U2~12Ja0,0.500,100;K35R900V40` | A recorded tube-radio hum, key-tracked. |
| Drones | Electric Bell Drone | `em_electric_bell_loop#10Ja0,0.200,100;K84R500V50` | A recorded trembler bell as a pitched, buzzing drone. |
| Pads | Dial Tone Organ | `ems_dial_tone#10Ja0,0.60,100/ems_ringmod_dial_tone#6L50Q40;K69R400V40` | 350 + 440 Hz dial tone as an organ, with a ring-modulated copy. |
| Pads | Switchroom Pad | `emh_switchroom_drone#8Ja0,0.900,100F/ems_motor_drone_c3#8L60Ja0,0.1200,100;K48R1500V30` | Hybrid switchboard relays over a 50 Hz drone, with a pitched motor pad. |
| FX | Newsroom | `ems_tty_burst#8Ja0,0.200,100Q-40F/em_tty_machine_loop#8L70Q40F;R800V60` | Two teletypes printing, one synthetic and one recorded, panned apart. |
| FX | Relay Rain | `ems_relay_rack_chatter#8U2~30Q-50F/em_relays_fast_loop#8Q50L80F;R600V70m1=0m11Q-100,100m12Q100,-100` | A rack of relays operating, wide. Mod wheel (macro 1) swings the pan. |
| FX | Digital Trunk | `emh_modem_crush#8Q-30F/ems_crushed_line_noise#8L60Q30F;R400V60` | Hybrid: a recorded dial-up handshake bitcrushed to 4 bits, over crushed line noise. |
| FX | Party Line | `ems_crosstalk#6F/ems_line_crackle#5L80F/ems_mains_hum#5L40;K35R500V50m1=30m11L20,200m12L20,200` | Crosstalk murmur, crackle and hum: a noisy party line. The hum layer follows the key. |

### 13.2 Pioneer kits (12, DNA v3 kit mode, PRESET-ENGINE-2.md §15.2)

Most pads are fixed pitch (`p0`, the default). A few are pitched in a limited range (`p100w<n>`, root folded to
the octave nearest the pad's keys). Loops are gated (`g`) and share cut groups, so a new loop replaces the old
one. In Message Center, the CR pad mutes the print burst (`u1`), and the card-out pad stops the tape punch
(`u2`). Velocity layers: in the Relay Room and Solenoid Lab, key 38 plays a plain pull when soft and a bouncy pull when
hard (`y`). The Typing Pool's key 40 is a three-way random Selectric (`z`).

### Relay Room

Zuse/Bell Labs relay racks: pull and release pairs as velocity layers, chatter loops in a cut group, a pitched relay mallet on the upper keys.

| Keys | Pad | Pitched | Token |
|---|---|---|---|
| 36 | Contactor pull (`ems_contactor_pull`) |  | `k36j6` |
| 37 | Contactor release (`ems_contactor_release`) |  | `k37j7` |
| 38 | Relay pull (soft) (`ems_relay_pull`) |  | `k38j1y1,100` |
| 38 | Relay pull (hard, bouncy) (`ems_relay_bouncy`) |  | `k38j4i120y101,127` |
| 39 | Relay release (`ems_relay_release`) |  | `k39j2` |
| 40 | Relay operate+release (`ems_relay_pair`) |  | `k40j3` |
| 41 | Miniature relay (`ems_relay_tiny`) |  | `k41j5` |
| 42 | Relay click A (`em_relay_click_a`) |  | `k42j8h70` |
| 43 | Relay click B (`em_relay_click_b`) |  | `k43j9h130` |
| 44 | High-speed relay (`em_relay_hs_a`) |  | `k44j10` |
| 45 | Large relay (`em_relay_large_a`) |  | `k45j11` |
| 46 | Contactor (rec) (`em_contactor_a`) |  | `k46j12` |
| 47 | Rack chatter (held) (`ems_relay_rack_chatter`) |  | `k47l2gc1` |
| 48 | AC relay buzz (held) (`ems_relay_buzz_ac`) |  | `k48l3gc1` |
| 60,72 | Relay mallet (pitched, +-12) (`ems_relay_mallet_c5`) | yes | `k60,72l4r72p100w12` |

DNA (477 bytes):

```
ems_relay_pull@t30000Iems_relay_release@t30000Iems_relay_pair@t30000Iems_relay_bouncy@t30000Iems_relay_tiny@t30000Iems_contactor_pull@t30000Iems_contactor_release@t30000Iem_relay_click_a@t30000Iem_relay_click_b@t30000Iem_relay_hs_a@t30000Iem_relay_large_a@t30000Iem_contactor_a#10/ems_relay_rack_chatter#2/ems_relay_buzz_ac#2/ems_relay_mallet_c5#2;R200V90k36j6k37j7k38j1y1,100k38j4i120y101,127k39j2k40j3k41j5k42j8h70k43j9h130k44j10k45j11k46j12k47l2gc1k48l3gc1k60,72l4r72p100w12
```

### Card Room

Hollerith to IBM 407: keypunch, card feed and stacker, tabulator cycle, sorter run, Hollerith bell. Loops are gated in one cut group.

| Keys | Pad | Pitched | Token |
|---|---|---|---|
| 36 | Tabulator cycle (`ems_tabulator_cycle`) |  | `k36j5` |
| 37 | Stacker thump (`ems_card_stack`) |  | `k37j3` |
| 38 | Keypunch column (`ems_card_punch_col`) |  | `k38j1` |
| 39 | Punch magnet (`ems_punch_magnet`) |  | `k39j4` |
| 40 | Card feed (`ems_card_feed`) |  | `k40j2` |
| 41 | Clutch trip (`ems_clutch_trip`) |  | `k41j9` |
| 42 | Ratchet (`em_adder_ratchet_a`) |  | `k42j8` |
| 43 | Adding machine pull (`ems_adding_machine_pull`) |  | `k43j7` |
| 44 | Paper (`em_papertape_a`) |  | `k44j6` |
| 46 | Duplicating (held) (`ems_card_punch_dup`) |  | `k46l2gc1` |
| 47 | Sorter 1000/min (held) (`ems_sorter_run`) |  | `k47l3gc1` |
| 48 | 407 report run (held) (`ems_tabulator_run`) |  | `k48l4gc1` |
| 72,79 | Hollerith counter bell (pitched, +-4) (`ems_typewriter_bell`) | yes | `k72,79j10r79p100w4` |

DNA (397 bytes):

```
ems_card_punch_col@t30000Iems_card_feed@t30000Iems_card_stack@t30000Iems_punch_magnet@t30000Iems_tabulator_cycle@t30000Iem_papertape_a@t30000Iems_adding_machine_pull@t30000Iem_adder_ratchet_a@t30000Iems_clutch_trip@t30000Iems_typewriter_bell#10/ems_card_punch_dup#2/ems_sorter_run#2/ems_tabulator_run#2;R200V90k36j5k37j3k38j1k39j4k40j2k41j9k42j8k43j7k44j6k46l2gc1k47l3gc1k48l4gc1k72,79j10r79p100w4
```

### Teletype 33

A Model 33 ASR as a kit: characters, CR, LF, bell, motor start and stop (one cut group), print bursts and the tape punch.

| Keys | Pad | Pitched | Token |
|---|---|---|---|
| 36 | Carriage return (`ems_tty_cr`) |  | `k36j2` |
| 37 | Line feed (`ems_tty_lf`) |  | `k37j3` |
| 38 | Character (`ems_tty_char`) |  | `k38j1` |
| 39 | Print hit (rec) (`em_tty_machine_hit_a`) |  | `k39j7` |
| 40 | Print hit B (rec) (`em_tty_machine_hit_b`) |  | `k40j8` |
| 41 | Selector magnet (`ems_selector_magnet`) |  | `k41j4` |
| 42 | Typebar (`ems_typebar`) |  | `k42j6` |
| 44 | Motor start (`ems_tty_motor_start`) |  | `k44l2c2` |
| 45 | Motor stop (`ems_tty_motor_stop`) |  | `k45l3c2` |
| 46 | Print burst (held) (`ems_tty_burst`) |  | `k46l4gc1` |
| 47 | Tape punch (held) (`ems_tape_punch_burst`) |  | `k47l5gc1` |
| 72,84 | BEL (pitched, +-7) (`ems_tty_bell`) | yes | `k72,84j5r78p100w7` |

DNA (344 bytes):

```
ems_tty_char@t30000Iems_tty_cr@t30000Iems_tty_lf@t30000Iems_selector_magnet@t30000Iems_tty_bell@t30000Iems_typebar@t30000Iem_tty_machine_hit_a@t30000Iem_tty_machine_hit_b#9/ems_tty_motor_start#2/ems_tty_motor_stop#1/ems_tty_burst#2/ems_tape_punch_burst#2;R200V90k36j2k37j3k38j1k39j7k40j8k41j4k42j6k44l2c2k45l3c2k46l4gc1k47l5gc1k72,84j5r78p100w7
```

### Message Center

Arrive, store, display: each row of keys is one event phrase broken into its parts. C2 row arrive (bell, motor, print, CR, LF), C3 row store (punch, card, drum, tape), C4 row display (line printer, split-flap, flip-disc, Selectric), C5 whole phrases.

| Keys | Pad | Pitched | Token |
|---|---|---|---|
| 36 | Arrive: bell (`ems_tty_bell`) |  | `k36j1` |
| 37 | Arrive: motor start (`ems_tty_motor_start`) |  | `k37j13` |
| 38 | Arrive: character (`ems_tty_char`) |  | `k38j2` |
| 39 | Arrive: print burst (held) (`ems_tty_burst`) |  | `k39l2gc1` |
| 40 | Arrive: CR (stops the burst) (`ems_tty_cr`) |  | `k40j3u1` |
| 41 | Arrive: LF (`ems_tty_lf`) |  | `k41j4` |
| 48 | Store: tape punch (held) (`ems_tape_punch_burst`) |  | `k48l3gc2` |
| 49 | Store: card feed (`ems_card_feed`) |  | `k49j6` |
| 50 | Store: punch column (`ems_card_punch_col`) |  | `k50j5` |
| 51 | Store: card out (`ems_card_stack`) |  | `k51j7u2` |
| 52 | Store: drum write (`ems_drum_write`) |  | `k52j8` |
| 60 | Display: printer line (`ems_lineprinter_line`) |  | `k60j9` |
| 61 | Display: split-flap (`ems_splitflap`) |  | `k61j10` |
| 62 | Display: flip-disc (`ems_flipdot`) |  | `k62j11` |
| 63 | Display: Selectric (`ems_selectric_char`) |  | `k63j12` |
| 64 | Display: printer page (held) (`ems_lineprinter_page`) |  | `k64l8gc3` |
| 65 | Display: split-flap (rec) (`em_splitflap_a`) |  | `k65j14` |
| 72 | Phrase: message received (`ems_tty_message_received`) |  | `k72l4c4` |
| 73 | Phrase: modem connect (`ems_modem_handshake`) |  | `k73l7c4` |
| 74 | Phrase: board update (`ems_splitflap_board`) |  | `k74l5c4` |
| 75 | Phrase: sign rewrite (`ems_flipdot_wipe`) |  | `k75l6c4` |
| 84,96 | Arrive: bell (pitched, +-6) (`ems_tty_bell`) | yes | `k84,96j1r90p100w6` |

DNA (612 bytes):

```
ems_tty_bell@t30000Iems_tty_char@t30000Iems_tty_cr@t30000Iems_tty_lf@t30000Iems_card_punch_col@t30000Iems_card_feed@t30000Iems_card_stack@t30000Iems_drum_write@t30000Iems_lineprinter_line@t30000Iems_splitflap@t30000Iems_flipdot@t30000Iems_selectric_char@t30000Iems_tty_motor_start@t30000Iem_splitflap_a#9/ems_tty_burst#1/ems_tape_punch_burst#1/ems_tty_message_received#1/ems_splitflap_board#1/ems_flipdot_wipe#1/ems_modem_handshake#1/ems_lineprinter_page#1;R150V85k36j1k37j13k38j2k39l2gc1k40j3u1k41j4k48l3gc2k49j6k50j5k51j7u2k52j8k60j9k61j10k62j11k63j12k64l8gc3k65j14k72l4c4k73l7c4k74l5c4k75l6c4k84,96j1r90p100w6
```

### Line

The telephone line: call-progress tones (one cut group, so a new tone replaces the last), pulse dialling, ringers, modem and RTTY tones, and the noises (hum, hiss, crackle, dropouts, crosstalk, hits).

| Keys | Pad | Pitched | Token |
|---|---|---|---|
| 36 | Off-hook relay (`ems_relay_pull`) |  | `k36j5` |
| 37 | Hang-up (`em_fetap_hangup`) |  | `k37j4` |
| 38 | Pulse digit 7 (`ems_pulse_dial_digit`) |  | `k38j1` |
| 39 | Rotary dial (`ems_rotary_dial`) |  | `k39l5` |
| 40 | Line hit (`ems_line_hit`) |  | `k40j2` |
| 41 | Switch click (`em_switchboard_click_a`) |  | `k41j6` |
| 42 | Dial tone (held) (`ems_dial_tone`) |  | `k42l2j1gc1` |
| 43 | Ring-back (held) (`ems_ringback`) |  | `k43l2j2gc1` |
| 44 | Busy (held) (`ems_busy`) |  | `k44l2j3gc1` |
| 45 | Reorder (held) (`ems_reorder`) |  | `k45l2j4gc1` |
| 46 | SIT tones (`ems_sit_tones`) |  | `k46j3c1` |
| 47 | Ringer (`ems_phone_ring_trill`) |  | `k47l6c2` |
| 48 | Hiss (held) (`ems_line_hiss`) |  | `k48l3j1gc3` |
| 49 | Crackle (held) (`ems_line_crackle`) |  | `k49l3j2gc3` |
| 50 | Dropouts (held) (`ems_line_dropout`) |  | `k50l3j3gc3` |
| 51 | Crosstalk (held) (`ems_crosstalk`) |  | `k51l3j4gc3` |
| 52 | Hum (held) (`ems_mains_hum`) |  | `k52l3j5gc3` |
| 53 | Bell 103 originate (held) (`ems_fsk_bell103_orig`) |  | `k53l4j1gc4` |
| 54 | Bell 103 answer (held) (`ems_fsk_bell103_ans`) |  | `k54l4j2gc4` |
| 55 | Answer tone 2100 (held) (`ems_modem_answer_tone`) |  | `k55l4j3gc4` |
| 56 | RTTY (held) (`ems_rtty_baudot`) |  | `k56l4j4gc4` |
| 57 | Modem beep (`em_modem_beep`) |  | `k57j7` |
| 58 | Dial-up (rec) (`em_modem_dialup`) |  | `k58l7c4` |
| 60,72 | Hum (pitched, held) (`ems_mains_hum`) | yes | `k60,72l3j5r71p100w12gc3` |

DNA (713 bytes):

```
ems_pulse_dial_digit@t30000Iems_line_hit@t30000Iems_sit_tones@t30000Iem_fetap_hangup@t30000Iems_relay_pull@t30000Iem_switchboard_click_a@t30000Iem_modem_beep#6/ems_dial_tone@t30000Iems_ringback@t30000Iems_busy@t30000Iems_reorder#2/ems_line_hiss@t30000Iems_line_crackle@t30000Iems_line_dropout@t30000Iems_crosstalk@t30000Iems_mains_hum#3/ems_fsk_bell103_orig@t30000Iems_fsk_bell103_ans@t30000Iems_modem_answer_tone@t30000Iems_rtty_baudot#2/ems_rotary_dial#1/ems_phone_ring_trill#1/em_modem_dialup#1;R80V70k36j5k37j4k38j1k39l5k40j2k41j6k42l2j1gc1k43l2j2gc1k44l2j3gc1k45l2j4gc1k46j3c1k47l6c2k48l3j1gc3k49l3j2gc3k50l3j3gc3k51l3j4gc3k52l3j5gc3k53l4j1gc4k54l4j2gc4k55l4j3gc4k56l4j4gc4k57j7k58l7c4k60,72l3j5r71p100w12gc3
```

### Strowger Exchange

A step-by-step office: selector steps, vertical pulses, rotary hunt, release, crossbar and the recorded 500-point selector and switchboard; ringer gong pitched on the top keys.

| Keys | Pad | Pitched | Token |
|---|---|---|---|
| 36 | Switch release (`ems_stepper_release`) |  | `k36j4` |
| 37 | One step (`ems_stepper_step`) |  | `k37j1` |
| 38 | Vertical steps (7) (`ems_stepper_vertical`) |  | `k38j2` |
| 39 | Rotary hunt (`ems_stepper_rotary_hunt`) |  | `k39j3` |
| 40 | Crossbar select+hold (`ems_crossbar_select`) |  | `k40j5` |
| 41 | Crossbar release (`ems_crossbar_release`) |  | `k41j6` |
| 42 | Kiss-off (rec) (`em_crossbar_kissoff`) |  | `k42j7` |
| 43 | 500-selector run (rec) (`em_selector500_a`) |  | `k43j8` |
| 44 | 500-selector hit (rec) (`em_selector500_b`) |  | `k44j9` |
| 45 | Switchboard click (`em_switchboard_click_b`) |  | `k45j10` |
| 46 | Stepping run (rec) (`em_stepper_steps`) |  | `k46j11` |
| 47 | Timing relays (rec) (`em_crossbar_timing_a`) |  | `k47j12` |
| 48 | Switch room (held) (`em_switchboard_relays`) |  | `k48l2g` |
| 60,72 | Ringer gong (pitched, +-6) (`ems_exchange_bell_c4`) | yes | `k60,72l3p100w6` |

DNA (455 bytes):

```
ems_stepper_step@t30000Iems_stepper_vertical@t30000Iems_stepper_rotary_hunt@t30000Iems_stepper_release@t30000Iems_crossbar_select@t30000Iems_crossbar_release@t30000Iem_crossbar_kissoff@t30000Iem_selector500_a@t30000Iem_selector500_b@t30000Iem_switchboard_click_b@t30000Iem_stepper_steps@t30000Iem_crossbar_timing_a#11/em_switchboard_relays#2/ems_exchange_bell_c4#3;R200V90k36j4k37j1k38j2k39j3k40j5k41j6k42j7k43j8k44j9k45j10k46j11k47j12k48l2gk60,72l3p100w6
```

### Telegraph Office

Sounder click/clack, keyed phrases, CW tones, Morse buzzer, ticker, the news keyer and the radio-teletype modes.

| Keys | Pad | Pitched | Token |
|---|---|---|---|
| 36 | Sounder click/clack (`ems_telegraph_sounder`) |  | `k36j1` |
| 37 | Key click (rec) (`em_cw_click_a`) |  | `k37j2` |
| 38 | Ticker tick (`em_ticker_a`) |  | `k38j3` |
| 39 | Ticker print (`em_ticker_b`) |  | `k39j4` |
| 40 | Print (`ems_typebar`) |  | `k40j5` |
| 41 | Sounder 'CQ' (`ems_telegraph_message`) |  | `k41l2c1` |
| 42 | CW 'BSYN' (`ems_morse_cw`) |  | `k42l3c1` |
| 43 | News keyer (`em_news_keyer`) |  | `k43l4c2` |
| 44 | Ticker run (held) (`ems_ticker`) |  | `k44l5gc3` |
| 45 | Hellschreiber (held) (`em_hellschreiber_loop`) |  | `k45l6gc3` |
| 46 | RTTY (held) (`em_rtty_wiki`) |  | `k46l7gc3` |
| 60,72 | Morse buzzer (pitched, held) (`em_morse_buzzer_a`) | yes | `k60,72l8p100w12g` |

DNA (322 bytes):

```
ems_telegraph_sounder@t30000Iem_cw_click_a@t30000Iem_ticker_a@t30000Iem_ticker_b@t30000Iems_typebar#6/ems_telegraph_message#2/ems_morse_cw#1/em_news_keyer#1/ems_ticker#2/em_hellschreiber_loop#1/em_rtty_wiki#1/em_morse_buzzer_a#2;R200V90k36j1k37j2k38j3k39j4k40j5k41l2c1k42l3c1k43l4c2k44l5gc3k45l6gc3k46l7gc3k60,72l8p100w12g
```

### Calculator Bureau

Comptometers, Fridens and registers: crank pulls, ratchets, division runs, cash register and its bell (pitched), time clock.

| Keys | Pad | Pitched | Token |
|---|---|---|---|
| 36 | Hand crank (rec) (`em_adding_crank`) |  | `k36j2` |
| 37 | Handle pull (`ems_adding_machine_pull`) |  | `k37j1` |
| 38 | Ratchet A (`em_adder_ratchet_a`) |  | `k38j3` |
| 39 | Ratchet B (`em_adder_ratchet_b`) |  | `k39j4` |
| 40 | Mechanism (`em_adder_drawer_a`) |  | `k40j5` |
| 41 | Calculator hit (`em_calc_mech_a`) |  | `k41j6` |
| 42 | Escapement (`ems_escapement`) |  | `k42j10` |
| 43 | Register (rec) (`em_cash_register_a`) |  | `k43j9` |
| 44 | Register sale (`ems_cash_register`) |  | `k44j7c2` |
| 45 | Time clock (`ems_punch_clock`) |  | `k45j8` |
| 46 | Friden division (held) (`ems_calculator_division`) |  | `k46l2gc1` |
| 47 | Calculator run (held) (`em_calc_mech_loop`) |  | `k47l3gc1` |
| 72,84 | Drawer bell (pitched, +-5) (`ems_fm_register_bell_c6`) | yes | `k72,84l4r84p100w5` |

DNA (410 bytes):

```
ems_adding_machine_pull@t30000Iem_adding_crank@t30000Iem_adder_ratchet_a@t30000Iem_adder_ratchet_b@t30000Iem_adder_drawer_a@t30000Iem_calc_mech_a@t30000Iems_cash_register@t30000Iems_punch_clock@t30000Iem_cash_register_a@t30000Iems_escapement#11/ems_calculator_division#2/em_calc_mech_loop#1/ems_fm_register_bell_c6#2;R200V90k36j2k37j1k38j3k39j4k40j5k41j6k42j10k43j9k44j7c2k45j8k46l2gc1k47l3gc1k72,84l4r84p100w5
```

### Typing Pool

Typebars, Selectric, electric and daisy-wheel machines, margin bells, carriage returns.

| Keys | Pad | Pitched | Token |
|---|---|---|---|
| 36 | Carriage slam (`ems_tty_cr`) |  | `k36j11` |
| 37 | Margin release (`em_typewriter_return_a`) |  | `k37j7` |
| 38 | Typebar key (rec) (`em_typewriter_key_a`) |  | `k38j1` |
| 39 | Typebar (model) (`ems_typebar`) |  | `k39j5` |
| 40 | Selectric (random) (`em_selectric_key_a`) |  | `k40j2z` |
| 40 | Selectric (random) (`em_selectric_key_b`) |  | `k40j3z` |
| 40 | Selectric (random) (`em_selectric_key_c`) |  | `k40j4z` |
| 41 | Selectric (model) (`ems_selectric_char`) |  | `k41j6` |
| 42 | Daisy wheel (`em_daisywheel_a`) |  | `k42j10` |
| 43 | Margin bell A (`em_typewriter_bell_a`) |  | `k43j8` |
| 44 | Margin bell C (`em_typewriter_bell_c`) |  | `k44j9` |
| 45 | Bell + return (`em_typewriter_bell_return`) |  | `k45j12` |
| 46 | Selectric typing (held) (`em_selectric_typing_loop`) |  | `k46l2gc1` |
| 47 | Electric typing (held) (`em_etypewriter_loop`) |  | `k47l3gc1` |
| 72,84 | Margin bell (pitched) (`em_typewriter_bell_b`) | yes | `k72,84l4r73p100w5` |

DNA (484 bytes):

```
em_typewriter_key_a@t30000Iem_selectric_key_a@t30000Iem_selectric_key_b@t30000Iem_selectric_key_c@t30000Iems_typebar@t30000Iems_selectric_char@t30000Iem_typewriter_return_a@t30000Iem_typewriter_bell_a@t30000Iem_typewriter_bell_c@t30000Iem_daisywheel_a@t30000Iems_tty_cr@t30000Iem_typewriter_bell_return#12/em_selectric_typing_loop#1/em_etypewriter_loop#1/em_typewriter_bell_b#2;R200V90k36j11k37j7k38j1k39j5k40j2zk40j3zk40j4zk41j6k42j10k43j8k44j9k45j12k46l2gc1k47l3gc1k72,84l4r73p100w5
```

### Mainframe Hall

1950s-60s machine room: line printer, vacuum-column tape, drum memory, card reader, and the first computer-music voices (Ferranti hoot, CSIRAC pulse) pitched on the top keys.

| Keys | Pad | Pitched | Token |
|---|---|---|---|
| 36 | Printer line (`ems_lineprinter_line`) |  | `k36j1` |
| 37 | Hammer (`ems_print_hammer`) |  | `k37j2` |
| 38 | Drum write (`ems_drum_write`) |  | `k38j3` |
| 39 | Card feed (`ems_card_feed`) |  | `k39j4` |
| 40 | Relay (`ems_relay_pull`) |  | `k40j5` |
| 41 | Dot-matrix hit (`em_dotmatrix_hit_a`) |  | `k41j6` |
| 42 | Tape reader (held) (`ems_tape_reader`) |  | `k42j7gc1` |
| 43 | Printer page (held) (`ems_lineprinter_page`) |  | `k43l2gc1` |
| 44 | Tape drive (held) (`ems_tape_drive_shuttle`) |  | `k44l3gc2` |
| 45 | Drum (held) (`ems_drum_memory`) |  | `k45l4gc2` |
| 46 | Dot-matrix burst (held) (`em_dotmatrix_burst_a`) |  | `k46l5gc1` |
| 60,71 | Ferranti hoot (pitched, held) (`ems_ferranti_hoot_c4`) | yes | `k60,71l6p100w12g` |
| 72,84 | CSIRAC pulse (pitched, held) (`ems_csirac_pulse_e4`) | yes | `k72,84l7r76p100w12g` |

DNA (407 bytes):

```
ems_lineprinter_line@t30000Iems_print_hammer@t30000Iems_drum_write@t30000Iems_card_feed@t30000Iems_relay_pull@t30000Iem_dotmatrix_hit_a@t30000Iems_tape_reader#8/ems_lineprinter_page#1/ems_tape_drive_shuttle#1/ems_drum_memory#1/em_dotmatrix_burst_a#1/ems_ferranti_hoot_c4#2/ems_csirac_pulse_e4#2;R200V90k36j1k37j2k38j3k39j4k40j5k41j6k42j7gc1k43l2gc1k44l3gc2k45l4gc2k46l5gc1k60,71l6p100w12gk72,84l7r76p100w12g
```

### Signal Bells

Bells of the machine age: BEL, margin bells, trembler and alarm bells, the GPO exchange alarm, ringers, the desk-calculator bell. Most pads fixed; three pitched in a narrow range.

| Keys | Pad | Pitched | Token |
|---|---|---|---|
| 36 | Signal bell (`em_signal_bell`) |  | `k36j6` |
| 37 | Trembler bell (`em_electric_bell_a`) |  | `k37j5` |
| 38 | Teletype BEL (`ems_tty_bell`) |  | `k38j1` |
| 39 | Margin bell A (`em_typewriter_bell_a`) |  | `k39j2` |
| 40 | Margin bell C (`em_typewriter_bell_c`) |  | `k40j3` |
| 41 | Margin bell (model) (`ems_typewriter_bell`) |  | `k41j4` |
| 42 | Time clock bell (`ems_punch_clock`) |  | `k42j7` |
| 43 | FeTAp ring (held) (`em_fetap_ring`) |  | `k43j8gc1` |
| 44 | Twin-gong ringer (held) (`ems_phone_ring_trill`) |  | `k44l3gc1` |
| 45 | GPO alarm (held) (`em_gpo_alarm_bell`) |  | `k45l2gc1` |
| 60,67 | Ringer gong (pitched, +-4) (`ems_exchange_bell_c4`) | yes | `k60,67l5p100w4` |
| 72,84 | BEL keyboard (pitched, +-5) (`ems_ttybell_g5`) | yes | `k72,84l4r79p100w5` |

DNA (370 bytes):

```
ems_tty_bell@t30000Iem_typewriter_bell_a@t30000Iem_typewriter_bell_c@t30000Iems_typewriter_bell@t30000Iem_electric_bell_a@t30000Iem_signal_bell@t30000Iems_punch_clock@t30000Iem_fetap_ring#8/em_gpo_alarm_bell#2/ems_phone_ring_trill#2/ems_ttybell_g5#2/ems_exchange_bell_c4#2;R200V90k36j6k37j5k38j1k39j2k40j3k41j4k42j7k43j8gc1k44l3gc1k45l2gc1k60,67l5p100w4k72,84l4r79p100w5
```

### Solenoid Lab

Actuator physics: the modelled plunger in its variants (pull, release, bounce, tiny, large) beside recorded solenoids, contactors and relays. Pull pads mute the held buzz; release pads answer note-off where gated.

| Keys | Pad | Pitched | Token |
|---|---|---|---|
| 36 | Contactor pull (mutes buzz) (`ems_contactor_pull`) |  | `k36j4u1` |
| 37 | Contactor release (`ems_contactor_release`) |  | `k37j5` |
| 38 | Relay pull (`ems_relay_pull`) |  | `k38j1y1,95` |
| 38 | Relay pull, bouncy (hard) (`ems_relay_bouncy`) |  | `k38j3y96,127` |
| 39 | Relay release (`ems_relay_release`) |  | `k39j2` |
| 40 | Print hammer (`ems_print_hammer`) |  | `k40j6` |
| 41 | Punch magnet (`ems_punch_magnet`) |  | `k41j7` |
| 42 | Flip-disc (`ems_flipdot`) |  | `k42j8` |
| 43 | Stepper (`ems_stepper_step`) |  | `k43j9` |
| 44 | 12 V solenoid (rec) (`em_solenoid12v_a`) |  | `k44j10` |
| 45 | Solenoid switch (rec) (`em_solenoid_sw_a`) |  | `k45j11` |
| 46 | Contactor (rec) (`em_kontaktor_a`) |  | `k46j12` |
| 47 | Large relay (rec) (`em_relay_large_b`) |  | `k47j13` |
| 48 | Metal click (`em_metal_click_a`) |  | `k48j14` |
| 49 | Switch (`em_switch_a`) |  | `k49j15` |
| 50 | Clutch trip (`ems_clutch_trip`) |  | `k50j16` |
| 51 | AC buzz (held) (`ems_relay_buzz_ac`) |  | `k51l2gc1` |
| 52 | Split-flap unit (`ems_splitflap`) |  | `k52l3` |
| 60,64 | Relay pull (pitched, +-2) (`ems_relay_pull`) | yes | `k60,64j1r63p100w2` |

DNA (547 bytes):

```
ems_relay_pull@t30000Iems_relay_release@t30000Iems_relay_bouncy@t30000Iems_contactor_pull@t30000Iems_contactor_release@t30000Iems_print_hammer@t30000Iems_punch_magnet@t30000Iems_flipdot@t30000Iems_stepper_step@t30000Iem_solenoid12v_a@t30000Iem_solenoid_sw_a@t30000Iem_kontaktor_a@t30000Iem_relay_large_b@t30000Iem_metal_click_a@t30000Iem_switch_a@t30000Iems_clutch_trip#12/ems_relay_buzz_ac#2/ems_splitflap#2;R200V90k36j4u1k37j5k38j1y1,95k38j3y96,127k39j2k40j6k41j7k42j8k43j9k44j10k45j11k46j12k47j13k48j14k49j15k50j16k51l2gc1k52l3k60,64j1r63p100w2
```

## 14. Gaps and next steps

- **No authentic recordings of the famous machines.** None of the PD/CC0 sources had a Zuse Z3/Z4 replica, a
  Harvard Mark I, a Bell Labs relay computer, an IBM 026/029 keypunch, an 082/083 sorter, a 407 tabulator, an IBM
  1403 or a vacuum-column tape drive. Those are modelled (sections 12.1 and 12.2) instead. The Computer History
  Museum's 1401/1403 and keypunch demonstrations would fill this gap, but they are not openly licensed. A good next
  step is to ask the museum, or the Hünfeld Zuse museum, for a CC0 release, or to record a working machine.
- **No Curta, Friden, Comptometer or Model 33 recordings** under PD/CC0 were found. The calculator and teletype
  sounds are generic recordings plus models.
- **Prelinger and archive.org films:** only one excerpt was usable. Most films are narration over music; the
  subtitle gaps in *The Coming of the Dial* gave a clean alarm bell, but its switch-room montage has music under
  it. Prelinger films about SAGE, telephones and the 1950s office (`OnGuard1956`, `Telephon1946`,
  `WeLearnA1965`, `Nationat1951`) are candidates for a manual pass by ear.
- **Not checked by ear.** The slices were chosen by onset detection and statistics. Some may hold room noise,
  voices or a double hit; a listening pass should drop or re-cut these. The suspects are `em_selector500_loop`
  (it carries a steady 440 Hz tone), `em_tty_police_loop` (room ambience), `em_typewriter_return_*` (short
  mechanism clicks, not full returns) and `em_office_machines_*`. Roots of noisy tonal recordings are rough.
- **Kit maps are v3 only.** On a v2 machine every layer of a kit sounds on every note (§15.1). Ship them in a
  category with a minimum DNA version of 3. They also need `seg` reporting and choke from the guests (phase 5b).
- **3.11:** these designs need the library disc. Their sounds are not in C:\WINDOWS. The 3.11 library drive
  must carry the `electromech` folder.
- **Not rendered through the real machine.** `tools/batch_render.py` could render each preset with a test score
  for an A/B check against the reference mode; this lane did not launch a VM.

## 15. Sources and further reading

- Konrad Zuse, *Der Computer – mein Lebenswerk* (1970); Raúl Rojas, "Konrad Zuse's legacy: the architecture of
  the Z1 and Z3", *IEEE Annals of the History of Computing* 19(2), 1997.
- I. Bernard Cohen, *Howard Aiken: Portrait of a Computer Pioneer* (MIT Press, 1999); the Harvard Mark I
  operating manual (*A Manual of Operation for the Automatic Sequence Controlled Calculator*, 1946).
- George Stibitz, "Early computers", in Metropolis et al. (eds.), *A History of Computing in the Twentieth
  Century* (1980); the Bell Labs relay computers in E. G. Andrews, "Telephone switching and the early Bell
  Laboratories computers", *Bell System Technical Journal* 42(2), 1963.
- Alice and Arthur Burks, *The First Electronic Computer: The Atanasoff Story* (1988).
- IBM reference manuals: *IBM 024, 026 Card Punch*; *IBM 029 Card Punch*; *IBM 082, 083, 084 Sorters*; *IBM 407
  Accounting Machine*; *IBM 1403 Printer Component Description* (bitsavers.org).
- Teletype Corporation bulletins for the Model 15, 28 and 33; ITA2 (CCITT) and the Telex answerback (WRU).
- *Bell System Technical Journal*: the precise tone plan and the step-by-step, panel and crossbar papers; the Bell
  103 and 202 data-set specifications; the impulse-noise studies of data transmission (early 1960s).
- Jack Copeland and Jason Long, "Restoring the first recording of computer music" (British Library, 2016); Paul
  Doornbusch, *The Music of CSIRAC* (2005); J. L. Kelly, C. Lochbaum, M. V. Mathews, "Daisy Bell" (Bell Labs,
  1961).
- Freesound, Wikimedia Commons and archive.org pages: per entry in `catalog/electromech.json`.
