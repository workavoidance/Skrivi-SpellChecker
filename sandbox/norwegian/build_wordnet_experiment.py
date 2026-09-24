"""Compose the WordNet meaning experiment without changing the default UI."""

from pathlib import Path

HERE = Path(__file__).parent
page = (HERE / 'responsive.html').read_text(encoding='utf-8')
page = page.replace('Skriv og velg · Bokmål', 'Bokmål · Norsk ordvev-eksperiment', 1)
page = page.replace('</html>', '<script src="/wordnet.js"></script></html>', 1)
(HERE / 'responsive-wordnet.html').write_text(page, encoding='utf-8')
