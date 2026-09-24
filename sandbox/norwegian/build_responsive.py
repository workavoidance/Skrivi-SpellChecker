"""Build the responsive local UI from the existing POC, reusing its checked behavior."""
from pathlib import Path

HERE = Path(__file__).parent
page = (HERE / 'poc.html').read_text(encoding='utf-8')
css = (HERE / 'responsive.css').read_text(encoding='utf-8')
page = page.replace('</style>', css + '\n</style>', 1)
page = page.replace('</html>', '<script src="/responsive.js"></script></html>')
(HERE / 'responsive.html').write_text(page, encoding='utf-8')
