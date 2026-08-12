from flask import Flask, request, redirect, Response, render_template_string
import os
import requests

app = Flask(__name__)

# ─── 설정 ────────────────────────────────────────────────
SCRIPT_FILE = "script.luau"
ADMIN_PASSWORD = "exploit111"
DISCORD_URL = "https://discord.gg/McCGMv9qwk"

# MoonVeil API Key (JWT)
MOONVEIL_API_KEY = os.environ.get(
    "MOONVEIL_API_KEY",
    "mv-secret-2785898a76386e5f64957742c502ff8cc66c5e8e004215b1475390f8d76dc844",
)
MOONVEIL_OBF_URL = "https://moonveil.cc/api/v2/obf"

DEFAULT_SCRIPT = """-- Luau Script
print("Hello from Luau Host")
"""

# ─── 헬퍼 ────────────────────────────────────────────────

def load_script() -> str:
    if os.path.exists(SCRIPT_FILE):
        with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return DEFAULT_SCRIPT


def save_script(content: str) -> None:
    with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write(content)


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
            save_script(script_content)
            current_script = script_content
            message = "✅ 스크립트가 성공적으로 저장되었습니다."

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


@app.route("/home")
def home():
    # 사이트 주소는 요청 호스트 기준으로 표시
    host = request.host_url.rstrip("/")
    html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Script Hub — Ultimate Roblox Scripting</title>
