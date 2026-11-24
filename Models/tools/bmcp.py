# bmcp.py — выполнить код в ОТКРЫТОМ окне Blender пользователя через аддон BlenderMCP (порт 9876):
#   python tools/bmcp.py "print(bpy.app.version_string)"      или      python tools/bmcp.py @файл.py
# Нужен, чтобы показывать пользователю готовую модель в его окне Blender (сборка и рендеры идут без окна).
import socket, json, sys

code = sys.argv[1]
if code.startswith('@'):
    code = open(code[1:], encoding='utf-8').read()
s = socket.create_connection(('127.0.0.1', 9876), timeout=10)
s.settimeout(float(sys.argv[2]) if len(sys.argv) > 2 else 120)
s.sendall(json.dumps({'type': 'execute_code', 'params': {'code': code}}).encode('utf-8'))
buf = b''
while True:
    try:
        chunk = s.recv(65536)
    except socket.timeout:
        print('TIMEOUT')
        break
    if not chunk:
        break
    buf += chunk
    try:
        r = json.loads(buf.decode('utf-8'))
        print(json.dumps(r, ensure_ascii=False)[:1500])
        break
    except ValueError:
        continue
s.close()
