import re
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

class ThemeInfo:
    """
    CSSテーマの設計仕様（フォント、カラーパレット、タイポグラフィ、文字サイズ等）を
    解析・保持し、Jupyter Notebook やコンソールで見やすく表示するクラス。
    """
    def __init__(self, css_path: Optional[str] = None, theme_name: Optional[str] = None):
        self.css_path = css_path
        self.theme_name = theme_name or "kracie"
        self.colors: Dict[str, Dict[str, str]] = {}
        self.fonts: Dict[str, str] = {}
        self.typography: Dict[str, Dict[str, str]] = {}
        self.templates: list[str] = ["title", "agenda", "normal", "default"]
        
        self._load_and_parse()

    def _load_and_parse(self):
        # デフォルト値の設定（Kracie 5色黄金比テーマ基準）
        default_colors = {
            "primary_accent": ("#FFD500", "メインアクセント (Kracie Yellow)"),
            "accent_light": ("#FFF4B8", "アクセント明 (ライトイエロー)"),
            "accent_dark": ("#b45309", "アクセント暗 (ゴールド/ダークアンバー)"),
            "sub_accent": ("#002BFF", "サブアクセント (Royal Blue)"),
            "sub_accent_light": ("#EBF0FF", "サブアクセント淡 (ソフトブルー)"),
            "text_main": ("#1e293b", "本文テキスト (スレートダーク)"),
            "text_sub": ("#64748b", "補助テキスト (スレートミディアム)"),
            "text_muted": ("#94a3b8", "薄字・注釈 (スレートライト)"),
            "bg_main": ("#ffffff", "スライド背景 (ホワイト)"),
            "bg_dark": ("#0f172a", "ダーク背景 (ディープスレート)"),
            "color_red": ("#ef4444", "警告・エラー・強調 (レッド)"),
            "color_green": ("#10b981", "成功・好調・プラス (グリーン)"),
            "border": ("#e2e8f0", "境界線・枠線 (ボーダー)"),
            "laser_color": ("#ff2a2a", "レーザーポインター発光色"),
        }
        
        default_fonts = {
            "main": '"BIZ UDPGothic", "BIZ UDPゴシック", -apple-system, sans-serif',
            "code": '"SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace',
        }
        
        default_typography = {
            "h1": {"role": "表紙大見出し", "size": "2.5em (~80px)", "weight": "700", "color": "#1e293b"},
            "h2": {"role": "スライドタイトル (黄帯アンダーライン)", "size": "1.55em (~50px)", "weight": "700", "color": "#1e293b"},
            "h3": {"role": "小見出し / セクション名 (青強調)", "size": "1.15em (~37px)", "weight": "700", "color": "#002BFF"},
            "h4": {"role": "カード・コンテナ見出し", "size": "1.0em (~32px)", "weight": "700", "color": "#1e293b"},
            "body": {"role": "本文・パラグラフ", "size": "1.0em (32px 基底)", "weight": "400", "color": "#1e293b"},
            "list_body": {"role": "箇条書きインデント説明文", "size": "0.9em (~28.8px)", "weight": "400", "color": "#1e293b (opacity 0.92)"},
            "memo / point": {"role": "枠付きメモ / ポイントボックス", "size": "0.88em (~28.2px)", "weight": "400", "color": "#1e293b"},
        }
        self.resolution = "1920x1080 (16:9 Full HD)"
        
        # CSSファイルが存在する場合は解析して上書き
        content = ""
        if self.css_path and Path(self.css_path).exists():
            try:
                with open(self.css_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                pass
        else:
            from .asset_encoder import find_default_theme_css
            try:
                theme_file = find_default_theme_css()
                if theme_file and theme_file.exists():
                    self.css_path = str(theme_file)
                    with open(theme_file, "r", encoding="utf-8") as f:
                        content = f.read()
            except Exception:
                pass

        # CSS内の :root 変数をパース
        parsed_vars = {}
        if content:
            matches = re.findall(r'--([a-zA-Z0-9_-]+)\s*:\s*([^;]+);', content)
            for k, v in matches:
                parsed_vars[k.strip()] = v.strip()

        # カラーの統合
        self.colors = {}
        for key, (default_val, desc) in default_colors.items():
            css_var_key = key.replace("_", "-")
            val = parsed_vars.get(css_var_key, default_val)
            self.colors[key] = {"color": val, "description": desc}
            
        if "accent" in parsed_vars:
            self.colors["primary_accent"]["color"] = parsed_vars["accent"]
        if "accent-blue" in parsed_vars:
            self.colors["sub_accent"]["color"] = parsed_vars["accent-blue"]

        # ユーザー追加のカスタムCSS変数（--custom-... 等）も一覧に追加
        for var_name, var_val in parsed_vars.items():
            std_key = var_name.replace("-", "_")
            if std_key not in self.colors and not var_name.startswith("font-") and not var_name.startswith("shadow-"):
                self.colors[std_key] = {"color": var_val, "description": f"カスタム変数 (--{var_name})"}

        # フォントの統合
        self.fonts = {
            "main": parsed_vars.get("font-main", default_fonts["main"]),
            "code": parsed_vars.get("font-code", default_fonts["code"])
        }

        # CSSから解像度とタイポグラフィの動的パース
        base_px = 32
        if content:
            # 基底フォントサイズパース (例: font-size: 32px;)
            base_m = re.search(r'(?:body|\.reveal)\s*\{[^}]*font-size:\s*([0-9]+)px', content)
            if base_m:
                try:
                    base_px = int(base_m.group(1))
                except ValueError:
                    pass

            # スライド高さ (解像度) パース (例: height: 1080px)
            h_m = re.search(r'section(?::not\(\.stack\))?[^}]*height:\s*([0-9]+)px', content)
            if h_m:
                h_val = h_m.group(1)
                if h_val == "1080":
                    self.resolution = "1920x1080 (16:9 Full HD)"
                elif h_val == "1200":
                    self.resolution = "1920x1200 (16:10 WUXGA)"
                elif h_val == "720":
                    self.resolution = "1280x720 (16:9 HD)"
                else:
                    self.resolution = f"Width x {h_val}px"

        # タイポグラフィ定義を実CSSから更新
        self.typography = {}
        for tag, info in default_typography.items():
            self.typography[tag] = dict(info)

        if content:
            # h1 ~ h4 の font-size, font-weight を CSS から動的抽出
            for h in ["h1", "h2", "h3", "h4"]:
                m = re.search(rf'\.reveal\s+{h}\s*\{{([^}}]+)\}}', content)
                if m:
                    block = m.group(1)
                    sz_m = re.search(r'font-size:\s*([^;!]+)', block)
                    wt_m = re.search(r'font-weight:\s*([^;!]+)', block)
                    col_m = re.search(r'color:\s*([^;!]+)', block)
                    if sz_m:
                        raw_sz = sz_m.group(1).strip()
                        # em を px に換算して併記
                        em_m = re.match(r'([0-9.]+)em', raw_sz)
                        if em_m:
                            px_val = round(float(em_m.group(1)) * base_px, 1)
                            raw_sz = f"{raw_sz} (~{px_val}px)"
                        self.typography[h]["size"] = raw_sz
                    if wt_m:
                        self.typography[h]["weight"] = wt_m.group(1).strip()
                    if col_m:
                        c_val = col_m.group(1).strip()
                        if "var(--accent-blue)" in c_val:
                            c_val = self.colors.get("sub_accent", {}).get("color", "#002BFF")
                        elif "var(--text-main)" in c_val:
                            c_val = self.colors.get("text_main", {}).get("color", "#1e293b")
                        self.typography[h]["color"] = c_val

    def to_dict(self) -> Dict[str, Any]:
        return {
            "theme_name": self.theme_name,
            "css_path": self.css_path,
            "fonts": self.fonts,
            "colors": self.colors,
            "typography": self.typography,
            "templates": self.templates
        }

    def __repr__(self) -> str:
        lines = [
            f"=== SlideFactory Theme Specification ({self.theme_name.upper()}) ===",
            f"Resolution: {getattr(self, 'resolution', '1920x1080 (16:9 Full HD)')}",
            f"CSS Source: {self.css_path or 'Built-in Kracie Theme'}",
            "",
            "■ Fonts (フォント):",
            f"  - Main : {self.fonts['main']}",
            f"  - Code : {self.fonts['code']}",
            "",
            "■ Colors (主要カラーパレット):",
        ]
        for k, v in self.colors.items():
            lines.append(f"  - {k:<16} : {v['color']:<9} ({v['description']})")
            
        lines.extend([
            "",
            "■ Typography (タイポグラフィ & 文字サイズ):",
        ])
        for tag, info in self.typography.items():
            lines.append(f"  - {tag:<14} : {info['size']:<16} [Weight: {info['weight']}] - {info['role']}")
            
        laser_col = self.colors.get("laser_color", {}).get("color", "#ff2a2a")
        lines.extend([
            "",
            "■ Presentation Tools (プレゼン機能):",
            f"  - Laser Pointer  : {laser_col} (--laser-color)",
            f"  - Templates      : {', '.join(self.templates)}",
            "=========================================================="
        ])
        return "\n".join(lines)

    def _repr_html_(self) -> str:
        """Jupyter Notebook 上で美しいカード & カラーチップ付きテーブルを表示"""
        color_rows = []
        for k, v in self.colors.items():
            c = v["color"]
            desc = v["description"]
            border = "border: 1px solid #cbd5e1;" if c.lower() in ("#ffffff", "#fff", "white") else ""
            chip = f'<span style="display:inline-block;width:18px;height:18px;vertical-align:middle;border-radius:4px;background-color:{c};{border}margin-right:8px;box-shadow:0 1px 3px rgba(0,0,0,0.15);"></span>'
            color_rows.append(
                f'<tr>'
                f'<td style="padding:6px 10px;font-family:monospace;font-weight:600;">{k}</td>'
                f'<td style="padding:6px 10px;">{chip}<code>{c}</code></td>'
                f'<td style="padding:6px 10px;color:#64748b;font-size:13px;">{desc}</td>'
                f'</tr>'
            )
        colors_table = "\n".join(color_rows)

        typo_rows = []
        for tag, info in self.typography.items():
            px_m = re.search(r'([0-9.]+)px', info.get("size", ""))
            actual_px = f"{px_m.group(1)}px" if px_m else "32px"
            weight = info.get("weight", "700")
            color = info.get("color", "#1e293b")
            font_fam = self.fonts.get("main", "sans-serif").replace('"', "'")

            typo_rows.append(
                f'<tr style="border-bottom:1px solid #f1f5f9;">'
                f'<td style="padding:8px 10px; vertical-align:middle;">'
                f'<span style="font-family:{font_fam}; font-size:{actual_px}; font-weight:{weight}; color:{color}; line-height:1.15; display:inline-block; letter-spacing:-0.01em;">{tag}</span>'
                f'</td>'
                f'<td style="padding:8px 10px; font-weight:600; font-size:13px; vertical-align:middle; white-space:nowrap;">{info["size"]}</td>'
                f'<td style="padding:8px 10px; color:#64748b; font-size:13px; vertical-align:middle; white-space:nowrap;">{weight}</td>'
                f'<td style="padding:8px 10px; font-size:13px; color:#334155; vertical-align:middle;">{info["role"]}</td>'
                f'</tr>'
            )
        typo_table = "\n".join(typo_rows)

        tpl_badges = " ".join([
            f'<span style="background:#f1f5f9;color:#1e293b;padding:3px 8px;border-radius:4px;font-size:12px;font-weight:600;margin-right:4px;border:1px solid #e2e8f0;">{t}</span>'
            for t in self.templates
        ])

        laser_col = self.colors.get("laser_color", {}).get("color", "#ff2a2a")
        laser_glow = self.colors.get("laser_glow", {}).get("color", "rgba(255, 42, 42, 0.7)")
        uid = uuid.uuid4().hex[:8]

        card_presets = [
            ("yellow", "#FFF4B8", "rgba(255, 213, 0, 0.5)", "#1e293b"),
            ("soft_yellow", "rgba(255, 213, 0, 0.15)", "rgba(255, 213, 0, 0.4)", "#1e293b"),
            ("blue", "rgba(0, 43, 255, 0.08)", "rgba(0, 43, 255, 0.35)", "#1e293b"),
            ("soft_blue", "rgba(0, 43, 255, 0.08)", "rgba(0, 43, 255, 0.25)", "#1e293b"),
            ("red", "rgba(239, 68, 68, 0.08)", "rgba(239, 68, 68, 0.35)", "#1e293b"),
            ("soft_red", "rgba(239, 68, 68, 0.08)", "rgba(239, 68, 68, 0.25)", "#1e293b"),
            ("green", "rgba(16, 185, 129, 0.08)", "rgba(16, 185, 129, 0.35)", "#1e293b"),
            ("soft_green", "rgba(16, 185, 129, 0.08)", "rgba(16, 185, 129, 0.25)", "#1e293b"),
            ("gold", "rgba(180, 83, 9, 0.08)", "rgba(180, 83, 9, 0.35)", "#1e293b"),
            ("soft_gold", "rgba(180, 83, 9, 0.08)", "rgba(180, 83, 9, 0.25)", "#1e293b"),
            ("gray", "#f8fafc", "#cbd5e1", "#1e293b"),
            ("dark", "#1e293b", "#334155", "#f8fafc"),
        ]
        card_badges = " ".join([
            f'<span style="background:{bg};border:1px solid {bd};color:{tc};padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600;margin:2px 3px 2px 0;display:inline-block;">{name}</span>'
            for name, bg, bd, tc in card_presets
        ])

        html = f"""
        <style>
        @keyframes laser-ripple-{uid} {{
            0% {{ transform: translate(-50%, -50%) scale(0.4); opacity: 1; }}
            100% {{ transform: translate(-50%, -50%) scale(3.2); opacity: 0; }}
        }}
        #theme-spec-{uid}.laser-enabled {{
            cursor: none !important;
        }}
        #theme-spec-{uid}.laser-enabled * {{
            cursor: none !important;
        }}
        #theme-spec-{uid}.laser-enabled button,
        #theme-spec-{uid}.laser-enabled a {{
            cursor: pointer !important;
        }}
        </style>
        <div id="theme-spec-{uid}" class="laser-enabled" style="position:relative; overflow:hidden; font-family:'BIZ UDPGothic', -apple-system, BlinkMacSystemFont, sans-serif; max-width:980px; border:1px solid #e2e8f0; border-radius:8px; padding:18px 22px; background:#ffffff; box-shadow:0 2px 10px rgba(0,0,0,0.05); color:#1e293b; user-select:none;">
            <!-- レーザーポインター本体 (マウス追従) -->
            <div id="laser-dot-{uid}" style="position:absolute; top:-100px; left:-100px; width:18px; height:18px; border-radius:50%; background:radial-gradient(circle, #ffffff 15%, {laser_col} 60%, rgba(180,0,0,0.9) 100%); pointer-events:none; z-index:99999; transform:translate(-50%, -50%); box-shadow:0 0 8px #ffffff, 0 0 16px {laser_col}, 0 0 32px {laser_glow}, 0 0 48px {laser_glow}; opacity:0; transition:opacity 0.15s ease;"></div>

            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #FFD500; padding-bottom:8px; margin-bottom:14px;">
                <div>
                    <h3 style="margin:0; font-size:18px; color:#1e293b; display:inline-block;">🎨 Slide Theme: <span style="color:#002BFF;">{self.theme_name.upper()}</span></h3>
                    <span style="display:inline-block; margin-left:8px; background:#eff6ff; color:#1d4ed8; font-size:11px; font-weight:700; padding:2px 8px; border-radius:10px; border:1px solid #bfdbfe;">{getattr(self, 'resolution', '1920x1080 (16:9 Full HD)')}</span>
                </div>
                <span style="font-size:12px; color:#64748b;">CSS: {Path(self.css_path).name if self.css_path else 'theme-custom.css (Built-in)'}</span>
            </div>

            <div style="margin-bottom:14px; font-size:13px;">
                <strong>フォントファミリー:</strong>
                <div style="margin-top:4px; padding:6px 10px; background:#f8fafc; border-radius:4px; font-family:monospace; font-size:12px;">
                    <div>• <strong>Main:</strong> {self.fonts['main']}</div>
                    <div>• <strong>Code:</strong> {self.fonts['code']}</div>
                </div>
            </div>

            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px;">
                <!-- カラーパレット -->
                <div>
                    <h4 style="margin:0 0 6px 0; font-size:14px; color:#0f172a;">■ カラーパレット</h4>
                    <table style="width:100%; border-collapse:collapse; font-size:13px; border:1px solid #f1f5f9;">
                        <thead>
                            <tr style="background:#f8fafc; text-align:left; border-bottom:1px solid #e2e8f0;">
                                <th style="padding:6px 10px;">名前</th>
                                <th style="padding:6px 10px;">カラー</th>
                                <th style="padding:6px 10px;">用途</th>
                            </tr>
                        </thead>
                        <tbody>
                            {colors_table}
                        </tbody>
                    </table>
                </div>

                <!-- タイポグラフィ -->
                <div>
                    <h4 style="margin:0 0 6px 0; font-size:14px; color:#0f172a;">■ タイポグラフィ・文字サイズ</h4>
                    <table style="width:100%; border-collapse:collapse; font-size:13px; border:1px solid #f1f5f9;">
                        <thead>
                            <tr style="background:#f8fafc; text-align:left; border-bottom:1px solid #e2e8f0;">
                                <th style="padding:6px 10px;">要素</th>
                                <th style="padding:6px 10px;">サイズ</th>
                                <th style="padding:6px 10px;">太さ</th>
                                <th style="padding:6px 10px;">役割</th>
                            </tr>
                        </thead>
                        <tbody>
                            {typo_table}
                        </tbody>
                    </table>
                    
                    <div style="margin-top:14px;">
                        <h4 style="margin:0 0 4px 0; font-size:13px; color:#0f172a;">■ カードカラー指定 (add_card)</h4>
                        <div style="margin-top:3px; line-height:1.7;">{card_badges}</div>
                    </div>

                    <div style="margin-top:12px;">
                        <h4 style="margin:0 0 4px 0; font-size:13px; color:#0f172a;">■ 利用可能なテンプレート</h4>
                        <div style="margin-top:3px;">{tpl_badges}</div>
                    </div>

                    <!-- レーザーポインター プレビュー体験 & 切り替え -->
                    <div style="margin-top:14px;">
                        <h4 style="margin:0 0 4px 0; font-size:13px; color:#0f172a;">■ レーザーポインター（カード上で動作中）</h4>
                        <div style="margin-top:4px; padding:8px 12px; background:#0b0f19; border-radius:6px; border:1px solid #1e293b; display:flex; align-items:center; justify-content:space-between;">
                            <div style="display:flex; align-items:center; gap:10px;">
                                <span style="display:inline-block; width:14px; height:14px; border-radius:50%; background:radial-gradient(circle, #ffffff 15%, {laser_col} 60%, rgba(180,0,0,0.9) 100%); box-shadow:0 0 6px #ffffff, 0 0 14px {laser_col};"></span>
                                <div>
                                    <div style="font-size:11px; font-weight:700; color:#f8fafc;">実機体験エリア</div>
                                    <div style="font-size:10px; color:#94a3b8;">カード上をポインター追従・クリックで波紋</div>
                                </div>
                            </div>
                            <button id="laser-toggle-{uid}" style="background:{laser_col}; color:#ffffff; font-size:11px; font-weight:700; padding:4px 10px; border-radius:4px; border:none; cursor:pointer; box-shadow:0 0 8px {laser_col}; transition:all 0.2s;">
                                ● LASER ON
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
        (function() {{
            var root = document.getElementById('theme-spec-{uid}');
            var dot = document.getElementById('laser-dot-{uid}');
            var btn = document.getElementById('laser-toggle-{uid}');
            if (!root || !dot) return;

            var isActive = true;

            function updatePointer(e) {{
                if (!isActive) return;
                var rect = root.getBoundingClientRect();
                var x = e.clientX - rect.left;
                var y = e.clientY - rect.top;
                dot.style.left = x + 'px';
                dot.style.top = y + 'px';
                dot.style.opacity = '1';
            }}

            root.addEventListener('mousemove', updatePointer);
            root.addEventListener('mouseenter', function(e) {{
                if (isActive) dot.style.opacity = '1';
                updatePointer(e);
            }});
            root.addEventListener('mouseleave', function() {{
                dot.style.opacity = '0';
            }});

            root.addEventListener('mousedown', function(e) {{
                if (!isActive) return;
                var rect = root.getBoundingClientRect();
                var x = e.clientX - rect.left;
                var y = e.clientY - rect.top;

                var ripple = document.createElement('div');
                ripple.style.position = 'absolute';
                ripple.style.left = x + 'px';
                ripple.style.top = y + 'px';
                ripple.style.width = '32px';
                ripple.style.height = '32px';
                ripple.style.border = '2px solid {laser_col}';
                ripple.style.borderRadius = '50%';
                ripple.style.pointerEvents = 'none';
                ripple.style.zIndex = '99998';
                ripple.style.boxShadow = '0 0 12px {laser_glow}';
                ripple.style.animation = 'laser-ripple-{uid} 0.45s ease-out forwards';
                root.appendChild(ripple);

                setTimeout(function() {{
                    if (ripple.parentNode) ripple.parentNode.removeChild(ripple);
                }}, 480);
            }});

            if (btn) {{
                btn.addEventListener('click', function(e) {{
                    e.stopPropagation();
                    isActive = !isActive;
                    root.classList.toggle('laser-enabled', isActive);
                    if (isActive) {{
                        btn.textContent = '● LASER ON';
                        btn.style.background = '{laser_col}';
                        btn.style.boxShadow = '0 0 8px {laser_col}';
                        dot.style.opacity = '1';
                    }} else {{
                        btn.textContent = '○ LASER OFF';
                        btn.style.background = '#64748b';
                        btn.style.boxShadow = 'none';
                        dot.style.opacity = '0';
                    }}
                }});
            }}
        }})();
        </script>
        """
        return html
