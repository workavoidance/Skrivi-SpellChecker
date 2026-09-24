"""Synthetic development cases and reserved regression cases; no model-generated labels.

Labels specify intended spelling, not every possible interpretation. This is not
representative dyslexia data. Reserve must remain untested until an engine change.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
development = {
'spelling': [
('Hun kommer alerede i morgen.', 'alerede', 'allerede'),
('Vi ventet i femten minuter.', 'minuter', 'minutter'),
('Jeg la brevet i jakkeloma.', 'jakkeloma', 'jakkelomma'),
('Koppen står på kjøkenbordet.', 'kjøkenbordet', 'kjøkkenbordet'),
('Han glemte avtallen vår.', 'avtallen', 'avtalen'),
('Vi spiste frokkost sammen.', 'frokkost', 'frokost'),
('Hun kjøpte en billett på stasjonn.', 'stasjonn', 'stasjonen'),
('Jeg skal besøke tannlegen på torssdag.', 'torssdag', 'torsdag'),
('Det ligger et brev i postkassa mi.', None, None),
('Jeg skrev telefonumeret på en lapp.', 'telefonumeret', 'telefonnummeret'),
('Barnet tegnet en sommerfugel.', 'sommerfugel', 'sommerfugl'),
('Vi trenger mer informasjonn.', 'informasjonn', 'informasjon'),
('Hun hadde glemt passorde sitt.', 'passorde', 'passordet'),
('Jeg har bestilt en legetimme.', 'legetimme', 'legetime'),
('Vi møtes ved bussholdeplasen.', 'bussholdeplasen', 'bussholdeplassen'),
('Jeg fant kviteringen i veska.', 'kviteringen', 'kvitteringen')],
'sound_based': [
('Vi skal på skjino i kveld.', 'skjino', 'kino'),
('Jeg må sjøpe en ny jakke.', 'sjøpe', 'kjøpe'),
('Han kjørte gjennom en tunell.', 'tunell', 'tunnel'),
('Kan du jælpe meg med døra?', 'jælpe', 'hjelpe'),
('Hun kjøpte en ny sjole.', 'sjole', 'kjole'),
('Jeg har sjikkelig vondt i hodet.', 'sjikkelig', 'skikkelig'),
('Jeg ønsker meg en sjangse til.', 'sjangse', 'sjanse'),
('Vi fant en liten jæmelighet.', 'jæmelighet', 'hemmelighet')],
'context': [
('Jeg viste ikke at butikken var stengt.', 'viste', 'visste'),
('Hun visste meg veien til skolen.', 'visste', 'viste'),
('Vi skule ta bussen hjem.', 'skule', 'skulle'),
('Hun har lånt en bok av meg, og jeg vil ha den til bake.', None, None),
('Jeg vil hjerne hjelpe deg med leksene.', 'hjerne', 'gjerne'),
('Etter middagen gikk vi gjem.', 'gjem', 'hjem'),
('Det har hvert kaldt hele natten.', 'hvert', 'vært'),
('Hun prøver og åpne døra.', 'og', 'å'),
('Vi kjøpte melk å brød.', 'å', 'og'),
('Han for en gave på bursdagen sin.', 'for', 'får'),
('Jeg trenger penger får å kjøpe mat.', 'får', 'for'),
('Hun vill komme på besøk i morgen.', 'vill', 'vil'),
('Vi så en vil rev ved skogen.', 'vil', 'vill'),
('Hun la boka på borde.', 'borde', 'bordet'),
('Jeg tok med meg en ekstra jakke får sikkerhets skyld.', 'får', 'for'),
('Kan du gjemme veska her mens jeg går hjem?', None, None)],
'clean': [(s,None,None) for s in [
'Jeg viste henne bildene fra ferien.', 'Hun visste svaret med en gang.',
'Jeg liker å synge og danse.', 'Hun kjøpte epler og pærer.',
'Hvert rom har et stort vindu.', 'Hun har vært på jobb i dag.',
'Hjernen trenger hvile etter en lang dag.', 'Jeg vil gjerne bli med.',
'Gjem brevet i skuffen.', 'Vi går hjem etter middag.',
'Han får hjelp av læreren.', 'Dette er en gave for hele familien.',
'Det er en vill katt i hagen.', 'Jeg vil lese ferdig boka.',
'Boka ligger i veska ved døra.', 'Boken ligger i vesken ved døren.',
'Jeg kasta ballen over gjerdet.', 'Jeg kastet ballen over gjerdet.',
'Åse og Øyvind reiser til Bodø på lørdag.', 'Amina og Sindre møtes på biblioteket.',
'Regnjakka henger ved inngangsdøra.', 'Sykkelhjelmen ligger i skolesekken.',
'Hun sendte en e-post til kundeservice.', 'Vi møtes klokka 14 på fredag.'
]]}
# Remove multiword errors from this single-word benchmark; retain scope in notes.
development['context'] = [r for r in development['context'] if 'til bake' not in r[0]]
# "tunell" is an accepted Bokmål variant: it belongs in clean controls.
development['sound_based'] = [r for r in development['sound_based'] if r[1] != 'tunell']
development['clean'].append(('Han kjørte gjennom en tunell.', None, None))

reserved = {
'spelling': [
('Hun fant en gammel notatbokk i skuffen.', 'notatbokk', 'notatbok'),
('Vi spiste midagg hos bestemor.', 'midagg', 'middag'),
('Jeg glemte laderren hjemme.', 'laderren', 'laderen'),
('Han sjekket kalenderren før han svarte.', 'kalenderren', 'kalenderen'),
('Det var en overaskelse for alle.', 'overaskelse', 'overraskelse'),
('Hun fant en parkeringsplas ved hotellet.', 'parkeringsplas', 'parkeringsplass')],
'context': [
('Ingen viste hvor nøkkelen lå.', 'viste', 'visste'),
('Guiden visste oss det gamle slottet.', 'visste', 'viste'),
('Barna skule besøke bestefar i helgen.', 'skule', 'skulle'),
('Jeg blir hjerne med på konserten.', 'hjerne', 'gjerne'),
('Har du hvert i Tromsø før?', 'hvert', 'vært'),
('Vi begynte og rydde etter festen.', 'og', 'å')],
'clean': [(s,None,None) for s in [
'Jeg viste fram den nye jakka.', 'Vi visste ikke når toget kom.',
'Hvert bord hadde en vase med blomster.', 'Hun ville lære å svømme.',
'Vi kjøpte kaffe og te til møtet.', 'Jeg blir gjerne med neste gang.',
'Regnbuksa ligger i barnehagesekken.', 'Ingvild og Håkon besøkte Ålesund.',
'Han lukka døra forsiktig.', 'Han lukket døren forsiktig.',
'Jeg får svar på søknaden i morgen.', 'Vi gjemte gavene under senga.'
]]}

def save(name, groups):
    rows=[]
    for kind, entries in groups.items():
        for text, wrong, right in entries:
            rows.append(dict(id=f'{name}-{len(rows)+1:03}',kind=kind if wrong else 'clean',text=text,
                             errors=[dict(word=wrong,occurrence=0,suggestions=[right])] if wrong else []))
    (HERE/f'{name}.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(name,len(rows),'sentences',sum(len(r['errors']) for r in rows),'errors')

if __name__=='__main__':
    save('extended-development',development)
    save('reserved-regression',reserved)
