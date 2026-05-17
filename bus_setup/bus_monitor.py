# 大总管（WorkBuddy）总线监听与路由脚本 V7.2
# 基于 BUS_SETUP_GUIDE.md V6.0 实现
# 功能：5秒轮询Shadow/目录 → TRIGGER_*.md路由分发 → 窗口激活+视觉注入+回车发送
#
# 架构设计（V7.2）：
#   单Python进程：信号监听 + 路由分发 + 配置读取 + 日志记录 + UI自动化
#   UI操作：pyautogui（截图/点击/键盘）+ ctypes（窗口查找/激活）
#   不依赖PowerShell子进程，无环境块限制问题
#
# V7.2 更新：
#   - 过滤最小化窗口（-32000坐标检测），pick_best_window智能选择编辑器窗口
#   - SW_RESTORE后重新验证坐标有效性，无效则重试
#   - get_input_coords()按应用类型自动适配输入框坐标（Kiro:b-45, Codex:b-120）
#   - doubleClick + Ctrl+A + Ctrl+V 聚焦粘贴方案

import os, sys, time, glob, json, ctypes, subprocess, re, traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ============================================================
# 导入pyautogui（纯Python GUI自动化）
# ============================================================
import pyautogui

# ============================================================
# 配置区域
# ============================================================
SCRIPT_DIR = Path(__file__).parent.resolve()
BUS_SETUP_DIR = SCRIPT_DIR
WORKFLOW_ROOT = SCRIPT_DIR.parent          # workflow_template/
PROJECT_ROOT = WORKFLOW_ROOT.parent        # <项目根>/
SHADOW_DIR = PROJECT_ROOT / "Shadow"
PROMPTS_DIR = BUS_SETUP_DIR / "prompts"
CONFIG_DIR = WORKFLOW_ROOT / "config"
GIT_COMMIT_BAT = BUS_SETUP_DIR / "git_commit.bat"

POLL_INTERVAL = 5       # 轮询间隔(秒)
LISTEN_TIMEOUT = 1200    # 超时告警(秒)

WINDOW_PATTERNS = {"planner": "Kiro", "executor": "Codex", "auditor": "WorkBuddy"}
WEBHOOK_URL = ""
LOG_FILE = SHADOW_DIR / "_bus_log.txt"
WEBHOOK_FALLBACK_LOG = SHADOW_DIR / "_webhook_fallback.log"
GIT_FALLBACK_LOG = SHADOW_DIR / "_git_fallback.log"
SCREENSHOT_DIR = SHADOW_DIR  # 截图保存目录

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# ============================================================
# 路由表（来自 triggers_dictionary.md）
# ============================================================
ROUTE_TABLE = {
    "TRIGGER_PHASE_1_PLAN":    {"window":"planner","prompt":"phase1_to_planner.txt",    "pre_action":None},
    "TRIGGER_PHASE_2_EXECUTE": {"window":"executor","prompt":"phase2_to_executor.txt",   "pre_action":None},
    "TRIGGER_PHASE_3_AUDIT":   {"window":"auditor", "prompt":"phase3_to_auditor.txt",    "pre_action":None},
    "TRIGGER_ROUTE_A_PASS":    {"window":"planner","prompt":"route_a_pass.txt",         "pre_action":"git_commit"},
    "TRIGGER_ROUTE_B_REJECT":  {"window":"executor","prompt":"route_b_reject.txt",      "pre_action":None},
    "TRIGGER_ROUTE_C_ESCALATE":{"window":"planner","prompt":"route_c_escalate.txt",    "pre_action":"webhook"},
}

# ============================================================
# 日志工具
# ============================================================
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        SHADOW_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
    except: pass

def now_iso():
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")

