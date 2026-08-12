from flask import Flask, request, redirect, Response, render_template_string, make_response
import os
import re
import requests
from urllib.parse import urlparse, quote, unquote

app = Flask(__name__)

# 간단한 봇 확인 (클릭 1회) — Cloudflare 스타일
BOT_COOKIE = "kh_human"
BOT_COOKIE_VAL = "1"
# 봇 확인 적용 경로 (실행기용 "/" 는 제외)
BOT_CHECK_PATHS = {"/home", "/obf", "/bypass", "/admin", "/discord"}


def bot_verified() -> bool:
    return request.cookies.get(BOT_COOKIE) == BOT_COOKIE_VAL


def bot_challenge_page():
    next_url = request.path
    if request.query_string:
        next_url = next_url + "?" + request.query_string.decode()
    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Checking your browser...</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    background: #050508; color: #e8e8f0;
    font-family: Inter, system-ui, sans-serif;
  }}
  .box {{
    width: 100%; max-width: 420px; margin: 16px;
    background: #0c0c14; border: 1px solid #1a1a28;
    border-radius: 16px; padding: 36px 28px; text-align: center;
    box-shadow: 0 20px 50px rgba(0,0,0,0.45);
  }}
  .logo {{
    font-weight: 800; font-size: 1.1rem; letter-spacing: 0.04em;
    background: linear-gradient(135deg, #c084fc, #ab3cff);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 20px;
  }}
  h1 {{ font-size: 1.15rem; margin-bottom: 8px; }}
  p {{ color: #8a8aa0; font-size: 0.9rem; margin-bottom: 24px; line-height: 1.5; }}
  .check {{
    display: flex; align-items: center; gap: 12px;
    background: #07070c; border: 1px solid #2a2a3a;
    border-radius: 10px; padding: 14px 16px; cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
    text-align: left;
  }}
  .check:hover {{ border-color: #ab3cff; background: #0f0f18; }}
  .box-sq {{
    width: 22px; height: 22px; border: 2px solid #8a8aa0;
    border-radius: 4px; flex-shrink: 0;
  }}
  .check span {{ font-size: 0.92rem; color: #e8e8f0; }}
  .foot {{ margin-top: 22px; font-size: 0.75rem; color: #5a5a70; }}
</style>
</head>
<body>
  <div class="box">
    <div class="logo">KENDERHOOK</div>
    <h1>봇 확인 / Verify you are human</h1>
    <p>계속하려면 아래를 클릭하세요.<br>Click the box below to continue.</p>
    <form method="POST" action="/verify-human">
      <input type="hidden" name="next" value="{next_url}">
      <button type="submit" class="check" name="ok" value="1">
        <div class="box-sq"></div>
        <span>확인 · Confirm you are human</span>
      </button>
    </form>
    <div class="foot">KENDERHOOK Security Check</div>
  </div>
</body>
</html>
"""
    return Response(html, mimetype="text/html")


@app.before_request
def require_human():
    # 정적/검증/실행기 엔드포인트는 제외
    if request.path in ("/verify-human", "/"):
        return None
    if request.path.startswith("/static"):
        return None
    # UI 경로만 검사
    if request.path not in BOT_CHECK_PATHS and not request.path.startswith("/admin"):
        return None
    if bot_verified():
        return None
    # POST verify는 before_request에서 막지 않음
    return bot_challenge_page()


@app.route("/verify-human", methods=["POST"])
def verify_human():
    next_url = request.form.get("next") or "/home"
    if not next_url.startswith("/"):
        next_url = "/home"
    resp = make_response(redirect(next_url))
    # 세션마다 다시 보게: max_age 없으면 브라우저 종료 시 삭제 / 또는 하루
    resp.set_cookie(
        BOT_COOKIE,
        BOT_COOKIE_VAL,
        max_age=60 * 60 * 12,  # 12시간
        httponly=True,
        samesite="Lax",
    )
    return resp


# ─── 설정 ────────────────────────────────────────────────
ADMIN_PASSWORD = "exploit111"
DISCORD_URL = "https://discord.gg/m3VKRyweHC"

# 서버 저장 파일 (.luau 확장자 사용 안 함)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_FILE = os.path.join(BASE_DIR, "script.txt")

# MoonVeil API Key
MOONVEIL_API_KEY = os.environ.get(
    "MOONVEIL_API_KEY",
    "mv-secret-2785898a76386e5f64957742c502ff8cc66c5e8e004215b1475390f8d76dc844",
)
MOONVEIL_OBF_URL = "https://moonveil.cc/api/v2/obf"

DEFAULT_SCRIPT = """-- Script
print("Hello from Host")
"""

# ─── 헬퍼 ────────────────────────────────────────────────

def load_script() -> str:
    """서버에 저장된 스크립트 읽기"""
    if os.path.isfile(SCRIPT_FILE):
        try:
            with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            pass
    return DEFAULT_SCRIPT


def save_script(content: str) -> str:
    """서버에 스크립트 저장. .luau 파일명 사용하지 않음."""
    content = content if content is not None else ""
    tmp_path = SCRIPT_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, SCRIPT_FILE)
    return SCRIPT_FILE


def is_browser(user_agent: str) -> bool:
    if not user_agent:
        return False
    ua = user_agent.lower()
    browser_keywords = [
        "mozilla", "chrome", "safari", "firefox", "edge", "opera",
        "msie", "trident", "gecko", "webkit"
    ]
    return any(k in ua for k in browser_keywords)


def call_moonveil(script: str, options: dict | None = None) -> tuple[bool, str]:
    """MoonVeil API 호출. 성공 시 (True, obfuscated_code), 실패 시 (False, error_msg)"""
    if not MOONVEIL_API_KEY or MOONVEIL_API_KEY.strip() == "":
        return False, "API 키가 설정되지 않았습니다. Render Environment에 MOONVEIL_API_KEY를 넣어주세요."

    payload = {"script": script}
    if options:
        payload["options"] = options

    headers = {
        "Authorization": f"Bearer {MOONVEIL_API_KEY.strip()}",
        "Content-Type": "application/json",
        "Accept": "text/plain, application/json",
    }

    try:
        resp = requests.post(MOONVEIL_OBF_URL, json=payload, headers=headers, timeout=120)
        if resp.status_code == 200:
            return True, resp.text
        try:
            err = resp.json().get("error", resp.text)
        except Exception:
            err = resp.text or f"HTTP {resp.status_code}"
        if resp.status_code == 401:
            return False, (
                "[401] API 키가 유효하지 않습니다 (unauthorized).\n"
                "MoonVeil 대시보드에서 새 API Key를 발급받아 "
                "Render Environment → MOONVEIL_API_KEY 에 넣어주세요."
            )
        if resp.status_code == 429:
            return False, "[429] 일일 할당량 초과 또는 rate limit. 나중에 다시 시도하세요."
        return False, f"[{resp.status_code}] {err}"
    except requests.Timeout:
        return False, "요청 시간 초과 (120초). 스크립트가 너무 길 수 있습니다."
    except Exception as e:
        return False, f"요청 실패: {e}"


# ─── 라우트 ───────────────────────────────────────────────

@app.route("/")
def index():
    ua = request.headers.get("User-Agent", "")
    if is_browser(ua):
        return Response(
            "<html><body style='background:#111;color:#f55;font-family:monospace;"
            "display:flex;justify-content:center;align-items:center;height:100vh;margin:0'>"
            "<div style='text-align:center'>"
            "<h1>⛔ ACCESS DENIED</h1>"
            "<p>This endpoint is not available for browsers.</p>"
            "</div></body></html>",
            status=403,
            mimetype="text/html",
        )
    script = load_script()
    return Response(script, mimetype="text/plain; charset=utf-8")


@app.route("/discord")
def discord():
    return redirect(DISCORD_URL, code=302)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    message = ""
    current_script = load_script()

    if request.method == "POST":
        password = request.form.get("password", "")
        script_content = request.form.get("script", "")

        if password != ADMIN_PASSWORD:
            message = "❌ 비밀번호가 틀렸습니다."
        else:
            saved_path = save_script(script_content)
            current_script = script_content
            message = f"✅ 서버에 저장됨: {saved_path}"

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin - Luau Script Manager</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                background: #0d1117; color: #e6edf3;
                font-family: 'Segoe UI', system-ui, sans-serif;
                min-height: 100vh; display: flex; justify-content: center;
                align-items: flex-start; padding: 40px 20px;
            }}
            .container {{
                width: 100%; max-width: 800px; background: #161b22;
                border: 1px solid #30363d; border-radius: 12px; padding: 32px;
                box-shadow: 0 8px 24px rgba(0,0,0,0.4);
            }}
            h1 {{ font-size: 1.5rem; margin-bottom: 8px; color: #58a6ff; }}
            .subtitle {{ color: #8b949e; font-size: 0.9rem; margin-bottom: 24px; }}
            label {{ display: block; margin-bottom: 6px; font-weight: 600; font-size: 0.9rem; }}
            input[type="password"], textarea {{
                width: 100%; background: #0d1117; border: 1px solid #30363d;
                border-radius: 8px; color: #e6edf3; padding: 12px 14px;
                font-size: 0.95rem; margin-bottom: 18px;
                font-family: 'Cascadia Code', 'Fira Code', monospace;
            }}
            input:focus, textarea:focus {{
                outline: none; border-color: #58a6ff;
                box-shadow: 0 0 0 3px rgba(88,166,255,0.2);
            }}
            textarea {{ min-height: 320px; resize: vertical; line-height: 1.5; }}
            button {{
                background: #238636; color: white; border: none; border-radius: 8px;
                padding: 12px 24px; font-size: 1rem; font-weight: 600; cursor: pointer;
            }}
            button:hover {{ background: #2ea043; }}
            .msg {{ margin-bottom: 20px; padding: 12px 16px; border-radius: 8px; font-size: 0.95rem; }}
            .msg.success {{ background: rgba(35,134,54,0.2); border: 1px solid #238636; color: #3fb950; }}
            .msg.error {{ background: rgba(248,81,73,0.15); border: 1px solid #f85149; color: #f85149; }}
            .info {{ margin-top: 24px; padding-top: 20px; border-top: 1px solid #30363d; font-size: 0.85rem; color: #8b949e; }}
            .info code {{ background: #0d1117; padding: 2px 6px; border-radius: 4px; color: #79c0ff; }}
            a {{ color: #58a6ff; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛠 Luau Script Admin</h1>
            <p class="subtitle">비밀번호를 입력하고 스크립트를 저장하세요.</p>

            {"<div class='msg success'>" + message + "</div>" if message.startswith("✅") else ""}
            {"<div class='msg error'>" + message + "</div>" if message.startswith("❌") else ""}

            <form method="POST">
                <label for="password">비밀번호</label>
                <input type="password" id="password" name="password" placeholder="admin password" required autocomplete="current-password">

                <label for="script">Luau 스크립트</label>
                <textarea id="script" name="script" spellcheck="false">{current_script}</textarea>

                <button type="submit">저장하기</button>
            </form>

            <div class="info">
                <p>• 메인 <code>/</code> : 브라우저 접속 시 차단 / 그 외에는 저장된 스크립트 반환</p>
                <p>• Discord <code>/discord</code> · 난독화 <code>/obf</code></p>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route("/obf", methods=["GET", "POST"])
def obfuscate_page():
    result = ""
    error = ""
    input_script = ""
    selected_compile = "cff"
    selected_vm = "skid"

    if request.method == "POST":
        input_script = request.form.get("script", "").strip()
        selected_compile = request.form.get("compileType", "cff")
        selected_vm = request.form.get("vmType", "skid")

        if not input_script:
            error = "스크립트를 입력해주세요."
        else:
            options = {
                "compileType": selected_compile,
                "vmType": selected_vm,
            }
            # 체크박스 옵션
            if request.form.get("cffDecompose"):
                options["cffDecompose"] = True
            if request.form.get("cffMangleStrings"):
                options["cffMangleStrings"] = True
            if request.form.get("cffMangleGlobals"):
                options["cffMangleGlobals"] = True

            ok, out = call_moonveil(input_script, options)
            if ok:
                result = out
            else:
                error = out

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Luau Obfuscator (MoonVeil)</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                background: #0d1117; color: #e6edf3;
                font-family: 'Segoe UI', system-ui, sans-serif;
                min-height: 100vh; padding: 32px 16px;
            }}
            .wrap {{ max-width: 1100px; margin: 0 auto; }}
            h1 {{ font-size: 1.6rem; color: #a371f7; margin-bottom: 6px; }}
            .sub {{ color: #8b949e; margin-bottom: 28px; font-size: 0.9rem; }}
            .sub a {{ color: #58a6ff; }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
            @media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
            .panel {{
                background: #161b22; border: 1px solid #30363d;
                border-radius: 12px; padding: 20px;
            }}
            label {{ display: block; font-weight: 600; font-size: 0.85rem; margin-bottom: 6px; color: #c9d1d9; }}
            textarea {{
                width: 100%; min-height: 340px; background: #0d1117;
                border: 1px solid #30363d; border-radius: 8px; color: #e6edf3;
                padding: 14px; font-family: 'Cascadia Code', 'Fira Code', monospace;
                font-size: 0.9rem; line-height: 1.5; resize: vertical;
            }}
            textarea:focus {{ outline: none; border-color: #a371f7; box-shadow: 0 0 0 3px rgba(163,113,247,0.2); }}
            .opts {{
                display: flex; flex-wrap: wrap; gap: 12px 20px;
                margin: 16px 0; align-items: center;
            }}
            .opts select {{
                background: #0d1117; border: 1px solid #30363d; color: #e6edf3;
                padding: 8px 12px; border-radius: 6px; font-size: 0.9rem;
            }}
            .opts label.chk {{
                display: flex; align-items: center; gap: 6px; font-weight: 500;
                cursor: pointer; margin: 0;
            }}
            button {{
                background: #8957e5; color: white; border: none; border-radius: 8px;
                padding: 12px 28px; font-size: 1rem; font-weight: 600; cursor: pointer;
                transition: background 0.15s;
            }}
            button:hover {{ background: #a371f7; }}
            button:disabled {{ opacity: 0.6; cursor: not-allowed; }}
            .msg {{
                margin-top: 16px; padding: 12px 16px; border-radius: 8px; font-size: 0.9rem;
            }}
            .msg.error {{ background: rgba(248,81,73,0.15); border: 1px solid #f85149; color: #f85149; }}
            .msg.ok {{ background: rgba(35,134,54,0.15); border: 1px solid #238636; color: #3fb950; }}
            .copy-btn {{
                background: #21262d; color: #c9d1d9; border: 1px solid #30363d;
                padding: 6px 12px; border-radius: 6px; font-size: 0.8rem;
                cursor: pointer; margin-top: 10px;
            }}
            .copy-btn:hover {{ background: #30363d; }}
        </style>
    </head>
    <body>
        <div class="wrap">
            <h1>🔒 Luau Obfuscator</h1>
            <p class="sub">Powered by MoonVeil · <a href="/discord">Discord</a> · <a href="/home">Home</a></p>

            <form method="POST" id="obfForm">
                <div class="grid">
                    <div class="panel">
                        <label for="script">원본 스크립트</label>
                        <textarea id="script" name="script" spellcheck="false" placeholder="-- 여기에 Luau 코드를 붙여넣으세요">{input_script}</textarea>
                    </div>
                    <div class="panel">
                        <label>난독화 결과</label>
                        <textarea id="result" readonly spellcheck="false" placeholder="결과가 여기에 표시됩니다...">{result}</textarea>
                        {"<button type='button' class='copy-btn' onclick='copyResult()'>복사하기</button>" if result else ""}
                    </div>
                </div>

                <div class="opts">
                    <div>
                        <label style="margin:0 0 4px 0">Compile Type</label>
                        <select name="compileType">
                            <option value="cff" {"selected" if selected_compile == "cff" else ""}>cff</option>
                            <option value="vm" {"selected" if selected_compile == "vm" else ""}>vm</option>
                            <option value="safeEnv" {"selected" if selected_compile == "safeEnv" else ""}>safeEnv</option>
                        </select>
                    </div>
                    <div>
                        <label style="margin:0 0 4px 0">VM Type</label>
                        <select name="vmType">
                            <option value="skid" {"selected" if selected_vm == "skid" else ""}>skid</option>
                            <option value="fox" {"selected" if selected_vm == "fox" else ""}>fox</option>
                        </select>
                    </div>
                    <label class="chk"><input type="checkbox" name="cffDecompose" value="1"> cffDecompose</label>
                    <label class="chk"><input type="checkbox" name="cffMangleStrings" value="1"> Mangle Strings</label>
                    <label class="chk"><input type="checkbox" name="cffMangleGlobals" value="1"> Mangle Globals</label>
                </div>

                <button type="submit" id="btn">난독화 실행</button>
            </form>

            {"<div class='msg error'>" + error + "</div>" if error else ""}
            {"<div class='msg ok'>✅ 난독화 완료</div>" if result else ""}
        </div>

        <script>
            document.getElementById('obfForm').addEventListener('submit', function() {{
                document.getElementById('btn').disabled = true;
                document.getElementById('btn').textContent = '처리 중...';
            }});
            function copyResult() {{
                const t = document.getElementById('result');
                t.select();
                navigator.clipboard.writeText(t.value);
            }}
        </script>
    </body>
    </html>
    """
    return render_template_string(html)



SUPPORTED_HOST_KEYWORDS = (
    "linkvertise", "link-vertise", "linkvertise.lol",
    "lootlabs", "loot-link", "lootlinks", "lootdest", "lootlink",
    "work.ink", "workink", "workink.net",
    "delta", "keysystem", "getkey", "key-system",
    "platoboost", "pandadevelopment", "rekonise",
)

def is_supported_link(url: str) -> bool:
    u = (url or "").lower()
    return any(k in u for k in SUPPORTED_HOST_KEYWORDS)

def detect_link_type(url: str) -> str:
    u = url.lower()
    if "linkvertise" in u or "link-vertise" in u:
        return "Linkvertise"
    if "lootlabs" in u or "loot-link" in u or "lootlinks" in u or "lootdest" in u or "lootlink" in u:
        return "Lootlabs"
    if "work.ink" in u or "workink" in u:
        return "Work.ink"
    if "delta" in u or "keysystem" in u or "getkey" in u or "key-system" in u:
        return "Delta/Key"
    if "platoboost" in u or "pandadevelopment" in u or "rekonise" in u:
        return "Key System"
    return "Unknown"


def try_linkvertise_lol(url: str) -> str | None:
    """linkvertise.com -> linkvertise.lol domain swap"""
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower()
        if "linkvertise" not in host and "link-vertise" not in host:
            return None
        new_host = host.replace("linkvertise.com", "linkvertise.lol").replace("link-vertise.com", "linkvertise.lol")
        if new_host == host and not host.endswith(".lol"):
            # force .lol
            parts = host.split(".")
            if len(parts) >= 2:
                new_host = ".".join(parts[:-1] + ["lol"])
        scheme = p.scheme or "https"
        path = p.path or "/"
        query = f"?{p.query}" if p.query else ""
        return f"{scheme}://{new_host}{path}{query}"
    except Exception:
        return None


def try_follow_redirects(url: str) -> str | None:
    """Follow redirects with browser-like headers; return final URL if changed."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        final = r.url
        if final and final.rstrip("/") != url.rstrip("/"):
            return final
        # meta refresh
        m = re.search(r'url=["\']?(https?://[^"\'>\s]+)', r.text or "", re.I)
        if m:
            return m.group(1)
        # common destination patterns in page
        for pat in [
            r'["\'](https?://[^"\']*(?:pastebin|rentry|discord\.gg|github|raw\.githubusercontent)[^"\']*)["\']',
            r'destination["\s:=]+["\'](https?://[^"\']+)["\']',
            r'targetUrl["\s:=]+["\'](https?://[^"\']+)["\']',
        ]:
            m = re.search(pat, r.text or "", re.I)
            if m:
                return m.group(1)
    except Exception:
        return None
    return None


def try_public_apis(url: str) -> tuple[bool, str, str]:
    """Try free/public bypass endpoints. Returns (ok, result_or_error, method)."""
    encoded = quote(url, safe="")
    endpoints = [
        ("bypass.vip", f"https://api.bypass.vip/bypass?url={encoded}"),
    ]
    for name, api in endpoints:
        try:
            r = requests.get(api, timeout=25, headers={"User-Agent": "KENDERHOOK/1.0"})
            if r.status_code != 200:
                continue
            data = r.json() if "application/json" in (r.headers.get("content-type") or "") else None
            if isinstance(data, dict):
                if data.get("status") == "success" and data.get("result"):
                    res = str(data["result"])
                    if res.startswith("http"):
                        return True, res, name
                    # shutdown message etc.
                    continue
                if data.get("success") and (data.get("destination") or data.get("result")):
                    res = data.get("destination") or data.get("result")
                    if str(res).startswith("http"):
                        return True, str(res), name
        except Exception:
            continue
    return False, "", ""


def bypass_url(url: str) -> dict:
    url = (url or "").strip()
    if not url:
        return {"ok": False, "incompatible": False, "error": "URL을 입력하세요. / Please enter a URL."}
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    link_type = detect_link_type(url)
    steps = []

    if not is_supported_link(url):
        return {
            "ok": False,
            "type": link_type,
            "incompatible": True,
            "error": "호환되지 않는 링크입니다. / Incompatible link.",
        }

    # 1) Linkvertise .lol swap
    lol = try_linkvertise_lol(url)
    if lol:
        steps.append({"method": "Linkvertise .lol", "url": lol, "note": "이 링크를 열면 광고 없이 이동할 수 있습니다."})

    # 2) Public APIs
    ok, result, method = try_public_apis(url)
    if ok:
        return {"ok": True, "type": link_type, "result": result, "method": method, "steps": steps}

    # 3) Redirect follow
    final = try_follow_redirects(url)
    if final and final != url:
        # if final is still an ad domain, note it
        return {"ok": True, "type": link_type, "result": final, "method": "redirect", "steps": steps}

    if steps:
        return {
            "ok": True,
            "type": link_type,
            "result": steps[0]["url"],
            "method": steps[0]["method"],
            "steps": steps,
            "note": "직접 결과 URL을 찾지 못해 대체 링크를 제공합니다. 아래 링크를 열어보세요.",
        }

    return {
        "ok": False,
        "type": link_type,
        "incompatible": False,
        "error": "바이패스에 실패했습니다. / Bypass failed. The link may be expired or protected.",
        "steps": steps,
    }


@app.route("/bypass", methods=["GET", "POST"])
def bypass_page():
    result_data = None
    input_url = ""

    if request.method == "POST":
        input_url = request.form.get("url", "").strip()
        result_data = bypass_url(input_url)

    # also support ?url=
    if request.method == "GET" and request.args.get("url"):
        input_url = request.args.get("url", "").strip()
        result_data = bypass_url(input_url)

    res_html = ""
    if result_data:
        if result_data.get("ok"):
            res_html = f"""
            <div class="msg ok">
              <div style="margin-bottom:8px;font-size:0.85rem;opacity:0.8">{result_data.get('type','')} · {result_data.get('method','')}</div>
              <div style="word-break:break-all;font-family:monospace;font-size:0.92rem;margin-bottom:12px">{result_data.get('result','')}</div>
              <a class="btn" href="{result_data.get('result','')}" target="_blank" rel="noopener">결과 링크 열기</a>
              <button type="button" class="btn ghost" onclick="navigator.clipboard.writeText('{result_data.get('result','').replace("'", "\\'")}')">복사</button>
              {"<p style='margin-top:12px;font-size:0.85rem;opacity:0.75'>" + result_data.get("note","") + "</p>" if result_data.get("note") else ""}
            </div>
            """
        elif result_data.get("incompatible"):
            res_html = """
            <div class="msg err incompatible">
              <div class="err-ko">호환되지 않는 링크입니다.</div>
              <div class="err-en">Incompatible link.</div>
            </div>
            """
        else:
            res_html = f"""<div class="msg err">{result_data.get('error','실패 / Failed')}</div>"""

    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KENDERHOOK Bypass</title>
<style>
  :root {{
    --bg:#050508; --card:#0c0c14; --border:#1a1a28; --text:#f0f0f5;
    --muted:#8a8aa0; --accent:#ab3cff; --accent2:#7c3aed;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{
    background:var(--bg); color:var(--text);
    font-family:Inter,system-ui,sans-serif; min-height:100vh;
    padding:40px 16px;
  }}
  .wrap {{ max-width:640px; margin:0 auto; }}
  h1 {{
    font-size:1.6rem; font-weight:800; margin-bottom:8px;
    background:linear-gradient(135deg,#c084fc,var(--accent));
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
  }}
  .sub {{ color:var(--muted); margin-bottom:28px; font-size:0.92rem; }}
  .sub a {{ color:#c084fc; }}
  .panel {{
    background:var(--card); border:1px solid var(--border);
    border-radius:14px; padding:24px;
  }}
  label {{ display:block; font-size:0.85rem; font-weight:600; margin-bottom:8px; }}
  input[type=url], input[type=text] {{
    width:100%; background:#07070c; border:1px solid var(--border);
    border-radius:10px; color:var(--text); padding:14px 16px;
    font-size:0.95rem; margin-bottom:16px;
  }}
  input:focus {{ outline:none; border-color:var(--accent); }}
  .btn {{
    display:inline-flex; align-items:center; gap:6px;
    background:linear-gradient(135deg,var(--accent),var(--accent2));
    color:#fff; border:none; border-radius:10px; padding:12px 22px;
    font-weight:600; font-size:0.95rem; cursor:pointer; text-decoration:none;
  }}
  .btn.ghost {{
    background:transparent; border:1px solid var(--border); color:var(--text);
    margin-left:8px;
  }}
  .tags {{ display:flex; flex-wrap:wrap; gap:8px; margin:18px 0 0; }}
  .tag {{
    background:rgba(171,60,255,0.1); border:1px solid rgba(171,60,255,0.25);
    color:#c084fc; padding:6px 12px; border-radius:999px; font-size:0.78rem; font-weight:600;
  }}
  .msg {{ margin-top:20px; padding:16px; border-radius:12px; }}
  .msg.ok {{ background:rgba(34,197,94,0.1); border:1px solid rgba(34,197,94,0.35); }}
  .msg.err {{ background:rgba(248,81,73,0.12); border:1px solid rgba(248,81,73,0.35); color:#f85149; }}
  .msg.incompatible {{ text-align:center; padding:22px 16px; }}
  .msg.incompatible .err-ko {{ font-size:1.08rem; font-weight:700; margin-bottom:6px; color:#f85149; }}
  .msg.incompatible .err-en {{ font-size:0.95rem; color:#f85149; opacity:0.9; }}
  .hint {{ margin-top:24px; color:var(--muted); font-size:0.82rem; line-height:1.6; }}
</style>
</head>
<body>
  <div class="wrap">
    <h1>KENDERHOOK Bypass</h1>
    <p class="sub"><a href="/home">Home</a> · Delta Key · Linkvertise · Lootlabs · Work.ink</p>

    <div class="panel">
      <form method="POST">
        <label for="url">광고 / 키 시스템 링크</label>
        <input type="url" id="url" name="url" placeholder="https://linkvertise.com/... 또는 work.ink / lootlabs / delta key 링크"
               value="{input_url}" required>
        <button class="btn" type="submit">Bypass</button>
      </form>
      <div class="tags">
        <span class="tag">Delta Key</span>
        <span class="tag">Linkvertise</span>
        <span class="tag">Lootlabs</span>
        <span class="tag">Work.ink</span>
      </div>
      {res_html}
    </div>

    <p class="hint">
      사용법: 실행기/키 시스템에서 받은 링크를 붙여넣고 Bypass를 누르세요.<br>
      Linkvertise는 .lol 대체 링크를 우선 제공합니다. 결과는 외부 서비스 상태에 따라 달라질 수 있습니다.
    </p>
  </div>
</body>
</html>
"""
    return render_template_string(html)


@app.route("/home")
def home():
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KENDERHOOK — Free Roblox Script Hub</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #050508;
    --card: #0c0c14;
    --border: #1a1a28;
    --text: #f0f0f5;
    --muted: #8a8aa0;
    --accent: #ab3cff;
    --accent2: #7c3aed;
    --glow: rgba(171, 60, 255, 0.4);
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{ scroll-behavior: smooth; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', system-ui, sans-serif;
    line-height: 1.6;
    overflow-x: hidden;
  }}
  .nav {{
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 28px;
    background: rgba(5,5,8,0.8);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border);
  }}
  .logo {{
    font-weight: 800; font-size: 1.35rem; letter-spacing: -0.02em;
    background: linear-gradient(135deg, #c084fc, var(--accent), #6366f1);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }}
  .nav-right {{ display: flex; gap: 18px; align-items: center; }}
  .nav-links {{ display: flex; gap: 20px; align-items: center; }}
  .nav-links a {{
    color: var(--muted); text-decoration: none; font-size: 0.88rem; font-weight: 500;
    transition: color 0.15s;
  }}
  .nav-links a:hover {{ color: var(--text); }}
  .lang-toggle {{
    display: flex; background: var(--card); border: 1px solid var(--border);
    border-radius: 8px; overflow: hidden; font-size: 0.78rem; font-weight: 600;
  }}
  .lang-toggle button {{
    background: transparent; border: none; color: var(--muted);
    padding: 6px 12px; cursor: pointer; transition: all 0.15s;
  }}
  .lang-toggle button.active {{
    background: rgba(171,60,255,0.2); color: #c084fc;
  }}
  .btn {{
    display: inline-flex; align-items: center; gap: 8px;
    padding: 10px 22px; border-radius: 10px; font-weight: 600; font-size: 0.9rem;
    text-decoration: none; border: none; cursor: pointer; transition: all 0.2s;
  }}
  .btn-primary {{
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    color: #fff; box-shadow: 0 4px 24px var(--glow);
  }}
  .btn-primary:hover {{ transform: translateY(-2px); box-shadow: 0 8px 32px var(--glow); }}
  .btn-ghost {{
    background: transparent; color: var(--text); border: 1px solid var(--border);
  }}
  .btn-ghost:hover {{ border-color: var(--accent); color: #c084fc; }}
  .hero {{
    padding: 150px 24px 60px;
    text-align: center;
    position: relative;
  }}
  .hero::before {{
    content: '';
    position: absolute; top: 0; left: 50%; transform: translateX(-50%);
    width: 700px; height: 500px;
    background: radial-gradient(ellipse, rgba(171,60,255,0.18) 0%, transparent 65%);
    pointer-events: none;
  }}
  .badge {{
    display: inline-block;
    background: rgba(171,60,255,0.12);
    color: #c084fc;
    border: 1px solid rgba(171,60,255,0.35);
    padding: 6px 16px; border-radius: 999px;
    font-size: 0.78rem; font-weight: 600; margin-bottom: 28px;
    letter-spacing: 0.04em; text-transform: uppercase;
  }}
  .hero h1 {{
    font-size: clamp(2.6rem, 7vw, 4.2rem);
    font-weight: 800; line-height: 1.1; margin-bottom: 18px;
    letter-spacing: -0.03em;
  }}
  .hero h1 .grad {{
    background: linear-gradient(135deg, #e9d5ff, var(--accent), #818cf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }}
  .hero p {{
    color: var(--muted); font-size: 1.15rem; max-width: 540px;
    margin: 0 auto 36px;
  }}
  .hero-btns {{ display: flex; gap: 14px; justify-content: center; flex-wrap: wrap; margin-bottom: 48px; }}
  .demo {{
    max-width: 620px; margin: 0 auto;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: hidden;
    text-align: left;
    box-shadow: 0 24px 64px rgba(0,0,0,0.5), 0 0 0 1px rgba(171,60,255,0.08);
  }}
  .demo-bar {{
    display: flex; align-items: center; gap: 7px;
    padding: 12px 16px; background: #0a0a12; border-bottom: 1px solid var(--border);
  }}
  .dot {{ width: 11px; height: 11px; border-radius: 50%; }}
  .dot.r {{ background: #ff5f56; }}
  .dot.y {{ background: #ffbd2e; }}
  .dot.g {{ background: #27c93f; }}
  .demo-bar span {{ color: var(--muted); font-size: 0.78rem; margin-left: 10px; font-weight: 500; }}
  .demo pre {{
    padding: 22px 20px; font-family: 'Cascadia Code', 'Fira Code', 'SF Mono', monospace;
    font-size: 0.86rem; line-height: 1.6; color: #d8b4fe; overflow-x: auto;
    white-space: pre-wrap; word-break: break-all;
  }}
  .demo .cmt {{ color: #6b7280; }}
  .demo .fn {{ color: #67e8f9; }}
  .demo .str {{ color: #86efac; }}
  .stats {{
    display: flex; justify-content: center; gap: 48px; flex-wrap: wrap;
    padding: 40px 24px; border-bottom: 1px solid var(--border);
  }}
  .stat {{ text-align: center; }}
  .stat strong {{
    display: block; font-size: 1.5rem; font-weight: 800;
    background: linear-gradient(135deg, #c084fc, var(--accent));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }}
  .stat span {{ color: var(--muted); font-size: 0.82rem; }}
  .section {{ max-width: 1080px; margin: 0 auto; padding: 80px 24px; }}
  .section-title {{
    text-align: center; font-size: 1.85rem; font-weight: 800; margin-bottom: 10px;
    letter-spacing: -0.02em;
  }}
  .section-sub {{
    text-align: center; color: var(--muted); margin-bottom: 48px; font-size: 1rem;
  }}
  .grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 18px;
  }}
  .card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 14px; padding: 28px 24px;
    transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
  }}
  .card:hover {{
    border-color: rgba(171,60,255,0.45);
    transform: translateY(-3px);
    box-shadow: 0 12px 32px rgba(171,60,255,0.1);
  }}
  .card-icon {{
    width: 46px; height: 46px; border-radius: 12px;
    background: rgba(171,60,255,0.12); display: flex; align-items: center;
    justify-content: center; font-size: 1.35rem; margin-bottom: 16px;
  }}
  .card h3 {{ font-size: 1.08rem; margin-bottom: 8px; font-weight: 700; }}
  .card p {{ color: var(--muted); font-size: 0.9rem; }}
  .games {{ display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }}
  .game-tag {{
    background: var(--card); border: 1px solid var(--border);
    padding: 10px 18px; border-radius: 999px; font-size: 0.88rem; font-weight: 500;
  }}
  .faq {{ max-width: 680px; margin: 0 auto; }}
  .faq-item {{ border-bottom: 1px solid var(--border); padding: 22px 0; }}
  .faq-item strong {{ display: block; margin-bottom: 8px; font-size: 1rem; }}
  .faq-item p {{ color: var(--muted); font-size: 0.92rem; }}
  .faq-item a {{ color: #c084fc; }}
  .cta {{
    text-align: center; padding: 90px 24px 100px;
    position: relative;
  }}
  .cta::before {{
    content: '';
    position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
    width: 500px; height: 300px;
    background: radial-gradient(ellipse, rgba(171,60,255,0.12) 0%, transparent 70%);
    pointer-events: none;
  }}
  .cta h2 {{ font-size: 2rem; font-weight: 800; margin-bottom: 14px; }}
  .cta p {{ color: var(--muted); margin-bottom: 28px; }}
  footer {{
    text-align: center; padding: 28px; border-top: 1px solid var(--border);
    color: var(--muted); font-size: 0.82rem;
  }}
  footer a {{ color: #c084fc; text-decoration: none; }}
  @media (max-width: 720px) {{
    .nav-links a:not(.btn) {{ display: none; }}
    .stats {{ gap: 28px; }}
  }}
</style>
</head>
<body>
  <nav class="nav">
    <div class="logo">KENDERHOOK</div>
    <div class="nav-right">
      <div class="nav-links">
        <a href="#features" data-i18n="nav_features">Features</a>
        <a href="#games" data-i18n="nav_games">Games</a>
        <a href="#faq" data-i18n="nav_faq">FAQ</a>
        <a href="/obf" data-i18n="nav_obf">Obfuscator</a>
        <a href="/bypass">Bypass</a>
      </div>
      <div class="lang-toggle">
        <button type="button" id="btn-en" class="active" onclick="setLang('en')">EN</button>
        <button type="button" id="btn-ko" onclick="setLang('ko')">한</button>
      </div>
      <a class="btn btn-primary" href="{DISCORD_URL}" target="_blank" rel="noopener" data-i18n="nav_discord">Discord</a>
    </div>
  </nav>

  <section class="hero">
    <div class="badge" data-i18n="badge">v2.0 Now Available</div>
    <h1>
      <span data-i18n="hero_title1">The Ultimate</span><br>
      <span class="grad" data-i18n="hero_title2">Roblox Scripting</span>
    </h1>
    <p data-i18n="hero_desc">Undetectable, powerful, and blazing fast. KENDERHOOK delivers the most advanced scripting experience for Roblox with industry-leading security.</p>
    <div class="hero-btns">
      <a class="btn btn-primary" href="{DISCORD_URL}" target="_blank" rel="noopener" data-i18n="btn_discord">Join Discord</a>
      <a class="btn btn-ghost" href="#demo" data-i18n="btn_demo">Live Demo</a>
    </div>

    <div class="demo" id="demo">
      <div class="demo-bar">
        <div class="dot r"></div><div class="dot y"></div><div class="dot g"></div>
        <span data-i18n="console">Console</span>
      </div>
      <pre><span class="cmt" data-i18n="demo_cmt">-- Paste this into your executor</span>
<span class="fn">loadstring</span>(game:<span class="fn">HttpGet</span>(<span class="str">"https://dlzbwydly.onrender.com/"</span>))()</pre>
    </div>
  </section>

  <div class="stats">
    <div class="stat"><strong data-i18n="stat1_v">24/7</strong><span data-i18n="stat1_l">Support</span></div>
    <div class="stat"><strong data-i18n="stat2_v">Fast</strong><span data-i18n="stat2_l">Updates</span></div>
    <div class="stat"><strong data-i18n="stat3_v">Free</strong><span data-i18n="stat3_l">Access</span></div>
    <div class="stat"><strong data-i18n="stat4_v">Safe</strong><span data-i18n="stat4_l">To Use</span></div>
  </div>

  <section class="section" id="features">
    <h2 class="section-title" data-i18n="feat_title">Why Choose KENDERHOOK?</h2>
    <p class="section-sub" data-i18n="feat_sub">Industry-leading features that set us apart from the competition.</p>
    <div class="grid">
      <div class="card">
        <div class="card-icon">🆓</div>
        <h3 data-i18n="f1_t">Completely Free</h3>
        <p data-i18n="f1_d">Get access to all scripts and features without paying anything through our accessible system.</p>
      </div>
      <div class="card">
        <div class="card-icon">⚡</div>
        <h3 data-i18n="f2_t">Always Improving</h3>
        <p data-i18n="f2_d">Our scripts are constantly updated to add new features and stay ahead of game changes.</p>
      </div>
      <div class="card">
        <div class="card-icon">🛡️</div>
        <h3 data-i18n="f3_t">Safe to Use</h3>
        <p data-i18n="f3_d">Designed to be reliable and keep your account safe while you play.</p>
      </div>
      <div class="card">
        <div class="card-icon">💬</div>
        <h3 data-i18n="f4_t">Community Support</h3>
        <p data-i18n="f4_d">Need help? Join our Discord Server for fast and friendly support from staff.</p>
      </div>
      <div class="card">
        <div class="card-icon">🚀</div>
        <h3 data-i18n="f5_t">Fast Updates</h3>
        <p data-i18n="f5_d">We ensure our scripts work after every game update.</p>
      </div>
      <div class="card">
        <div class="card-icon">🤖</div>
        <h3 data-i18n="f6_t">Powerful Automation</h3>
        <p data-i18n="f6_d">Our scripts handle the grind for you so you can focus on having fun.</p>
      </div>
    </div>
  </section>

  <section class="section" id="games">
    <h2 class="section-title" data-i18n="games_title">Supported Games</h2>
    <p class="section-sub" data-i18n="games_sub">Works seamlessly with all major Roblox experiences.</p>
    <div class="games">
      <div class="game-tag">Murder Mystery 2</div>
      <div class="game-tag">Arsenal</div>
      <div class="game-tag">Prison Life</div>
      <div class="game-tag">Blox Fruits</div>
      <div class="game-tag">Brookhaven</div>
      <div class="game-tag">Adopt Me</div>
      <div class="game-tag">Da Hood</div>
      <div class="game-tag" data-i18n="games_more">And more...</div>
    </div>
  </section>

  <section class="section" id="faq">
    <h2 class="section-title" data-i18n="faq_title">Frequently Asked Questions</h2>
    <p class="section-sub" data-i18n="faq_sub">Everything you need to know</p>
    <div class="faq">
      <div class="faq-item">
        <strong data-i18n="q1">How do I use KENDERHOOK?</strong>
        <p data-i18n="a1">Open your script executor, attach it to Roblox, paste the loadstring from the Live Demo above, and press Execute. That's it — no installation required.</p>
      </div>
      <div class="faq-item">
        <strong data-i18n="q2">Is KENDERHOOK free to use?</strong>
        <p data-i18n="a2">Yes, KENDERHOOK is completely free. No hidden fees, no subscriptions, no premium tiers — every feature is available to all users at no cost.</p>
      </div>
      <div class="faq-item">
        <strong data-i18n="q3">Where can I get support?</strong>
        <p data-i18n="a3">Join our Discord Server for fast and friendly support from the community and staff.</p>
      </div>
      <div class="faq-item">
        <strong data-i18n="q4">Is it detectable?</strong>
        <p data-i18n="a4">KENDERHOOK uses advanced methods designed to stay under the radar. We update regularly to maintain maximum safety.</p>
      </div>
    </div>
  </section>

  <section class="cta">
    <h2 data-i18n="cta_title">Ready to get started?</h2>
    <p data-i18n="cta_desc">Join the Discord and start scripting in seconds.</p>
    <a class="btn btn-primary" href="{DISCORD_URL}" target="_blank" rel="noopener" data-i18n="cta_btn">Join Discord</a>
  </section>

  <footer>
    KENDERHOOK © 2026 · <a href="{DISCORD_URL}" target="_blank" rel="noopener">Discord</a> · <a href="/obf" data-i18n="nav_obf">Obfuscator</a>
  </footer>

<script>
const T = {{
  en: {{
    nav_features: "Features", nav_games: "Games", nav_faq: "FAQ", nav_obf: "Obfuscator", nav_discord: "Discord",
    badge: "v2.0 Now Available",
    hero_title1: "The Ultimate", hero_title2: "Roblox Scripting",
    hero_desc: "Undetectable, powerful, and blazing fast. KENDERHOOK delivers the most advanced scripting experience for Roblox with industry-leading security.",
    btn_discord: "Join Discord", btn_demo: "Live Demo",
    console: "Console", demo_cmt: "-- Paste this into your executor",
    stat1_v: "24/7", stat1_l: "Support", stat2_v: "Fast", stat2_l: "Updates",
    stat3_v: "Free", stat3_l: "Access", stat4_v: "Safe", stat4_l: "To Use",
    feat_title: "Why Choose KENDERHOOK?", feat_sub: "Industry-leading features that set us apart from the competition.",
    f1_t: "Completely Free", f1_d: "Get access to all scripts and features without paying anything through our accessible system.",
    f2_t: "Always Improving", f2_d: "Our scripts are constantly updated to add new features and stay ahead of game changes.",
    f3_t: "Safe to Use", f3_d: "Designed to be reliable and keep your account safe while you play.",
    f4_t: "Community Support", f4_d: "Need help? Join our Discord Server for fast and friendly support from staff.",
    f5_t: "Fast Updates", f5_d: "We ensure our scripts work after every game update.",
    f6_t: "Powerful Automation", f6_d: "Our scripts handle the grind for you so you can focus on having fun.",
    games_title: "Supported Games", games_sub: "Works seamlessly with all major Roblox experiences.", games_more: "And more...",
    faq_title: "Frequently Asked Questions", faq_sub: "Everything you need to know",
    q1: "How do I use KENDERHOOK?", a1: "Open your script executor, attach it to Roblox, paste the loadstring from the Live Demo above, and press Execute. That's it — no installation required.",
    q2: "Is KENDERHOOK free to use?", a2: "Yes, KENDERHOOK is completely free. No hidden fees, no subscriptions, no premium tiers — every feature is available to all users at no cost.",
    q3: "Where can I get support?", a3: "Join our Discord Server for fast and friendly support from the community and staff.",
    q4: "Is it detectable?", a4: "KENDERHOOK uses advanced methods designed to stay under the radar. We update regularly to maintain maximum safety.",
    cta_title: "Ready to get started?", cta_desc: "Join the Discord and start scripting in seconds.", cta_btn: "Join Discord"
  }},
  ko: {{
    nav_features: "기능", nav_games: "지원 게임", nav_faq: "FAQ", nav_obf: "난독화", nav_discord: "디스코드",
    badge: "v2.0 출시",
    hero_title1: "최고의", hero_title2: "로블록스 스크립팅",
    hero_desc: "탐지 불가능, 강력하고 빠른 속도. KENDERHOOK은 업계 최고 수준의 보안으로 가장 앞선 로블록스 스크립팅 경험을 제공합니다.",
    btn_discord: "디스코드 참여", btn_demo: "라이브 데모",
    console: "콘솔", demo_cmt: "-- 실행기에 이 코드를 붙여넣으세요",
    stat1_v: "24/7", stat1_l: "지원", stat2_v: "빠른", stat2_l: "업데이트",
    stat3_v: "무료", stat3_l: "이용", stat4_v: "안전", stat4_l: "사용",
    feat_title: "왜 KENDERHOOK인가?", feat_sub: "경쟁사와 차별화되는 업계 최고 수준의 기능.",
    f1_t: "완전 무료", f1_d: "별도의 비용 없이 모든 스크립트와 기능을 이용할 수 있습니다.",
    f2_t: "지속 업데이트", f2_d: "새로운 기능을 추가하고 게임 변경에 맞춰 스크립트를 계속 업데이트합니다.",
    f3_t: "안전한 사용", f3_d: "계정 안전을 지키면서 안정적으로 사용할 수 있도록 설계되었습니다.",
    f4_t: "커뮤니티 지원", f4_d: "도움이 필요하신가요? 디스코드에서 스태프의 빠른 지원을 받으세요.",
    f5_t: "빠른 업데이트", f5_d: "게임 업데이트 이후에도 스크립트가 정상 동작하도록 유지합니다.",
    f6_t: "강력한 자동화", f6_d: "지루한 파밍은 스크립트에 맡기고 플레이에만 집중하세요.",
    games_title: "지원 게임", games_sub: "주요 로블록스 게임에서 원활하게 동작합니다.", games_more: "그 외 다수...",
    faq_title: "자주 묻는 질문", faq_sub: "알아두면 좋은 정보",
    q1: "KENDERHOOK은 어떻게 사용하나요?", a1: "스크립트 실행기를 열고 로블록스에 연결한 뒤, 위 Live Demo의 loadstring을 붙여넣고 Execute를 누르면 됩니다. 별도 설치는 필요 없습니다.",
    q2: "KENDERHOOK은 무료인가요?", a2: "네, 완전 무료입니다. 숨겨진 요금, 구독, 프리미엄 등급 없이 모든 기능을 이용할 수 있습니다.",
    q3: "어디서 도움을 받을 수 있나요?", a3: "디스코드 서버에 참여하시면 커뮤니티와 스태프의 빠른 지원을 받을 수 있습니다.",
    q4: "탐지되나요?", a4: "KENDERHOOK은 탐지를 최소화하는 방식으로 설계되었으며, 안전을 위해 정기적으로 업데이트합니다.",
    cta_title: "시작할 준비가 되셨나요?", cta_desc: "디스코드에 참여하고 바로 스크립팅을 시작하세요.", cta_btn: "디스코드 참여"
  }}
}};

function setLang(lang) {{
  const dict = T[lang] || T.en;
  document.querySelectorAll("[data-i18n]").forEach(el => {{
    const key = el.getAttribute("data-i18n");
    if (dict[key] !== undefined) el.textContent = dict[key];
  }});
  document.getElementById("btn-en").classList.toggle("active", lang === "en");
  document.getElementById("btn-ko").classList.toggle("active", lang === "ko");
  document.documentElement.lang = lang === "ko" ? "ko" : "en";
  try {{ localStorage.setItem("kh_lang", lang); }} catch(e) {{}}
}}

(function() {{
  let lang = "en";
  try {{
    const saved = localStorage.getItem("kh_lang");
    if (saved === "ko" || saved === "en") lang = saved;
    else if (navigator.language && navigator.language.toLowerCase().startsWith("ko")) lang = "ko";
  }} catch(e) {{}}
  setLang(lang);
}})();
</script>
</body>
</html>
"""
    return render_template_string(html)



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
