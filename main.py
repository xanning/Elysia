import subprocess, sys, re, os, shutil
def resource_path(name):
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, name)

YT_DLP = resource_path(
    "yt-dlp.exe" if os.name == "nt" else "yt-dlp"
)

FFMPEG = resource_path(
    "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
)
HEADERS = [
    "--add-header", "Origin:https://pstream.net",
    "--add-header", "Referer:https://pstream.net/",
    "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0"
]

CODEC_NAMES = {
    "avc1": "H.264",  "avc3": "H.264",
    "hev1": "H.265",  "hvc1": "H.265",
    "vp9":  "VP9",    "av01": "AV1",
    "aac":  "AAC",    "mp4a": "AAC",
    "ec3":  "Dolby Atmos",
    "ac3":  "Dolby Digital",
    "opus": "Opus",   "flac": "FLAC",
}

LANG_NAMES = {
    "af":"Afrikaans","sq":"Albanian","am":"Amharic","ar":"Arabic","hy":"Armenian",
    "az":"Azerbaijani","eu":"Basque","be":"Belarusian","bn":"Bengali","bs":"Bosnian",
    "bg":"Bulgarian","ca":"Catalan","zh":"Chinese","hr":"Croatian","cs":"Czech",
    "da":"Danish","nl":"Dutch","en":"English","et":"Estonian","fi":"Finnish",
    "fr":"French","gl":"Galician","ka":"Georgian","de":"German","el":"Greek",
    "gu":"Gujarati","he":"Hebrew","hi":"Hindi","hu":"Hungarian","is":"Icelandic",
    "id":"Indonesian","ga":"Irish","it":"Italian","ja":"Japanese","kn":"Kannada",
    "kk":"Kazakh","km":"Khmer","ko":"Korean","ku":"Kurdish","lo":"Lao",
    "lv":"Latvian","lt":"Lithuanian","mk":"Macedonian","ms":"Malay","ml":"Malayalam",
    "mt":"Maltese","mr":"Marathi","mn":"Mongolian","ne":"Nepali","nb":"Norwegian",
    "fa":"Persian","pl":"Polish","pt":"Portuguese","pa":"Punjabi","ro":"Romanian",
    "ru":"Russian","sr":"Serbian","si":"Sinhala","sk":"Slovak","sl":"Slovenian",
    "so":"Somali","es":"Spanish","sw":"Swahili","sv":"Swedish","tl":"Tagalog",
    "ta":"Tamil","te":"Telugu","th":"Thai","tr":"Turkish","uk":"Ukrainian",
    "ur":"Urdu","uz":"Uzbek","vi":"Vietnamese","cy":"Welsh","yo":"Yoruba","zu":"Zulu",
    "chi":"Chinese","zho":"Chinese","jpn":"Japanese","kor":"Korean","ara":"Arabic",
    "hin":"Hindi","spa":"Spanish","por":"Portuguese","rus":"Russian","deu":"German",
    "ger":"German","fra":"French","fre":"French","ita":"Italian","pol":"Polish",
    "cze":"Czech","ces":"Czech","tur":"Turkish","eng":"English","nld":"Dutch",
    "swe":"Swedish","nor":"Norwegian","dan":"Danish","fin":"Finnish","hun":"Hungarian",
    "ron":"Romanian","rum":"Romanian","bul":"Bulgarian","hrv":"Croatian","srp":"Serbian",
    "slk":"Slovak","slv":"Slovenian","ukr":"Ukrainian","vie":"Vietnamese","tha":"Thai",
    "heb":"Hebrew","ind":"Indonesian","msa":"Malay","cat":"Catalan","ell":"Greek",
}

def _c(code, t): return f"\033[{code}m{t}\033[0m"
def bold(t):     return _c("1", t)
def dim(t):      return _c("2", t)
def cyan(t):     return _c("96", t)
def blue(t):     return _c("94", t)
def green(t):    return _c("92", t)
def yellow(t):   return _c("93", t)
def magenta(t):  return _c("95", t)
def red(t):      return _c("91", t)
def white(t):    return _c("97", t)
def grey(t):     return _c("90", t)