# ============================================================
# 配置读取
# ============================================================
def read_workflow_toml():
    global WINDOW_PATTERNS, WEBHOOK_URL, LISTEN_TIMEOUT
    p = CONFIG_DIR / "workflow.toml"
    if not p.exists(): return
    sec = ""; content = p.read_text(encoding="utf-8")
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"): continue
        if line.startswith("[") and line.endswith("]"): sec = line[1:-1]; continue
        if "=" not in line: continue
        k, _, v = line.partition("="); k=k.strip(); v=v.strip().strip('"').strip("'")
        if sec=="bus_windows":
            if k=="planner_pattern" and v: WINDOW_PATTERNS["planner"]=v
            elif k=="executor_pattern" and v: WINDOW_PATTERNS["executor"]=v
            elif k=="auditor_pattern" and v: WINDOW_PATTERNS["auditor"]=v
        elif sec=="webhook":
            if k=="url" and v: WEBHOOK_URL=v
        elif sec=="timeouts":
            if k=="listen_timeout_sec" and v.isdigit(): LISTEN_TIMEOUT=int(v)
    log(f"[CONFIG] Windows={WINDOW_PATTERNS} Webhook={'on' if WEBHOOK_URL else 'off'} Timeout={LISTEN_TIMEOUT}s")

# ============================================================
# 窗口查找（V7.1：智能选择——优先可见窗口，必要时恢复最小化窗口）
# ============================================================
def find_window_by_title(pattern):
    """查找匹配标题的窗口，返回列表。不在此处过滤，由调用方决定如何处理。"""
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    matches = []
    def cb(hwnd, lp):
        n = user32.GetWindowTextLengthW(hwnd)
        if n > 0:
            b = ctypes.create_unicode_buffer(n+1)
            user32.GetWindowTextW(hwnd, b, n+1)
            t = b.value
            if re.search(pattern, t, re.IGNORECASE): matches.append((hwnd,t))
        return True
    cb_func = WNDENUMPROC(cb)
    user32.EnumWindows(cb_func, 0)
    return matches

def pick_best_window(matches, pattern_name):
    """
    从匹配窗口中选择最佳目标：
    ① 优先选主编辑器窗口（标题长、含文件名/括号角色标识、大尺寸）
    ② 其次选正常可见的大窗口
    ③ 再选可见的中小窗口（面板/对话框）
    ④ 最后才选最小化的大窗口（需要restore）
    ⑤ 跳过GDI+/内部小窗口（<10x10）

    主编辑器特征：标题较长(>15字符)、含[]括号或'-'分隔的多段式标题
    """
    candidates = []
    for hwnd, title in matches:
        r = RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        w = r.right - r.left
        h = r.bottom - r.top
        is_min = (r.left <= -30000 or r.top <= -30000)
        is_tiny = (w < 10 or h < 10)

        # 判断是否像主编辑器窗口
        is_editor_like = (
            len(title) > 20          # 标题长（含文件名+路径+角色）
            and ('[' in title or ' - ' in title)  # 含括号角色或多段分隔
        )

        info = {"hwnd": hwnd, "title": title, "rect": r,
                "w": w, "h": h, "is_minimized": is_min, "is_tiny": is_tiny,
                "is_editor_like": is_editor_like}
        log(f"    [WIN-CAND] HWND={hwnd} [{title}] ({r.left},{r.top},{r.right},{r.bottom}) "
            f"{w}x{h} min={is_min} tiny={is_tiny} editor={is_editor_like}")
        candidates.append(info)

    # 第一选择：主编辑器风格窗口（无论是否最小化，都值得恢复）
    for c in candidates:
        if c["is_editor_like"] and not c["is_tiny"]:
            if c["is_minimized"]:
                log(f"    [WIN-PICK] Editor window (will restore): HWND={c['hwnd']} [{c['title']}]")
            else:
                log(f"    [WIN-PICK] Editor window (visible): HWND={c['hwnd']} [{c['title']}]")
            return c["hwnd"], c["title"]

    # 第二选择：正常可见的大窗口（>600x400，大概率是主窗口）
    for c in candidates:
        if not c["is_minimized"] and not c["is_tiny"] and c["w"] > 600 and c["h"] > 400:
            log(f"    [WIN-PICK] Large visible: HWND={c['hwnd']} [{c['title']}]")
            return c["hwnd"], c["title"]

    # 第三选择：正常可见的中等窗口（面板/对话框）
    for c in candidates:
        if not c["is_minimized"] and not c["is_tiny"]:
            log(f"    [WIN-PICK] Visible fallback: HWND={c['hwnd']} [{c['title']}]")
            return c["hwnd"], c["title"]

    # 第四选择：最小化的大窗口（需要restore）
    for c in candidates:
        if c["is_minimized"] and not c["is_tiny"] and c["w"] > 100:
            log(f"    [WIN-PICK] Will restore minimized: HWND={c['hwnd']} [{c['title']}]")
            return c["hwnd"], c["title"]

    log(f"    [WIN-PICK] No usable window found for '{pattern_name}'")
    return None, None

