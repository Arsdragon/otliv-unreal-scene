"""MCP server (stdio, no dependencies) that drives a running Unreal Editor.

It talks to the editor through Unreal's own Python remote execution client
(PythonScriptPlugin/Content/Python/remote_execution.py), with fixes for this project:
  * loopback only (multicast bound to 127.0.0.1, TTL 0) - nothing outside this PC reaches the editor;
  * lazy connect + automatic reconnect when the editor is restarted or crashes;
  * a free command port per connection (no clash with other clients on the fixed 6776);
  * safe message framing (the stock client cuts long answers at 8 KB boundaries);
  * screenshots come back to the chat as images.

Run as an MCP server:   python -I server.py
Self-test:              python -I server.py --selftest [seconds_to_wait_for_editor]
"""
import base64
import ctypes
import json
import os
import socket
import sys
import threading
import time
import traceback

UE_ROOT = os.environ.get("UE_ROOT", r"C:\Program Files\Epic Games\UE_5.8")
PROJECT_NAME = os.environ.get("UE_PROJECT_NAME", "Scenes")
SHOTS_DIR = os.environ.get("UE_SHOTS_DIR", r"C:\UnrealScenes\Review\_mcp")
MAX_TEXT = 60000

sys.path.insert(0, os.path.join(UE_ROOT, r"Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python"))
import remote_execution as rex  # noqa: E402  (ships with the engine)


