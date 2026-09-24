import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
import webbrowser
from engine import Checker
from setup_assets import ROOT
from wordnet_help import WordnetHelp
from personal_dictionary import PersonalDictionary

HERE = Path(__file__).parent

def serve(port=0, open_browser=True, poc=False, responsive=False, wordnet=False):
    checker = Checker()
    personal = PersonalDictionary()
    lexical_help = WordnetHelp(
        ROOT / 'lexical' / 'norsk-ordvev-1.1.2' / 'wordnet-help.sqlite3'
        if wordnet else None
    )
    lock = threading.Lock()
    speech_lock = threading.Lock()
    key = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log user writing.

        def reply(self, code, data, kind='application/json; charset=utf-8'):
            payload = data.encode() if isinstance(data, str) else json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; connect-src 'self'; media-src 'self' data: blob:")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.headers.get('Host') != self.server.host:
                return self.reply(403, {'error': 'Invalid host'})
            if self.path == '/':
                page = ('responsive-wordnet.html' if wordnet else
                        ('responsive.html' if responsive else ('poc.html' if poc else 'index.html')))
                return self.reply(200, (HERE/page).read_text(encoding='utf-8').replace('__SESSION_KEY__', key), 'text/html; charset=utf-8')
            if self.path in ('/poc.js', '/responsive.js', '/wordnet.js'):
                return self.reply(200, (HERE/self.path[1:]).read_text(encoding='utf-8'), 'text/javascript; charset=utf-8')
            self.reply(404, {'error': 'Not found'})

        def do_POST(self):
            if (self.headers.get('Host') != self.server.host or
                self.headers.get('X-Skrivi-Key') != key or
                self.headers.get('Origin') not in (None, 'http://'+self.server.host)):
                return self.reply(403, {'error': 'Invalid session'})
            if self.path == '/shutdown':
                self.reply(200, {'ok': True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if self.path not in ('/check', '/speech', '/voices', '/word-help', '/personal-word'):
                return self.reply(404, {'error': 'Not found'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if length <= 0 or length > 24000:
                    raise ValueError('Request too large or empty.')
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('Invalid request.')
                if self.path == '/word-help':
                    if not lexical_help.available:
                        return self.reply(503, {'error': 'Norsk ordvev help is not installed.'})
                    return self.reply(200, {
                        'available': True,
                        'entries': lexical_help.lookup_many(data.get('words')),
                    })
                if self.path == '/personal-word':
                    action = data.get('action')
                    if action == 'add':
                        return self.reply(200, {'ok': True, 'count': personal.add(data.get('word'))})
                    if action == 'clear':
                        return self.reply(200, {'ok': True, 'removed': personal.clear()})
                    raise ValueError('Unknown remembered-word action.')
                if self.path in ('/speech', '/voices'):
                    from local_speech import synthesize
                    if not speech_lock.acquire(blocking=False):
                        return self.reply(409, {'error':'Lyden klargjøres. Prøv igjen om et øyeblikk.'})
                    try:
                        if self.path == '/speech' and not isinstance(data.get('text'), str):
                            raise ValueError('Text is required.')
                        return self.reply(200, synthesize(data.get('text') if self.path == '/speech' else None))
                    finally:
                        speech_lock.release()
                if not isinstance(data.get('text'), str):
                    raise ValueError('Text is required.')
                if not lock.acquire(blocking=False):
                    return self.reply(409, {'error': 'A check is already running.'})
                try:
                    result = personal.apply(checker.check(data['text'], data.get('mode')))
                finally:
                    lock.release()
                self.reply(200, result)
            except Exception as exc:
                self.reply(400, {'error': str(exc)})

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.host = f'127.0.0.1:{server.server_port}'
    print('Skrivi Norwegian POC: http://'+server.host, flush=True)
    if open_browser:
        webbrowser.open('http://'+server.host)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        if checker.qwen:
            checker.qwen.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--poc', action='store_true')
    parser.add_argument('--responsive', action='store_true')
    parser.add_argument('--wordnet', action='store_true')
    args = parser.parse_args()
    serve(args.port, not args.no_browser, args.poc, args.responsive, args.wordnet)