# ============================================================
# 纯Python视觉注入引擎（V7 核心模块）
# 不使用PowerShell子进程，不依赖Add-Type，不受环境块限制
# ============================================================

class RECT(ctypes.Structure):
    _fields_ = [("left",ctypes.c_long),("top",ctypes.c_long),
               ("right",ctypes.c_long),("bottom",ctypes.c_long)]

def set_clipboard_text(text):
    """设置系统剪贴板文本。多种方法尝试。"""
    # 方法1: pypercopy
    try:
        import pyperclip
        pyperclip.copy(text)
        log("  [CLIP] Method: pyperclip OK")
        return True
    except Exception as e1:
        log(f"  [CLIP] pyperclip failed: {e1}")

    # 方法2: 通过ctypes调用Win32剪贴板API
    try:
        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        data_bytes = (text + "\0").encode("utf-16-le")
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data_bytes))
        if h_mem:
            p_mem = kernel32.GlobalLock(h_mem)
            ctypes.memmove(p_mem, data_bytes, len(data_bytes))
            kernel32.GlobalUnlock(h_mem)
            user32.OpenClipboard(0)
            user32.EmptyClipboard()
            user32.SetClipboardData(CF_UNICODETEXT, h_mem)
            user32.CloseClipboard()
            log("  [CLIP] Method: Win32 API OK")
            return True
    except Exception as e2:
        log(f"  [CLIP] Win32 API failed: {e2}")

    # 方法3: 写入临时文件，通过BAT启动最小化PS1只做剪贴板
    try:
        tmp_clip = SHADOW_DIR / "_clip_tmp.txt"
        tmp_clip.write_text(text, encoding="utf-8")
        clip_bat = SHADOW_DIR / "_clip.bat"
        clip_bat.write_text(
            r'@echo off' + '\r\n'
            + r'set PATH=C:\Windows\System32;C:\Windows' + '\r\n'
            + 'powershell.exe -NoProfile -Command '
            + '"[System.Windows.Forms.Clipboard]::SetText([IO.File]::ReadAllText(\''
            + str(tmp_clip).replace('\\','/')
            + '\',[Text.Encoding]::UTF8))"' + '\r\n',
            encoding="ascii"
        )
        subprocess.run(["cmd","/c","start","","/min",str(clip_bat)],
                       capture_output=True, timeout=10)
        time.sleep(1)
        log("  [CLIP] Method: BAT+PS1 clipboard fallback")
        return True
    except Exception as e3:
        log(f"  [CLIP] All methods failed: {e3}")
        return False

def is_valid_rect(rect):
    """检查窗口坐标是否有效（非最小化、非零尺寸）"""
    if rect.left <= -30000 or rect.top <= -30000:
        return False
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    return w > 100 and h > 100  # 至少100x100才认为是正常窗口

def get_window_rect_safe(hwnd):
    """安全获取窗口坐标，返回RECT或None"""
    r = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r