def log(*args):
    print(*args, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- remote execution fixes
def _receive_message(self, expected_type):
    """Read until the bytes form one complete JSON message (no length prefix in the protocol)."""
    data = b""
    while True:
        part = self._command_channel_socket.recv(65536)
        if not part:
            raise ConnectionError("the editor closed the command connection")
        data += part
        try:
            json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
        break
    message = rex._RemoteExecutionMessage(None, None)
    if message.from_json_bytes(data) and message.passes_receive_filter(self._node_id) and message.type_ == expected_type:
        return message
    raise RuntimeError("the editor sent an unexpected answer")


rex._RemoteExecutionCommandConnection._receive_message = _receive_message


def _free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _MemStatus(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def memory_line():
    try:
        m = _MemStatus()
        m.dwLength = ctypes.sizeof(m)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        g = 2 ** 30
        return ("PC memory: free RAM %.1f of %.1f GB, free commit %.1f of %.1f GB"
                % (m.ullAvailPhys / g, m.ullTotalPhys / g, m.ullAvailPageFile / g, m.ullTotalPageFile / g))
    except Exception as e:  # pragma: no cover
        return "PC memory: unknown (%s)" % e


class EditorNotFound(RuntimeError):
    pass


class Editor:
    def __init__(self):
        self.rex = None
        self.node = None
        self.lock = threading.Lock()

    def _start(self):
        if self.rex is None:
            cfg = rex.RemoteExecutionConfig()
            cfg.multicast_ttl = 0
            cfg.multicast_group_endpoint = ("239.0.0.1", 6766)
            cfg.multicast_bind_address = "127.0.0.1"
            cfg.command_endpoint = ("127.0.0.1", _free_port())
            self.rex = rex.RemoteExecution(cfg)
            self.rex.start()

    def reset(self):
        try:
            if self.rex:
                self.rex.stop()
        except Exception:
            pass
        self.rex = None
        self.node = None

    def nodes(self, wait=3.0):
        self._start()
        deadline = time.time() + wait
        found = self.rex.remote_nodes
        while not found and time.time() < deadline:
            time.sleep(0.2)
            found = self.rex.remote_nodes
        return found

    def connect(self, wait=10.0):
        if self.node and self.rex and self.rex.has_command_connection():
            alive = [n for n in self.rex.remote_nodes if n.get("node_id") == self.node.get("node_id")]
            if alive:
                return self.node
            self.reset()  # editor restarted or gone: its node id timed out
        found = self.nodes(wait)
        if not found:
            self.reset()
            raise EditorNotFound(
                "Unreal Editor not found. Start it: \"%s\\Engine\\Binaries\\Win64\\UnrealEditor.exe\" "
                "\"C:\\UnrealScenes\\Project\\Scenes.uproject\" (first start compiles shaders for a long time; "
                "the editor answers only after its window is up). %s" % (UE_ROOT, memory_line()))
        pick = next((n for n in found if n.get("project_name") == PROJECT_NAME), found[0])
        self.rex._config.command_endpoint = ("127.0.0.1", _free_port())
        self.rex.open_command_connection(pick["node_id"])
        self.node = pick
        return pick

    def run(self, code, timeout=300.0, mode=rex.MODE_EXEC_FILE):
        with self.lock:
            self.connect()
            cc = self.rex._command_connection
            cc._command_channel_socket.settimeout(timeout)
            try:
                cc._send_message(rex._RemoteExecutionMessage(rex._TYPE_COMMAND, cc._node_id, cc._remote_node_id, {
                    "command": code, "unattended": True, "exec_mode": mode}))
                return cc._receive_message(rex._TYPE_COMMAND_RESULT).data
            except socket.timeout:
                self.reset()
                raise TimeoutError("no answer from the editor within %d s - the command may still be running "
                                   "(the editor is busy or hung). %s" % (timeout, memory_line()))
            except (OSError, ConnectionError, RuntimeError) as e:
                self.reset()
                raise ConnectionError("lost the editor during the command (%s) - did it crash? Check "
                                      "C:\\UnrealScenes\\Project\\Saved\\Logs\\Scenes.log. %s" % (e, memory_line()))


EDITOR = Editor()


def format_result(data):
    lines = []
    for o in data.get("output") or []:
        kind, text = o.get("type", "Info"), (o.get("output") or "").rstrip("\r\n")
        lines.append(text if kind == "Info" else "[%s] %s" % (kind, text))
    out = "\n".join(lines)
    res = data.get("result")
    if not data.get("success"):
        out += ("\n" if out else "") + "FAILED:\n" + str(res)
    elif res not in (None, "None", ""):
        out += ("\n" if out else "") + "result: " + str(res)
    if len(out) > MAX_TEXT:
        out = out[:MAX_TEXT] + "\n... [cut: %d more characters]" % (len(out) - MAX_TEXT)
    return out or "(no output)"


# ---------------------------------------------------------------- tools
def tool_status(args):
    found = EDITOR.nodes(float(args.get("wait_s", 3)))
    lines = [memory_line()]
    if not found:
        lines.append("Unreal Editor: not found (not running, still starting, or remote execution is off).")
    for n in found:
        lines.append("Editor node %s: project %s, engine %s, %s" % (
            n.get("node_id", "?")[:8], n.get("project_name"), n.get("engine_version"), n.get("project_root")))
    if EDITOR.node:
        lines.append("Command connection open to node %s." % EDITOR.node.get("node_id", "?")[:8])
    return [{"type": "text", "text": "\n".join(lines)}], False


def tool_python(args):
    code = args.get("code") or ""
    if not code.strip():
        return [{"type": "text", "text": "code is empty"}], True
    data = EDITOR.run(code, float(args.get("timeout_s", 300)))
    return [{"type": "text", "text": format_result(data)}], not data.get("success")


SHOT_SCRIPT = r'''
import os, unreal
path = %(path)r
camera = None
name = %(camera)r
if name:
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if a.get_actor_label() == name or a.get_name() == name:
            camera = a
            break
    if camera is None:
        raise RuntimeError("camera actor not found: " + name)
os.makedirs(os.path.dirname(path), exist_ok=True)
if os.path.exists(path):
    os.remove(path)
unreal.AutomationLibrary.take_high_res_screenshot(%(w)d, %(h)d, path, camera=camera)
print("screenshot requested")
'''


def tool_screenshot(args):
    w, h = int(args.get("width", 960)), int(args.get("height", 540))
    timeout = float(args.get("timeout_s", 120))
    path = args.get("save_as") or os.path.join(SHOTS_DIR, time.strftime("shot_%Y%m%d_%H%M%S.png"))
    path = os.path.abspath(path)
    if not path.lower().endswith(".png"):
        path += ".png"
    data = EDITOR.run(SHOT_SCRIPT % {"path": path, "camera": args.get("camera") or "", "w": w, "h": h}, 120)
    if not data.get("success"):
        return [{"type": "text", "text": format_result(data)}], True
    deadline, last = time.time() + timeout, -1
    while time.time() < deadline:  # the editor writes the file a few frames later
        if os.path.exists(path):
            size = os.path.getsize(path)
            if size > 0 and size == last:
                break
            last = size
        time.sleep(0.5)
    else:
        return [{"type": "text", "text": "the screenshot file did not appear in %d s: %s (is the editor window "
                 "minimised or frozen?)" % (timeout, path)}], True
    content = [{"type": "text", "text": "saved %dx%d: %s" % (w, h, path)}]
    if args.get("return_image", True):
        with open(path, "rb") as f:
            content.append({"type": "image", "data": base64.b64encode(f.read()).decode("ascii"),
                            "mimeType": "image/png"})
    return content, False


TOOLS = [
    {"name": "ue_status",
     "description": "Find the running Unreal Editor and report free PC memory. Use first, and after any crash.",
     "inputSchema": {"type": "object", "properties": {
         "wait_s": {"type": "number", "description": "seconds to wait for the editor to answer (default 3)"}}}},
    {"name": "ue_python",
     "description": ("Run Python inside the Unreal Editor (full `unreal` API, runs on the editor's main thread). "
                     "The code runs as a script: use print() for output. Errors come back with a traceback. "
                     "Keep each call short (the editor is frozen while it runs); split long jobs."),
     "inputSchema": {"type": "object", "required": ["code"], "properties": {
         "code": {"type": "string", "description": "Python source to execute in the editor"},
         "timeout_s": {"type": "number", "description": "how long to wait for the result (default 300)"}}}},
    {"name": "ue_screenshot",
     "description": ("Render the active level viewport (or a camera actor's view) to a PNG and return it as an image. "
                     "Keep sizes modest (default 960x540) to save context; set return_image=false to only save the file."),
     "inputSchema": {"type": "object", "properties": {
         "width": {"type": "integer"}, "height": {"type": "integer"},
         "camera": {"type": "string", "description": "label or name of a CameraActor/CineCameraActor to shoot from"},
         "save_as": {"type": "string", "description": "absolute .png path (default C:\\UnrealScenes\\Review\\_mcp\\shot_<time>.png)"},
         "return_image": {"type": "boolean"},
         "timeout_s": {"type": "number", "description": "how long to wait for the file (default 120)"}}}},
]
HANDLERS = {"ue_status": tool_status, "ue_python": tool_python, "ue_screenshot": tool_screenshot}

INSTRUCTIONS = ("Drives the user's running Unreal Editor 5.8 (project C:\\UnrealScenes\\Project\\Scenes.uproject) through "
                "Python remote execution. The PC is a 16 GB laptop with integrated Intel graphics: the editor is slow, "
                "check memory with ue_status before heavy work, keep scripts short, save the level often. "
                "If the editor is not found, start it with Bash and wait for its window.")


# ---------------------------------------------------------------- MCP stdio loop
def send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def handle(msg):
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        return  # notification
    if method == "initialize":
        ver = (msg.get("params") or {}).get("protocolVersion") or "2025-06-18"
        send({"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": ver, "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "unreal-scenes", "version": "1.0.0"}, "instructions": INSTRUCTIONS}})
    elif method == "ping":
        send({"jsonrpc": "2.0", "id": mid, "result": {}})
    elif method == "tools/list":
        send({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
    elif method == "tools/call":
        params = msg.get("params") or {}
        name, args = params.get("name"), params.get("arguments") or {}
        fn = HANDLERS.get(name)
        if fn is None:
            send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": "unknown tool: %s" % name}})
            return
        try:
            content, is_error = fn(args)
        except Exception as e:
            log(traceback.format_exc())
            content, is_error = [{"type": "text", "text": "%s: %s" % (type(e).__name__, e)}], True
        send({"jsonrpc": "2.0", "id": mid, "result": {"content": content, "isError": is_error}})
    else:
        send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found: %s" % method}})


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line.decode("utf-8"))
        except ValueError:
            log("bad json from client: %r" % line[:200])
            continue
        try:
            handle(msg)
        except Exception:
            log(traceback.format_exc())
    EDITOR.reset()


def selftest(wait):
    sys.stdout.reconfigure(encoding="utf-8")
    print(memory_line())
    deadline = time.time() + wait
    while True:
        try:
            node = EDITOR.connect(wait=5)
            break
        except EditorNotFound:
            if time.time() > deadline:
                print("editor not found")
                return 1
    print("connected:", node.get("project_name"), node.get("engine_version"), node.get("project_root"))
    data = EDITOR.run("import unreal\nprint(unreal.SystemLibrary.get_engine_version())\n"
                      "print(unreal.Paths.get_project_file_path())\nprint('x' * 20000)", 60)
    text = format_result(data)
    print("success:", data.get("success"), "| output chars:", len(text))
    print(text[:300])
    EDITOR.reset()
    return 0 if data.get("success") else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        sys.exit(selftest(float(sys.argv[2]) if len(sys.argv) > 2 else 10))
    main()