def vlen(s):
    return len(re.sub(r'\033\[[^m]*m', '', s))

def rpad(s, w):
    return s + " " * max(0, w - vlen(s))

def lpad(s, w):
    return " " * max(0, w - vlen(s)) + s

def lang_label(code):
    return LANG_NAMES.get(code.lower(), code.upper())

def codec_label(s):
    s = s.lower()
    for k, v in CODEC_NAMES.items():
        if k in s:
            return v
    return s.upper()

def res_label(h):
    h = int(h)
    if h >= 2160: return "4K"
    if h >= 1440: return "2K"
    if h >= 1080: return "1080p"
    if h >= 720:  return "720p"
    if h >= 480:  return "480p"
    if h >= 360:  return "360p"
    return f"{h}p"

def term_width():
    return shutil.get_terminal_size((80, 24)).columns

def run_formats(url):
    r = subprocess.run(
        [YT_DLP] + HEADERS + [
            "--ffmpeg-location", FFMPEG,
            "-F", "--no-warnings", url
        ],
        capture_output=True, text=True
    )
    return r.stdout

def parse_formats(raw):
    video, audio = [], []

    for line in raw.splitlines():
        if not line or line.startswith(("ID", "─", "[", "WARNING", "Available")):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        fid = parts[0]

        if "audio only" in line:
            lang_m  = re.search(r'\[(\w+)\]', line)
            ch_m    = re.search(r'\(([^)]+)\)', line)
            tbr_m   = re.search(r'(\d+)k\b', line)
            size_m  = re.search(r'~?\s*([\d.]+)\s*(\w+iB)', line)
            qual_hi = bool(re.search(r'\bhigh\b', line, re.I))
            qual_lo = bool(re.search(r'\blow\b',  line, re.I))

            codec_m   = re.match(r'audio_(\w+)-', fid, re.I)
            codec_raw = codec_m.group(1).lower() if codec_m else ""
            if not codec_raw:
                bm = re.search(r'\b(aac|ec3|ac3|mp4a|opus|flac)\b', line, re.I)
                codec_raw = bm.group(1).lower() if bm else ""
            codec = CODEC_NAMES.get(codec_raw, codec_raw.upper() if codec_raw else "")

            lang_code = lang_m.group(1) if lang_m else "und"
            lang      = lang_label(lang_code)
            channels  = ch_m.group(1) if ch_m else ""
            tbr       = int(tbr_m.group(1)) if tbr_m else 0
            size      = f"{size_m.group(1)} {size_m.group(2)}" if size_m else ""
            qual      = "High" if qual_hi else ("Low" if qual_lo else "")

            audio.append({
                "id": fid, "lang": lang, "lang_code": lang_code,
                "codec": codec, "codec_raw": codec_raw,
                "channels": channels, "tbr": tbr, "size": size, "qual": qual,
            })

        elif re.search(r'\d+x\d+', line):
            res_m   = re.search(r'(\d+)x(\d+)', line)
            fps_m   = re.search(r'\d+x\d+\s+(\d+)', line)
            tbr_m   = re.search(r'(\d+)k\b', line)
            size_m  = re.search(r'~?\s*([\d.]+)\s*(\w+iB)', line)
            codec_m = re.search(r'(hev1|hvc1|avc1|avc3|vp9|av01)\S*', line, re.I)
            hdr     = bool(re.search(r'hdr|smpte2084', line, re.I))

            w, h  = res_m.groups() if res_m else ("?", "?")
            fps   = fps_m.group(1) if fps_m else ""
            tbr   = int(tbr_m.group(1)) if tbr_m else 0
            size  = f"{size_m.group(1)} {size_m.group(2)}" if size_m else ""
            codec = codec_label(codec_m.group(1)) if codec_m else ""

            video.append({
                "id": fid, "w": w, "h": h, "res": res_label(h),
                "fps": fps, "tbr": tbr, "size": size, "codec": codec, "hdr": hdr,
            })

    video.sort(key=lambda x: x["tbr"], reverse=True)

    groups = {}
    for a in audio:
        key = (a["lang"], a["codec_raw"], a["channels"], a["qual"])
        groups.setdefault(key, []).append(a)
    for a in audio:
        key = (a["lang"], a["codec_raw"], a["channels"], a["qual"])
        grp = groups[key]
        a["track_idx"]   = grp.index(a) + 1
        a["track_total"] = len(grp)

    codec_order = {"ec3": 0, "ac3": 1, "aac": 2, "mp4a": 2, "opus": 3, "flac": 4}
    audio.sort(key=lambda a: (
        0 if a["lang"] == "English" else 1,
        a["lang"],
        codec_order.get(a["codec_raw"], 9),
        0 if a["qual"] == "High" else (1 if a["qual"] == "Low" else 2),
        a["track_idx"]
    ))

    return video, audio