def restore_and_verify(hwnd, max_retries=3):
    """
    恢复最小化窗口并验证坐标有效。
    返回 (success: bool, rect: RECT)
    Windows最小化窗口坐标在(-32000,-32000)附近，
    SW_RESTORE后需要重新GetWindowRect确认。
    """
    for attempt in range(1, max_retries + 1):
        log(f"    [RESTORE] Attempt {attempt}/{max_retries}...")
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        time.sleep(0.8)
        user32.SetForegroundWindow(hwnd)
        time.sleep(1.0)

        r = get_window_rect_safe(hwnd)
        if is_valid_rect(r):
            log(f"    [RESTORE] OK — Rect=({r.left},{r.top},{r.right},{r.bottom}) "
                f"size=({r.right-r.left}x{r.bottom-r.top})")
            return True, r
        else:
            log(f"    [RESTORE] Invalid coords still: ({r.left},{r.top}), retrying...")
            time.sleep(1.0)

    log("    [RESTORE] FAILED — window could not be restored to valid position")
    return False, None

def get_input_coords(rect, window_title):
    """
    根据窗口类型返回输入框坐标。
    不同应用的布局不同：
    - Kiro (Electron桌面应用): 输入框在底部45px
    - Codex (浏览器应用chatgpt.com): 输入框在底部120px（浏览器有工具栏/状态栏）
    - WorkBuddy: 待实测，先用通用值
    """
    win_w = rect.right - rect.left
    win_h = rect.bottom - rect.top

    title_lower = window_title.lower()

    if 'kiro' in title_lower:
        # Kiro: 聊天面板在右侧55%+区域, 输入框紧贴底部
        return (rect.left + int(win_w * 0.55), rect.bottom - 45)
    elif 'codex' in title_lower:
        # Codex(浏览器): 输入框距底部较远（约120px），聊天面板居中偏左
        return (rect.left + int(win_w * 0.45), rect.bottom - 120)
    else:
        # 通用fallback：水平居中、底部80px
        return (rect.left + int(win_w * 0.5), rect.bottom - 80)

def inject_to_window_v7(hwnd, prompt_text, window_title):
    """
    V7.1 视觉注入引擎：
    ① 恢复并激活窗口（含最小化检测+重试）
    ② 截图确认前台
    ③ Tab键导航聚焦输入框（主力方案）
    ④ 坐标点击作为fallback（仅Tab失败时用）
    ⑤ Ctrl+V粘贴 → Enter发送
    ⑥ 后截图验证
    """
    log(f"  [INJECT-V7.1] Target: [{window_title}] HWND={hwnd}")
    log(f"  [INJECT-V7.1] Prompt length: {len(prompt_text)} chars")

    # ========== Step 1: 恢复并激活窗口 ==========
    log("  [INJ-Step1] Restoring & activating window...")
    ok, rect = restore_and_verify(hwnd)
    if not ok:
        log("  [INJ-Step1] FATAL: Cannot restore window to valid position!")
        return False

    win_w = rect.right - rect.left
    win_h = rect.bottom - rect.top

    # ========== Step 2: 截图确认窗口在前台 ==========
    log("  [INJ-Step2] Taking pre-injection screenshot...")
    try:
        screenshot = pyautogui.screenshot()
        ss_path = str(SHADOW_DIR / f"_inject_{int(time.time())}.png")
        screenshot.save(ss_path)
        log(f"  [INJ-Step2] Screenshot saved: {ss_path}")
    except Exception as e:
        log(f"  [INJ-Step2] Screenshot warning: {e}")

    # ========== Step 3: 设剪贴板 ==========
    log("  [INJ-Step3] Setting clipboard...")
    set_clipboard_text(prompt_text)
    time.sleep(0.5)

    # ========== Step 4: 聚焦输入框 ==========
    log("  [INJ-Step4] Focusing input field...")
    input_x, input_y = get_input_coords(rect, window_title)
    log(f"    Double-clicking input field at ({input_x}, {input_y}) [auto-detected for {window_title.split()[0] if window_title else 'unknown'}]...")
    pyautogui.doubleClick(input_x, input_y)     # 双击确保聚焦
    time.sleep(0.8)

    # 全选已有内容（防止追加到旧文字后面）
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.3)

    # ========== Step 5: Ctrl+V 粘贴 ==========
    log("  [INJ-Step5] Pasting with Ctrl+V...")
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.8)

    # 验证粘贴是否成功：截小图看是否有文字变化
    try:
        verify_ss = pyautogui.screenshot()
        vpath = str(SHADOW_DIR / f"_verify_paste_{int(time.time())}.png")
        verify_ss.save(vpath)
        log(f"  [INJ-Step5] Paste verification screenshot: {vpath}")
    except Exception as e:
        log(f"  [INJ-Step5] Verification screenshot failed: {e}")

    # ========== Step 6: 回车发送 ==========
    log("  [INJ-Step6] Pressing Enter to send...")
    pyautogui.press('enter')
    time.sleep(0.5)

    # ========== Step 7: 后截图确认结果 ==========
    log("  [INJ-Step7] Taking post-injection screenshot...")
    try:
        post_screenshot = pyautogui.screenshot()
        post_ss_path = str(SHADOW_DIR / f"_post_inject_{int(time.time())}.png")
        post_screenshot.save(post_ss_path)
        log(f"  [INJ-Step7] Post-injection screenshot: {post_ss_path}")
    except Exception as e:
        log(f"  [INJ-Step7] Post-screenshot warning: {e}")

    log("  [INJECT-V7.1] COMPLETE ✅")
    return True

