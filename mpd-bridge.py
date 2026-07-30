#!/usr/bin/env python3
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import socket, json, urllib.request, urllib.parse, re, os, threading

MPD_HOST = os.environ.get('MPD_HOST', '127.0.0.1')
MPD_PORT = int(os.environ.get('MPD_PORT', '6600'))
PORT = int(os.environ.get('PORT', '8766'))
LASTFM_KEY = os.environ.get("LASTFM_API_KEY", "your_lastfm_api_key_here")

_art_cache = {}

_mpd_sock = None
_mpd_lock = threading.Lock()  # the HTTP server is multi-threaded, the mpd socket is shared

def mpd_command(cmd):
    with _mpd_lock:
        return _mpd_command_unlocked(cmd)

def _mpd_connect():
    s = socket.socket()
    s.settimeout(3)  # bounds connect/send/recv: a frozen mpd can't hang requests
    s.connect((MPD_HOST, MPD_PORT))
    s.recv(1024)  # "OK MPD x.y.z" banner
    return s

def _mpd_recv(sock):
    # Read a full mpd protocol response: it ends with a lone "OK" line,
    # or an "ACK ..." error line. TCP may fragment, so loop until complete.
    buf = b''
    while True:
        chunk = sock.recv(65536)
        if not chunk:
            raise ConnectionError('mpd connection closed')
        buf += chunk
        if buf == b'OK\n' or buf.endswith(b'\nOK\n'):
            return buf.decode()
        if buf.startswith(b'ACK ') and buf.endswith(b'\n'):
            return buf.decode()

def _mpd_command_unlocked(cmd):
    global _mpd_sock
    try:
        if _mpd_sock is None:
            _mpd_sock = _mpd_connect()
        _mpd_sock.sendall((cmd + '\n').encode())
        return _mpd_recv(_mpd_sock)
    except:
        try:
            _mpd_sock.close()
        except:
            pass
        _mpd_sock = None
        s = _mpd_connect()
        s.sendall((cmd + '\n').encode())
        result = _mpd_recv(s)
        _mpd_sock = s
        return result

def parse_mpd(raw):
    d = {}
    for line in raw.splitlines():
        if ': ' in line:
            k, v = line.split(': ', 1)
            d[k.lower()] = v
    return d

ALSA_CARD = os.environ.get('ALSA_CARD', '0')

def get_alsa_format():
    try:
        with open(f'/proc/asound/card{ALSA_CARD}/pcm0p/sub0/hw_params') as f:
            content = f.read()
        rate = ''
        bits = ''
        for line in content.splitlines():
            if line.startswith('format:'):
                m = re.search(r'S(\d+)', line)
                if m:
                    bits = m.group(1)
            if line.startswith('rate:'):
                rate = line.split()[1]
        if rate and bits:
            return f"{rate}:{bits}:2"
        return ''
    except:
        return ''

def get_art_url(artist, album):
    key = f"{artist}|{album}"
    if key in _art_cache:
        return _art_cache[key]
    if len(_art_cache) > 500:
        _art_cache.clear()  # simple cap to avoid unbounded growth
    try:
        q = urllib.parse.urlencode({
            'method': 'album.getinfo',
            'api_key': LASTFM_KEY,
            'artist': artist,
            'album': album,
            'format': 'json'
        })
        url = f'https://ws.audioscrobbler.com/2.0/?{q}'
        data = json.loads(urllib.request.urlopen(url, timeout=5).read())
        images = data.get('album', {}).get('image', [])
        art = ''
        for img in reversed(images):
            if img.get('#text'):
                art = re.sub(r'/\d+x\d+/', '/', img['#text'])
                break
        _art_cache[key] = art
        return art
    except:
        pass
    _art_cache[key] = ''
    return ''

def get_status():
    status = parse_mpd(mpd_command('status'))
    currentsong = parse_mpd(mpd_command('currentsong'))
    state = status.get('state', 'stop')
    elapsed = float(status.get('elapsed', 0))
    duration = float(status.get('duration', 0))
    file_url = currentsong.get('file', '')
    artist = currentsong.get('artist', '')
    album = currentsong.get('album', '')
    art_url = get_art_url(artist, album) if artist and album else ''
    # Next track in the queue (mpd exposes its position via 'nextsong')
    next_title = ''
    next_artist = ''
    ns = status.get('nextsong')
    if ns is not None and state != 'stop':
        nxt = parse_mpd(mpd_command(f'playlistinfo {ns}'))
        next_title = nxt.get('title', '')
        next_artist = nxt.get('artist', '')
    return {
        'state': state,
        'title': currentsong.get('title', '\u2014'),
        'artist': artist or '\u2014',
        'album': album,
        'elapsed': elapsed,
        'duration': duration,
        'format': get_alsa_format() if state != 'stop' else '',
        'art_url': art_url,
        'file': file_url,
        'next_title': next_title,
        'next_artist': next_artist
    }

STATIC_FILES = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/?lang=fr': ('index.fr.html', 'text/html; charset=utf-8'),
    '/index.html': ('index.html', 'text/html; charset=utf-8'),
    '/index.fr.html': ('index.fr.html', 'text/html; charset=utf-8'),
    '/hires.svg': ('hires.svg', 'image/svg+xml'),
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/now':
            try:
                data = get_status()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        elif self.path in STATIC_FILES:
            filename, content_type = STATIC_FILES[self.path]
            filepath = os.path.join(SCRIPT_DIR, filename)
            try:
                with open(filepath, 'rb') as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.end_headers()
                self.wfile.write(data)
            except:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, *args): pass

ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