def section_header(title):
    W = 54
    print()
    print("  " + grey("┌" + "─" * W + "┐"))
    pad   = W - len(title)
    left  = pad // 2
    right = pad - left
    print("  " + grey("│") + " " * left + bold(white(title)) + " " * right + grey("│"))
    print("  " + grey("└" + "─" * W + "┘"))
    print()


def print_video_menu(items):
    rows = []
    for i, v in enumerate(items, 1):
        num     = cyan(str(i))
        res     = bold(green(v["res"]))
        dims    = blue(f"{v['w']}×{v['h']}")
        fps     = white(f"{v['fps']} fps") if v["fps"] else ""
        codec   = yellow(v["codec"]) if v["codec"] else ""
        bitrate = magenta(f"{v['tbr']} kbps") if v["tbr"] else ""
        size    = grey(f"~{v['size']}") if v["size"] else ""
        hdr     = bold(yellow("  HDR")) if v["hdr"] else ""
        rows.append((num, res, dims, fps, codec, bitrate, size + hdr))

    cols = list(zip(*rows))
    ws   = [max(vlen(c) for c in col) for col in cols]

    for row in rows:
        cells = [lpad(row[0], ws[0])] + [rpad(row[j], ws[j]) for j in range(1, len(row))]
        sep   = "  " + grey("·") + "  "
        print("    " + cells[0] + "   " + sep.join(cells[1:]).rstrip())
    print()


def print_audio_menu(items):
    rows = []
    for i, a in enumerate(items, 1):
        num = cyan(str(i))

        if a["track_total"] > 1:
            lang_col = white(a["lang"]) + grey(f" ·{a['track_idx']}")
        else:
            lang_col = white(a["lang"])

        cod_raw = a["codec_raw"]
        if   cod_raw in ("ec3", "ac3"):  cod_col = magenta
        elif cod_raw in ("aac", "mp4a"): cod_col = blue
        elif cod_raw == "opus":          cod_col = cyan
        else:                            cod_col = yellow
        cod = cod_col(a["codec"]) if a["codec"] else ""

        ch  = grey(a["channels"]) if a["channels"] else ""
        bit = magenta(f"{a['tbr']} kbps") if a["tbr"] else ""

        if   a["qual"] == "High": q = green("High")
        elif a["qual"] == "Low":  q = yellow("Low")
        else:                     q = ""

        rows.append((num, lang_col, cod, ch, bit, q))

    cols = list(zip(*rows))
    ws   = [max(vlen(c) for c in col) for col in cols]

    prev_lang = None
    dot_w = sum(ws[1:]) + (len(ws) - 2) * 5
    for row, a in zip(rows, items):
        if prev_lang is not None and a["lang"] != prev_lang:
            print("       " + grey("·" * dot_w))
        prev_lang = a["lang"]

        cells = [lpad(row[0], ws[0])] + [rpad(row[j], ws[j]) for j in range(1, len(row))]
        sep   = "  " + grey("·") + "  "
        print("    " + cells[0] + "   " + sep.join(cells[1:]).rstrip())
    print()


def pick(n, label):
    while True:
        try:
            raw = input(bold(f"  ›  {label}: ")).strip()
            v   = int(raw)
            if 1 <= v <= n:
                return v
        except (ValueError, EOFError):
            pass
        except KeyboardInterrupt:
            print(red("\n  Aborted.\n"))
            sys.exit(0)
        print(red(f"    Enter a number from 1 to {n}"))