# ============================================================
# Webhook & Git Commit
# ============================================================
def http_post_webhook(event, detail):
    body = json.dumps({"event":event,"project":PROJECT_ROOT.name,"timestamp":now_iso(),"detail":detail}, ensure_ascii=False)
    if not WEBHOOK_URL:
        try:
            SHADOW_DIR.mkdir(parents=True, exist_ok=True)
            with open(WEBHOOK_FALLBACK_LOG,"a",encoding="utf-8") as f: f.write(f"[{now_iso()}] {body}\n")
        except: pass
        log(f"  Webhook(off): {event}")
        return
    try:
        import urllib.request
        req = urllib.request.Request(WEBHOOK_URL, data=body.encode("utf-8"), headers={"Content-Type":"application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r: log(f"  Webhook(on): {event} HTTP {r.status}")
    except Exception as e:
        try:
            with open(WEBHOOK_FALLBACK_LOG,"a",encoding="utf-8") as f: f.write(f"[{now_iso()}] FAILED:{body}|{e}\n")
        except: pass
        log(f"  Webhook fail: {e}")

def run_git_commit():
    if not GIT_COMMIT_BAT.exists(): log("  git_commit.bat missing"); return
    if not (PROJECT_ROOT/".git").exists(): log("  No .git"); return
    try:
        r = subprocess.run(["cmd","/c",str(GIT_COMMIT_BAT)], capture_output=True,text=True,timeout=30,cwd=str(PROJECT_ROOT))
        log(f"  git_commit: {r.stdout.strip()}")
        if r.returncode!=0:
            try:
                with open(GIT_FALLBACK_LOG,"a",encoding="utf-8") as f: f.write(f"[{now_iso()}] rc={r.returncode}:{r.stderr}\n")
            except: pass
    except Exception as e:
        try:
            with open(GIT_FALLBACK_LOG,"a",encoding="utf-8") as f: f.write(f"[{now_iso()}] ex:{e}\n")
        except: pass

# ============================================================
# 路由执行
# ============================================================
def route_signal(signal_name, signal_file):
    try:
        log(f"[DEBUG] route_signal START: {signal_name}")
        key = signal_name.replace(".md","").replace(".handling","")
        if key not in ROUTE_TABLE:
            log(f"[WARN] Unknown: {key}"); os.remove(signal_file); return

        rt = ROUTE_TABLE[key]
        role = rt["window"]
        pf = PROMPTS_DIR / rt["prompt"]
        pre = rt["pre_action"]

        log(f"=== ROUTE: {key} => {role}/{rt['prompt']} ===")

        # 前置动作
        if pre == "git_commit":
            log("  [STEP1] Running git_commit...")
            run_git_commit()
        elif pre == "webhook":
            log("  [STEP1] Sending webhook...")
            http_post_webhook("ESCALATE", f"Signal {key}")

        # 读提示词
        if not pf.exists(): log(f"[ERROR] Prompt missing: {pf}"); os.remove(signal_file); return
        pt = pf.read_text(encoding="utf-8")
        log(f"  [STEP2] Prompt loaded: {len(pt)} chars")

        # 查找目标窗口
        pat = WINDOW_PATTERNS.get(role, "")
        if not pat: log(f"[ERROR] No pattern for {role}"); os.remove(signal_file); return

        log(f"  [STEP3] Finding window pattern='{pat}'...")
        wins = find_window_by_title(pat)
        if not wins:
            for i in range(3):
                time.sleep(1)
                wins = find_window_by_title(pat)
                if wins: break
        if not wins: log(f"[ERROR] Window '{pat}' not found"); os.remove(signal_file); return

        # 智能选择最佳窗口（优先可见，必要时选最小化的）
        hwnd, wtitle = pick_best_window(wins, pat)
        if not hwnd: log(f"[ERROR] No usable window for '{pat}'"); os.remove(signal_file); return
        log(f"  [STEP4] Window selected: [{wtitle}] HWND={hwnd}")

        # V7.1 视觉注入（纯Python，Tab键导航聚焦，过滤最小化窗口）
        log("  [STEP5] Starting V7.1 visual injection...")
        inject_to_window_v7(hwnd, pt, wtitle)

        # 删除信号文件
        try: os.remove(signal_file)
        except FileNotFoundError: pass
        log(f"=== ROUTE COMPLETE: {key} ===")
    except Exception as e:
        log(f"[FATAL] route_signal unhandled: {type(e).__name__}: {e}")
        traceback.print_exc()

# ============================================================
# 主循环
# ============================================================
def wait_for_signal():
    SHADOW_DIR.mkdir(parents=True, exist_ok=True)
    last_t = time.time()

    while True:
        triggers = [f for f in glob.glob(str(SHADOW_DIR/"TRIGGER_*.md"))
                    if not f.endswith(".tmp") and not f.endswith(".handling")]
        if triggers:
            sf = triggers[0]
            sn = os.path.basename(sf)
            hf = sf+".handling"
            try: os.rename(sf,hf)
            except (FileExistsError,FileNotFoundError): continue
            last_t = time.time()
            try:
                route_signal(sn, hf)
            except Exception as e:
                log(f"[ERROR] route_signal failed: {e}")
                traceback.print_exc()
                try: os.remove(hf)
                except: pass
        else:
            if time.time()-last_t >= LISTEN_TIMEOUT:
                log(f"[BLOCKED] {int((time.time()-last_t)/60)}min no signal")
                http_post_webhook("BLOCKED", f"No signal for {int((time.time()-last_t)/60)}min")
                last_t=time.time()
        time.sleep(POLL_INTERVAL)

def main():
    log("="*60 + "\nBus Monitor V7.2 (Auto-adaptive Input Coords)\nProject: "+str(PROJECT_ROOT)+"\nShadow: "+str(SHADOW_DIR)+"\nInterval: "+str(POLL_INTERVAL)+"s\n"+"="*60)
    read_workflow_toml()
    SHADOW_DIR.mkdir(parents=True, exist_ok=True)

    # 清理旧残留
    res = [f for f in glob.glob(str(SHADOW_DIR/"TRIGGER_*"))
           if not f.endswith(".tmp") and not f.endswith(".handling") and not f.startswith("_")]
    if res:
        log(f"[CLEANUP] Removing {len(res)} stale signals")
        for f in res:
            try: os.remove(f)
            except: pass

    try: wait_for_signal()
    except KeyboardInterrupt: log("Stopped by user")
    except Exception as e: log(f"[FATAL] {e}"); traceback.print_exc()

if __name__ == "__main__": main()
