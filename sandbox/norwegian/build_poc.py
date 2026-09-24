"""Compose a separate product POC from the proven sandbox review controls."""
from pathlib import Path
import re
HERE=Path(__file__).parent
text=(HERE/'index.html').read_text(encoding='utf-8')
text=text.replace('Skrivi · Norsk skriveprøve','Skrivi · Skriv og velg')
text=text.replace('Bokmål · lokal utprøving','Skriv og velg · Bokmål')
text=text.replace('Skriv ferdig tanken. Se på stavemåten etterpå.','Skriv det du vil si. Vi hjelper deg å finne skrivemåten etterpå.')
text=re.sub(r'<select id="mode">.*?</select>', '''<select id="mode">
<option value="nuspell_context" selected>Staving og sammenheng</option>
<option value="nuspell_compounds">Staving, sammenheng og ordgrenser (ny prøve)</option>
<option value="nuspell_rank">Staving med sorterte forslag</option>
<option value="nuspell">Bare stavekontroll</option></select>''',text,count=1)
text=text.replace('<textarea id="text"', '''<div class="tools help-tools"><label for="helpStyle">Ordhjelp:</label><select id="helpStyle"><option value="definition">Kort forklaring</option><option value="synonym">Lignende betydning</option><option value="example">Eksempel først</option></select><button id="stopAudio" disabled>Stopp lyd</button><button id="practiceToggle">Prøv ordhjelpen</button></div>
<p id="audioStatus" class="muted" role="status" aria-live="polite">Undersøker norsk opplesning …</p>
<aside id="practice" class="hidden"><h2>Hvilket ord mener du?</h2><p>Øv på å lese eller høre betydningen. Dette er faste ordpar, ikke et resultat fra stavekontrollen. Teksten din endres ikke.</p><div class="tools"><button data-pair="school" id="pairSchool">lekser / lakser</button><button data-pair="amount" id="pairAmount">mase / masse</button><button data-pair="wish" id="pairWish">gjerne / hjerne</button></div><div id="practiceChoices" class="choice-grid"></div><p id="practiceFeedback" role="status"></p></aside>
<textarea id="text"''')
text=text.replace('<p id="reason"></p>', '<p id="reason"></p><div id="originalHelp"></div>')
text=text.replace('Modellen sjekker ukjente ord og noen vanlige forvekslinger.', 'Kontrollen sammenligner skrivemåter og sammenheng. Den kan overse feil og markere riktige ord.')
text=text.replace('Ingenting lagres automatisk.', 'Ingenting lagres automatisk. Opplesning bruker en norsk stemme på denne maskinen. Ordhjelpen inneholder et lite utvalg betydninger, ikke en full ordbok. Forklaringene er forenklet; eksemplene er laget for denne prøven.')
text=text.replace('</style>', '''
.skipped{border-bottom:2px dashed #778488!important;background:#edf0f2!important}
.choice-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}.audio-actions{display:flex;gap:8px;flex-wrap:wrap}.audio-actions button{font-size:16px;padding:7px 10px}.choice-card .primary{width:100%;margin-top:18px}.hint-label{font-size:14px;color:#53656c;margin-top:12px}.original-help{padding:10px 14px;background:#eef3f2;border-radius:8px;margin:12px 0}.original-help details{margin:4px 0}#practice h2{font-size:23px;margin:0}.help-tools{margin-bottom:0}#audioStatus{min-height:24px}.word:focus-visible,summary:focus-visible{outline:3px solid #496ed0;outline-offset:3px}@media(max-width:600px){main{padding:0 14px;margin:20px auto}header{align-items:flex-start;gap:12px}textarea,#review{padding:15px;font-size:21px}.choice-card{flex-basis:100%}aside{padding:16px}.tools button{min-height:44px}}
</style>''')
text=text.replace('</script></html>', '</script><script src="/poc.js"></script></html>')
(HERE/'poc.html').write_text(text,encoding='utf-8')