def make_ytdlp_cmd(fmt_id, url, outfile):
    return (
        [YT_DLP] + HEADERS
        + [
            "--ffmpeg-location", FFMPEG,
            "-f", fmt_id,
            "-o", outfile,
            "--newline",
            "--no-warnings",
            "--concurrent-fragments", "2",
            "--http-chunk-size", "10M",
            "--buffer-size", "16K",
            "--no-part",
            "--retries", "10",
            "--fragment-retries", "10",
            "--retry-sleep", "linear=1::2",
            "--progress-template",
            "%(progress.status)s %(progress._percent_str)s %(progress._speed_str)s %(progress._eta_str)s %(progress.fragment_index)s %(progress.fragment_count)s",
            url
        ]
    )


def draw_dual_progress(v_pct, v_spd, v_eta, a_pct, a_spd, a_eta, v_done, a_done):
    bar_w = 24

    def bar(pct, done):
        filled = int(bar_w * pct / 100)
        if done:
            return green("█" * bar_w)
        return green("█" * filled) + grey("░" * (bar_w - filled))

    def row(label, pct, spd, eta, done):
        if done:
            right = green("done")
        else:
            right = cyan(f"{spd:<12}") + "  " + yellow(f"ETA {eta}" if eta else "")
        return f"  {grey(label)}  {bar(pct, done)}  {white(f'{pct:5.1f}%')}  {right}"

    sys.stdout.write("\033[2A\033[J")
    print(row("video", v_pct, v_spd, v_eta, v_done))
    print(row("audio", a_pct, a_spd, a_eta, a_done))
    sys.stdout.flush()


def parse_progress_line(line):
    """Return (status, pct, speed, eta) from a yt-dlp --newline progress line."""
    parts  = line.split()
    status = parts[0].lower() if parts else ""
    pct, speed, eta = 0.0, "", ""
    if len(parts) > 1:
        try: pct = float(parts[1].rstrip("%"))
        except ValueError: pass
    if len(parts) > 2: speed = parts[2]
    if len(parts) > 3: eta   = parts[3]
    return status, pct, speed, eta