<style>
  :root {{
    --bg: #07070c;
    --card: #0f0f18;
    --border: #1e1e2e;
    --text: #e8e8f0;
    --muted: #8b8ba3;
    --accent: #a855f7;
    --accent2: #6366f1;
    --green: #22c55e;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
    line-height: 1.6;
    overflow-x: hidden;
  }}
  .nav {{
    position: fixed; top: 0; left: 0; right: 0; z-index: 50;
    display: flex; align-items: center; justify-content: space-between;
    padding: 16px 32px;
    background: rgba(7,7,12,0.85);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
  }}
  .logo {{
    font-weight: 800; font-size: 1.25rem;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }}
  .nav-links {{ display: flex; gap: 24px; align-items: center; }}
  .nav-links a {{
    color: var(--muted); text-decoration: none; font-size: 0.9rem; font-weight: 500;
    transition: color 0.15s;
  }}
  .nav-links a:hover {{ color: var(--text); }}
  .btn {{
    display: inline-flex; align-items: center; gap: 8px;
    padding: 10px 20px; border-radius: 10px; font-weight: 600; font-size: 0.9rem;
    text-decoration: none; border: none; cursor: pointer; transition: all 0.15s;
  }}
  .btn-primary {{
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    color: white; box-shadow: 0 4px 20px rgba(168,85,247,0.35);
  }}
  .btn-primary:hover {{ transform: translateY(-1px); box-shadow: 0 6px 28px rgba(168,85,247,0.45); }}
  .btn-ghost {{
    background: transparent; color: var(--text); border: 1px solid var(--border);
  }}
  .btn-ghost:hover {{ border-color: var(--accent); color: var(--accent); }}

  .hero {{
    padding: 140px 24px 80px;
    text-align: center;
    position: relative;
  }}
  .hero::before {{
    content: '';
    position: absolute; top: -20%; left: 50%; transform: translateX(-50%);
    width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(168,85,247,0.15) 0%, transparent 70%);
    pointer-events: none;
  }}
  .badge {{
    display: inline-block;
    background: rgba(168,85,247,0.15);
    color: var(--accent);
    border: 1px solid rgba(168,85,247,0.3);
    padding: 6px 14px; border-radius: 999px;
    font-size: 0.8rem; font-weight: 600; margin-bottom: 24px;
  }}
  .hero h1 {{
    font-size: clamp(2.4rem, 6vw, 3.8rem);
    font-weight: 800; line-height: 1.15; margin-bottom: 20px;
  }}
  .hero h1 span {{
    background: linear-gradient(135deg, var(--accent), #c084fc, var(--accent2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }}
  .hero p {{
    color: var(--muted); font-size: 1.1rem; max-width: 560px;
    margin: 0 auto 36px;
  }}
  .hero-btns {{ display: flex; gap: 14px; justify-content: center; flex-wrap: wrap; }}

  .demo {{
    max-width: 640px; margin: 48px auto 0;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: hidden;
    text-align: left;
    box-shadow: 0 20px 60px rgba(0,0,0,0.4);
  }}
  .demo-bar {{
    display: flex; align-items: center; gap: 8px;
    padding: 12px 16px; background: #12121c; border-bottom: 1px solid var(--border);
  }}
  .dot {{ width: 10px; height: 10px; border-radius: 50%; }}
  .dot.r {{ background: #ff5f56; }}
  .dot.y {{ background: #ffbd2e; }}
  .dot.g {{ background: #27c93f; }}
  .demo-bar span {{ color: var(--muted); font-size: 0.8rem; margin-left: 8px; }}
  .demo pre {{
    padding: 20px; font-family: 'Cascadia Code', 'Fira Code', monospace;
    font-size: 0.88rem; line-height: 1.55; color: #c4b5fd; overflow-x: auto;
  }}
  .demo .cmt {{ color: #6b7280; }}
  .demo .fn {{ color: #67e8f9; }}
  .demo .str {{ color: #86efac; }}

  .section {{
    max-width: 1100px; margin: 0 auto; padding: 80px 24px;
  }}
  .section-title {{
    text-align: center; font-size: 1.9rem; font-weight: 700; margin-bottom: 12px;
  }}
  .section-sub {{
    text-align: center; color: var(--muted); margin-bottom: 48px; font-size: 1rem;
  }}
  .grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 20px;
  }}
  .card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 14px; padding: 28px 24px;
    transition: border-color 0.15s, transform 0.15s;
  }}
  .card:hover {{ border-color: rgba(168,85,247,0.4); transform: translateY(-2px); }}
  .card-icon {{
    width: 44px; height: 44px; border-radius: 10px;
    background: rgba(168,85,247,0.12); display: flex; align-items: center;
    justify-content: center; font-size: 1.3rem; margin-bottom: 16px;
  }}
  .card h3 {{ font-size: 1.1rem; margin-bottom: 8px; }}
  .card p {{ color: var(--muted); font-size: 0.9rem; }}

  .games {{
    display: flex; flex-wrap: wrap; gap: 12px; justify-content: center;
  }}
  .game-tag {{
    background: var(--card); border: 1px solid var(--border);
    padding: 10px 18px; border-radius: 999px; font-size: 0.9rem; font-weight: 500;
  }}

  .faq {{ max-width: 700px; margin: 0 auto; }}
  .faq-item {{
    border-bottom: 1px solid var(--border); padding: 20px 0;
  }}
  .faq-item strong {{ display: block; margin-bottom: 8px; font-size: 1rem; }}
  .faq-item p {{ color: var(--muted); font-size: 0.92rem; }}

  .cta {{
    text-align: center; padding: 80px 24px 100px;
  }}
  .cta h2 {{ font-size: 2rem; margin-bottom: 16px; }}
  .cta p {{ color: var(--muted); margin-bottom: 28px; }}

  footer {{
    text-align: center; padding: 32px; border-top: 1px solid var(--border);
    color: var(--muted); font-size: 0.85rem;
  }}
  footer a {{ color: var(--accent); text-decoration: none; }}
</style>
</head>
<body>
  <nav class="nav">
    <div class="logo">Script Hub</div>
    <div class="nav-links">
      <a href="#features">Features</a>
      <a href="#games">Games</a>
      <a href="#faq">FAQ</a>
      <a href="/obf">Obfuscator</a>
      <a class="btn btn-primary" href="{DISCORD_URL}" target="_blank">Discord</a>
    </div>
  </nav>

  <section class="hero">
    <div class="badge">v2.0 Now Available</div>
    <h1>The Ultimate<br><span>Roblox Scripting</span></h1>
    <p>Undetectable, powerful, and blazing fast. Deliver the most advanced scripting experience with industry-leading security.</p>
    <div class="hero-btns">
      <a class="btn btn-primary" href="{DISCORD_URL}" target="_blank">Join Discord</a>
      <a class="btn btn-ghost" href="#demo">Live Demo</a>
    </div>

    <div class="demo" id="demo">
      <div class="demo-bar">
        <div class="dot r"></div><div class="dot y"></div><div class="dot g"></div>
        <span>Console</span>
      </div>
      <pre><span class="cmt">-- Paste this into your executor</span>
<span class="fn">loadstring</span>(game:<span class="fn">HttpGet</span>(<span class="str">"{host}/"</span>))()</pre>
    </div>
  </section>

  <section class="section" id="features">
    <h2 class="section-title">Why Choose Us?</h2>
    <p class="section-sub">Industry-leading features that set us apart from the competition.</p>
    <div class="grid">
      <div class="card">
        <div class="card-icon">🆓</div>
        <h3>Completely Free</h3>
        <p>Get access to scripts and features without paying anything through our accessible system.</p>
      </div>
      <div class="card">
        <div class="card-icon">⚡</div>
        <h3>Always Improving</h3>
        <p>Scripts are constantly updated to add new features and stay ahead of game changes.</p>
      </div>
      <div class="card">
        <div class="card-icon">🛡️</div>
        <h3>Safe to Use</h3>
        <p>Designed to be reliable and keep your account safe while you play.</p>
      </div>
      <div class="card">
        <div class="card-icon">💬</div>
        <h3>Community Support</h3>
        <p>Need help? Join our Discord for fast and friendly support from staff.</p>
      </div>
      <div class="card">
        <div class="card-icon">🚀</div>
        <h3>Fast Updates</h3>
        <p>We ensure our scripts work after every major game update.</p>
      </div>
      <div class="card">
        <div class="card-icon">🤖</div>
        <h3>Powerful Automation</h3>
        <p>Our scripts handle the grind for you so you can focus on having fun.</p>
      </div>
    </div>
  </section>

  <section class="section" id="games">
    <h2 class="section-title">Supported Games</h2>
    <p class="section-sub">Works seamlessly with major Roblox experiences.</p>
    <div class="games">
      <div class="game-tag">Murder Mystery 2</div>
      <div class="game-tag">Arsenal</div>
      <div class="game-tag">Prison Life</div>
      <div class="game-tag">Blox Fruits</div>
      <div class="game-tag">Brookhaven</div>
      <div class="game-tag">Adopt Me</div>
      <div class="game-tag">And more...</div>
    </div>
  </section>

  <section class="section" id="faq">
    <h2 class="section-title">FAQ</h2>
    <p class="section-sub">Frequently asked questions</p>
    <div class="faq">
      <div class="faq-item">
        <strong>How do I use the script?</strong>
        <p>Open your script executor, attach it to Roblox, paste the loadstring from the demo above, and press Execute.</p>
      </div>
      <div class="faq-item">
        <strong>Is it free to use?</strong>
        <p>Yes. No hidden fees, no subscriptions required for basic access.</p>
      </div>
      <div class="faq-item">
        <strong>Where can I get support?</strong>
        <p>Join our <a href="{DISCORD_URL}" style="color:var(--accent)" target="_blank">Discord server</a> for help from the community and staff.</p>
      </div>
    </div>
  </section>

  <section class="cta">
    <h2>Ready to get started?</h2>
    <p>Join the Discord and start scripting in seconds.</p>
    <a class="btn btn-primary" href="{DISCORD_URL}" target="_blank">Join Discord</a>
  </section>

  <footer>
    Script Hub © 2026 · <a href="{DISCORD_URL}" target="_blank">Discord</a> · <a href="/obf">Obfuscator</a>
  </footer>
</body>
</html>
"""
    return render_template_string(html)



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