def run_download(v_id, a_id, url, outname):
   
    if a_id is None:
        print()
        print()
        proc = subprocess.Popen(
            make_ytdlp_cmd(v_id, url, f"{outname}.mp4"),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1
        )
        for line in proc.stdout:
            parts = line.strip().split()
            if parts and parts[0].lower() == "downloading":
                try:    pct = float(parts[1].rstrip("%"))
                except: pct = 0.0
                spd = parts[2] if len(parts) > 2 else ""
                draw_dual_progress(pct, spd, 0, "", False, True)
        proc.wait()
        return proc.returncode

    tmp_v = f"{outname}.video.tmp"
    tmp_a = f"{outname}.audio.tmp"
    out   = f"{outname}.mp4"

   
    proc_v = subprocess.Popen(
        make_ytdlp_cmd(v_id, url, tmp_v),
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, bufsize=8192
    )
    proc_a = subprocess.Popen(
        make_ytdlp_cmd(a_id, url, tmp_a),
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, bufsize=8192
    )

    state = {
        "v": {"pct": 0.0, "spd": "", "eta": "", "done": False},
        "a": {"pct": 0.0, "spd": "", "eta": "", "done": False},
    }

   
    print()
    print()

    import threading, queue

    q = queue.Queue()

    def reader(proc, key):
        for line in proc.stdout:
            q.put((key, line.strip()))
        proc.wait()
        q.put((key, None))  

    t_v = threading.Thread(target=reader, args=(proc_v, "v"), daemon=True)
    t_a = threading.Thread(target=reader, args=(proc_a, "a"), daemon=True)
    t_v.start()
    t_a.start()

    done_count = 0

    try:
        while done_count < 2:
            key, line = q.get()
            if line is None:
                done_count += 1
                state[key]["done"] = True
                state[key]["pct"]  = 100.0
                state[key]["eta"]  = ""
            else:
                status, pct, spd, eta = parse_progress_line(line)
                if status == "downloading":
                    state[key]["pct"] = pct
                    state[key]["spd"] = spd
                    state[key]["eta"] = eta
                elif status == "finished":
                    state[key]["done"] = True
                    state[key]["pct"]  = 100.0
                    state[key]["eta"]  = ""

            draw_dual_progress(
                state["v"]["pct"], state["v"]["spd"], state["v"]["eta"],
                state["a"]["pct"], state["a"]["spd"], state["a"]["eta"],
                state["v"]["done"], state["a"]["done"],
            )

    except KeyboardInterrupt:
        proc_v.terminate()
        proc_a.terminate()
        proc_v.wait()
        proc_a.wait()
        for f in (tmp_v, tmp_a):
            try: os.remove(f)
            except: pass
        print(red("\n\n  Download cancelled.\n"))
        sys.exit(0)

    if proc_v.returncode != 0 or proc_a.returncode != 0:
        return max(proc_v.returncode or 0, proc_a.returncode or 0)

   
    print()
    sys.stdout.write(grey("  · merging …"))
    sys.stdout.flush()

    merge = subprocess.run(
        [FFMPEG, "-y",
         "-i", tmp_v, "-i", tmp_a,
         "-c", "copy", out],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    for f in (tmp_v, tmp_a):
        try: os.remove(f)
        except: pass

    sys.stdout.write(f"\r{' ' * 20}\r")
    sys.stdout.flush()

    return merge.returncode


def banner():
    print()
    print()
    
    print("  " + grey("         ·"))
    print("  " + grey("      ·  ·  ·"))
    print("  " + grey("   ·     ·     ·"))
    
    print("  " + grey("·        ") + bold(white("E L Y S I A")) + grey("        ·"))
    print("  " + grey("   ·     ") + grey("media downloader") + grey("     ·"))
    
    print("  " + grey("      ·  ·  ·"))
    print("  " + grey("         ·"))
    print()
    print()

def main():
    os.system("")
    banner()

    try:
        url = input(bold("  URL  ›  ")).strip()
    except KeyboardInterrupt:
        sys.exit(0)

    print(dim("\n  · fetching formats\n"))
    raw          = run_formats(url)
    video, audio = parse_formats(raw)

    if not video:
        print(red("\n  no video streams found.\n"))
        sys.exit(1)

    section_header("V I D E O   Q U A L I T Y")
    print_video_menu(video)
    vi = pick(len(video), "select video") - 1
    v  = video[vi]

    a = None
    if audio:
        section_header("A U D I O   T R A C K")
        print_audio_menu(audio)
        ai = pick(len(audio), "select audio") - 1
        a  = audio[ai]

    print()
    try:
        outname = input(bold("  filename (without extension)  ›  ")).strip() or "output"
    except KeyboardInterrupt:
        sys.exit(0)

    W = 54
    def card_row(label, value):
        inner  = f"  {grey(label)}  {value}"
        rspace = W - vlen(inner)
        print("  " + grey("│") + inner + " " * max(rspace, 1) + grey("│"))

    print()
    print("  " + grey("┌" + "─" * W + "┐"))
    card_row("video ", f"{bold(green(v['res']))}  {blue(v['w']+'×'+v['h'])}  {yellow(v['codec'])}  {magenta(str(v['tbr'])+'kbps')}  {grey('~'+v['size'])}")
    if a:
        q_tag = f"  {green('High')}" if a["qual"] == "High" else (f"  {yellow('Low')}" if a["qual"] == "Low" else "")
        c_col = magenta if a["codec_raw"] in ("ec3","ac3") else blue
        card_row("audio ", f"{white(a['lang'])}  {c_col(a['codec'])}  {grey(a['channels'])}{q_tag}")
    card_row("file  ", yellow(outname + ".mp4"))
    print("  " + grey("└" + "─" * W + "┘"))
    print()
    print(grey("  · · ·  downloading  ·  ctrl+c to cancel"))
    print()

    if a:
        code = run_download(v["id"], a["id"], url, outname)
    else:
        
        code = run_download(v["id"], None, url, outname)

    if code == 0:
        print(green(f"  ✓  {bold(outname+'.mp4')}") + white("  saved successfully"))
    else:
        print(red(f"  ✗  something went wrong (exit {code})"))
    print()


if __name__ == "__main__":
    main()
