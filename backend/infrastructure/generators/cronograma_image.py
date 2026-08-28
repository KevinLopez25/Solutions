"""
infrastructure/generators/cronograma_image.py  v6

Genera PNG del cronograma con layout 100% dinámico:
- Un único _layout(total_semanas) controla SCALE, fuentes, filas y columnas.
- El PNG siempre tiene un ancho razonable (~2000-2800px) → al insertarse
  en PPTX el texto se ve legible sin importar cuántas semanas haya.
- Pills en UNA SOLA FILA, todos los elementos con rounded corners.
"""

import io
import math
import datetime
import os
from PIL import Image, ImageDraw, ImageFont

# ── Negocio ───────────────────────────────────────────────────────────────────
HORAS_SEMANALES_DEFAULT = 42
SEMANAS_POR_MES    = 4
SEMANAS_POR_SPRINT = 2

# ── Paleta ────────────────────────────────────────────────────────────────────
def _hex(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

VERDES_PRIMARIOS = ["166534", "15803D", "16A34A", "22C55E", "059669", "047857"]
BARRA_COLORES_RGB = [_hex(c) for c in VERDES_PRIMARIOS]
ROLE_COLORS_RGB = [_hex(c) for c in [
    "15803D", "16A34A", "047857", "166534", "22C55E", "059669",
]]
C_GESTION   = _hex("047857")
C_PREP      = _hex("166534")
C_MES       = _hex("15803D")
C_SEM_BG    = _hex("DCFCE7")
C_SEM_TX    = _hex("166534")
C_KO        = _hex("14532D")
C_SPRINT    = _hex("059669")
C_INFO_BG   = _hex("F0FDF4")
C_INFO_BOR  = _hex("16A34A")
C_TITULO    = _hex("14532D")
C_SUBTITULO = _hex("166534")
C_BADGE     = _hex("16A34A")
C_WHITE     = (255, 255, 255)
C_BG        = (255, 255, 255)

# ── Fuentes ───────────────────────────────────────────────────────────────────
_REG  = ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         os.path.join(os.environ.get("WINDIR", r"C:\Windows"),
                      "Fonts", "arial.ttf"),
         os.path.join(os.environ.get("WINDIR", r"C:\Windows"),
                      "Fonts", "calibri.ttf")]
_BOLD = ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         os.path.join(os.environ.get("WINDIR", r"C:\Windows"),
                      "Fonts", "arialbd.ttf"),
         os.path.join(os.environ.get("WINDIR", r"C:\Windows"),
                      "Fonts", "calibrib.ttf")]

def _fnt(paths, size):
    size = max(6, int(size))
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


# ── Layout dinámico ───────────────────────────────────────────────────────────
# Todo el sistema de coordenadas parte de aquí.
# El objetivo es que el PNG resultante tenga ~2000-2600px de ancho
# sin importar el número de semanas.

class L:
    """Contenedor de todas las dimensiones y fuentes del layout."""
    pass


def _build_layout(total_semanas: int) -> L:
    """
    Calcula SCALE, anchos de columna, altos de fila y fuentes de forma
    coordinada para que el PNG siempre sea legible en PPTX.

    Ancho objetivo del área de cronograma (sin col A ni col B):
        grid_w_target = total_semanas * COL_W
    Queremos que grid_w_target + COL_A + COL_B ≈ 2200px (antes de SCALE).
    """
    lo = L()

    # ── 1. Determinar SCALE base ──────────────────────────────────────────
    # SCALE=2 genera píxeles suficientes para nitidez en PPTX sin
    # que el PNG sea tan gigante que el texto quede minúsculo.
    lo.SCALE = 2

    def S(n):
        return int(n * lo.SCALE)

    lo.S = S

    # ── 2. Ancho de columna de semanas ────────────────────────────────────
    # Queremos ancho total del grid ≈ 1600 px (lógicos, antes de SCALE)
    # para semanas ≤ 8 usamos columnas más anchas.
    TARGET_GRID_W = 1600  # px lógicos (se multiplican por SCALE)
    raw_col_w = TARGET_GRID_W / max(total_semanas, 1)
    # Limitar a rango sensato
    raw_col_w = max(40, min(raw_col_w, 120))
    lo.COL_W = S(raw_col_w)

    # ── 3. Resto de columnas (fijas lógicas) ─────────────────────────────
    lo.PAD   = S(6)
    lo.COL_A = S(200)   # etiquetas
    lo.COL_B = S(60)    # Kick-Off / S0 / Sprint 0

    # ── 4. Fuentes — tamaño fijo lógico, legibles en PPTX ────────────────
    # Al usar SCALE=2 con estos tamaños lógicos el texto tiene un tamaño
    # absoluto razonable sin importar cuántas semanas haya.
    # Las fuentes de cabeceras de semana escalan ligeramente si hay muchas.
    sem_fnt_size = S(13) if total_semanas <= 16 else S(11) if total_semanas <= 28 else S(9)

    lo.F = {
        "title":  _fnt(_BOLD, S(22)),
        "sub":    _fnt(_REG,  S(11)),
        "hdr":    _fnt(_BOLD, S(13)),
        "sem":    _fnt(_BOLD, sem_fnt_size),
        "ko":     _fnt(_BOLD, S(11)),
        "pill":   _fnt(_BOLD, S(13)),
        "badge":  _fnt(_BOLD, S(9)),
        "info_t": _fnt(_BOLD, S(9)),
        "info_n": _fnt(_BOLD, S(13)),
        "info_s": _fnt(_REG,  S(9)),
    }

    # ── 5. Alturas de fila ────────────────────────────────────────────────
    # Las filas deben ser suficientemente altas para contener las fuentes.
    lo.ROW_TIT  = S(60)
    lo.ROW_PILL = S(44)
    lo.ROW_MES  = S(32)
    lo.ROW_SEM  = S(26)
    lo.ROW_SPR  = S(26)
    lo.ROW_ACT  = S(32)

    # ── 6. Radios y badges ────────────────────────────────────────────────
    lo.PILL_H  = S(28)
    lo.PILL_R  = S(14)
    lo.HDR_R   = S(5)
    lo.BAR_R   = S(5)
    lo.BADGE_R = S(10)

    return lo


# ── Primitivas ────────────────────────────────────────────────────────────────
def _rr(draw, xy, r, fill, outline=None, olw=1):
    x0, y0, x1, y1 = [int(v) for v in xy]
    r = int(min(r, (x1-x0)//2, (y1-y0)//2))
    if r <= 0:
        draw.rectangle([x0,y0,x1,y1], fill=fill, outline=outline, width=int(olw))
        return
    draw.rectangle([x0+r, y0, x1-r, y1], fill=fill)
    draw.rectangle([x0, y0+r, x1, y1-r], fill=fill)
    for cx, cy in [(x0,y0),(x1-2*r,y0),(x0,y1-2*r),(x1-2*r,y1-2*r)]:
        draw.ellipse([cx, cy, cx+2*r, cy+2*r], fill=fill)
    if outline:
        olw = int(olw)
        draw.arc([x0, y0, x0+2*r, y0+2*r], 180, 270, fill=outline, width=olw)
        draw.arc([x1-2*r, y0, x1, y0+2*r], 270, 360, fill=outline, width=olw)
        draw.arc([x0, y1-2*r, x0+2*r, y1],  90, 180, fill=outline, width=olw)
        draw.arc([x1-2*r, y1-2*r, x1, y1],   0,  90, fill=outline, width=olw)
        draw.line([x0+r, y0, x1-r, y0], fill=outline, width=olw)
        draw.line([x0+r, y1, x1-r, y1], fill=outline, width=olw)
        draw.line([x0, y0+r, x0, y1-r], fill=outline, width=olw)
        draw.line([x1, y0+r, x1, y1-r], fill=outline, width=olw)


def _ctr(draw, rect, text, font, color):
    x0, y0, x1, y1 = [int(v) for v in rect]
    bb = font.getbbox(text)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    draw.text((x0+(x1-x0-tw)//2, y0+(y1-y0-th)//2), text, fill=color, font=font)


def _lft(draw, xy, text, font, color, mw=None):
    x, y = int(xy[0]), int(xy[1])
    if mw:
        while len(text) > 1 and font.getbbox(text)[2] > mw:
            text = text[:-1]
    draw.text((x, y), text, fill=color, font=font)


# ── API pública ───────────────────────────────────────────────────────────────
def generate_cronograma_image(config: dict) -> bytes:
    actividades = config.get("actividades", [])
    roles_raw   = config.get("roles", [])
    nombre_proy = config.get("nombre_proyecto", "Proyecto")
    torre_proy  = config.get("torre", "")
    id_proy     = config.get("id_proyecto", "")
    fecha_str   = config.get("fecha",
                             datetime.date.today().strftime("%d de %B de %Y"))
    horas_semanales = _horas_semanales(config.get("horas_semanales"))
    if not actividades:
        raise ValueError("No hay actividades")

    roles = _norm_roles(roles_raw)

    total_horas = 0
    for act in actividades:
        p = max(1, int(act.get("personas", 1)))
        act["semanas"] = max(1, math.ceil(act["horas"] / horas_semanales / p))
        total_horas += act["horas"]

    total_semanas  = max(a["semanas"] for a in actividades)
    duracion_meses = round(total_semanas / SEMANAS_POR_MES, 1)

    meta = dict(nombre_proyecto=nombre_proy, torre=torre_proy,
                id_proyecto=id_proy, fecha=fecha_str,
                total_horas=total_horas, duracion_meses=duracion_meses,
                horas_semanales=horas_semanales)

    return _render(actividades, roles, total_semanas, meta)


def _horas_semanales(value):
    try:
        horas = float(value)
    except (TypeError, ValueError):
        return HORAS_SEMANALES_DEFAULT
    return horas if horas > 0 else HORAS_SEMANALES_DEFAULT


def _norm_roles(raw):
    out = []
    for r in raw:
        if isinstance(r, dict):
            n = str(r.get("perfil", r.get("rol", ""))).strip()
            if n:
                out.append({"perfil": n,
                            "seniority": str(r.get("seniority","")).strip(),
                            "personas": max(1, int(r.get("personas", 1)))})
        else:
            n = str(r).strip()
            if n:
                out.append({"perfil": n, "seniority": "", "personas": 1})
    return out


# ── Render ────────────────────────────────────────────────────────────────────
def _render(actividades, roles, total_semanas, meta) -> bytes:
    n_act = len(actividades)

    # ── Layout dinámico coordinado ────────────────────────────────────────
    lo = _build_layout(total_semanas)
    F       = lo.F
    S       = lo.S
    PAD     = lo.PAD
    COL_A   = lo.COL_A
    COL_B   = lo.COL_B
    COL_W   = lo.COL_W
    ROW_TIT  = lo.ROW_TIT
    ROW_PILL = lo.ROW_PILL
    ROW_MES  = lo.ROW_MES
    ROW_SEM  = lo.ROW_SEM
    ROW_SPR  = lo.ROW_SPR
    ROW_ACT  = lo.ROW_ACT
    PILL_H   = lo.PILL_H
    PILL_R   = lo.PILL_R
    HDR_R    = lo.HDR_R
    BAR_R    = lo.BAR_R
    BADGE_R  = lo.BADGE_R

    # ── Dimensiones base del cronograma ──────────────────────────────────
    crono_w = COL_A + COL_B + total_semanas * COL_W + PAD * 2

    # ── Pills ─────────────────────────────────────────────────────────────
    pills = []
    for i, rol in enumerate(roles):
        lbl = (f"{rol['perfil']} {rol['seniority']}"
               if rol["seniority"] else rol["perfil"])
        bb  = F["pill"].getbbox(lbl)
        pw  = max(bb[2]-bb[0] + PAD*6, S(80))
        pills.append(dict(label=lbl, w=pw,
                          personas=rol["personas"],
                          color=ROLE_COLORS_RGB[i % len(ROLE_COLORS_RGB)]))

    # Ajustar pills para que siempre quepan en una sola fila dentro de crono_w
    if pills:
        pills_needed = PAD + sum(p["w"] + PAD for p in pills)
        if pills_needed > crono_w:
            avail  = crono_w - PAD * (len(pills) + 1)
            max_pw = max(S(60), avail // len(pills))
            for p in pills:
                if p["w"] > max_pw:
                    p["w"]  = max_pw
                    orig    = p["label"]
                    lbl     = orig
                    inner_w = max_pw - PAD * 4
                    while len(lbl) > 2:
                        bb_t = F["pill"].getbbox(lbl + "…")
                        if bb_t[2] - bb_t[0] <= inner_w:
                            break
                        lbl = lbl[:-1]
                    p["label"] = (lbl.rstrip() + "…") if lbl != orig else orig

    # ── Dimensiones del canvas ────────────────────────────────────────────
    total_w = crono_w

    total_h = (ROW_TIT + ROW_PILL
               + ROW_MES + ROW_SEM + ROW_SPR
               + ROW_ACT * (2 + n_act)
               + PAD * 4)

    img  = Image.new("RGB", (total_w, total_h), C_BG)
    draw = ImageDraw.Draw(img)
    y    = PAD

    # ── 1. Título ──────────────────────────────────────────────────────────
    _lft(draw, (PAD*3, y + PAD),
         "Cronograma del Proyecto", F["title"], C_TITULO)
    sub = (f"Generado el {meta['fecha']}  |  "
           f"Total: {meta['total_horas']}h  |  "
           f"Duración: {meta['duracion_meses']} meses")
    _lft(draw, (PAD*3, y + PAD + S(24)), sub, F["sub"], C_SUBTITULO)
    y += ROW_TIT

    # ── 2. Pills ───────────────────────────────────────────────────────────
    xp  = PAD
    ypc = y + ROW_PILL // 2
    for pd in pills:
        pw  = pd["w"]
        py0 = ypc - PILL_H // 2
        py1 = py0 + PILL_H
        _rr(draw, (xp, py0, xp+pw, py1), PILL_R, pd["color"])
        bb = F["pill"].getbbox(pd["label"])
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
        draw.text((xp+(pw-tw)//2, py0+(PILL_H-th)//2),
                  pd["label"], fill=C_WHITE, font=F["pill"])
        # Badge
        bx = xp + pw - BADGE_R - PAD // 2
        by = py0 - BADGE_R // 2
        draw.ellipse([bx, by, bx+BADGE_R*2, by+BADGE_R*2], fill=C_BADGE)
        num = str(pd["personas"])
        bb2 = F["badge"].getbbox(num)
        nw, nh = bb2[2]-bb2[0], bb2[3]-bb2[1]
        draw.text((bx+BADGE_R-nw//2, by+BADGE_R-nh//2),
                  num, fill=C_WHITE, font=F["badge"])
        xp += pw + PAD
    y += ROW_PILL

    # ── 3. Cabecera: Kick-Off + Meses ────────────────────────────────────
    y_hdr = y
    ch    = ROW_MES + ROW_SEM + ROW_SPR

    # Card info proyecto
    _rr(draw, (PAD, y_hdr + PAD//2, COL_A - PAD, y_hdr + ch - PAD//2),
        S(6), C_INFO_BG, outline=C_INFO_BOR, olw=S(1))
    iy = y_hdr + PAD * 2
    _lft(draw, (PAD*3, iy),
         "INFORMACIÓN DEL PROYECTO", F["info_t"], C_INFO_BOR, mw=COL_A-PAD*6)
    iy += S(11)
    _lft(draw, (PAD*3, iy),
         meta["nombre_proyecto"], F["info_n"], C_TITULO, mw=COL_A-PAD*6)
    if meta["torre"]:
        iy += S(17)
        _lft(draw, (PAD*3, iy),
             f"\u25a1 {meta['torre']}", F["info_s"], C_INFO_BOR, mw=COL_A-PAD*6)
    if meta["id_proyecto"]:
        iy += S(13)
        _lft(draw, (PAD*3, iy),
             f"ID: {meta['id_proyecto']}", F["info_s"], C_SUBTITULO, mw=COL_A-PAD*6)

    # Kick Off
    _rr(draw, (COL_A+PAD//2, y_hdr+PAD//2,
               COL_A+COL_B-PAD//2, y_hdr+ROW_MES-PAD//2), HDR_R, C_KO)
    _ctr(draw, (COL_A, y_hdr, COL_A+COL_B, y_hdr+ROW_MES),
         "Kick Off", F["ko"], C_WHITE)

    # Meses
    xc = COL_A + COL_B
    for m in range(math.ceil(total_semanas / SEMANAS_POR_MES)):
        s0 = m * SEMANAS_POR_MES
        s1 = min(s0 + SEMANAS_POR_MES, total_semanas)
        mw = (s1 - s0) * COL_W
        _rr(draw, (xc+PAD//2, y_hdr+PAD//2,
                   xc+mw-PAD//2, y_hdr+ROW_MES-PAD//2), HDR_R, C_MES)
        _ctr(draw, (xc, y_hdr, xc+mw, y_hdr+ROW_MES),
             f"Mes {m+1}", F["hdr"], C_WHITE)
        xc += mw
    y += ROW_MES

    # ── 4. Semanas ────────────────────────────────────────────────────────
    _rr(draw, (COL_A+PAD//2, y+PAD//2, COL_A+COL_B-PAD//2, y+ROW_SEM-PAD//2),
        HDR_R, C_SEM_BG)
    _ctr(draw, (COL_A, y, COL_A+COL_B, y+ROW_SEM), "S0", F["sem"], C_SEM_TX)
    xc = COL_A + COL_B
    for s in range(total_semanas):
        _rr(draw, (xc+PAD//2, y+PAD//2, xc+COL_W-PAD//2, y+ROW_SEM-PAD//2),
            HDR_R, C_SEM_BG)
        _ctr(draw, (xc, y, xc+COL_W, y+ROW_SEM), f"S{s+1}", F["sem"], C_SEM_TX)
        xc += COL_W
    y += ROW_SEM

    # ── 5. Sprints ────────────────────────────────────────────────────────
    _rr(draw, (COL_A+PAD//2, y+PAD//2, COL_A+COL_B-PAD//2, y+ROW_SPR-PAD//2),
        HDR_R, C_SPRINT)
    _ctr(draw, (COL_A, y, COL_A+COL_B, y+ROW_SPR), "Sprint 0", F["ko"], C_WHITE)
    xc = COL_A + COL_B
    sn  = 1
    for s in range(0, total_semanas, SEMANAS_POR_SPRINT):
        ns  = min(SEMANAS_POR_SPRINT, total_semanas - s)
        spw = ns * COL_W
        _rr(draw, (xc+PAD//2, y+PAD//2, xc+spw-PAD//2, y+ROW_SPR-PAD//2),
            HDR_R, C_SPRINT)
        _ctr(draw, (xc, y, xc+spw, y+ROW_SPR), f"Sprint {sn}", F["hdr"], C_WHITE)
        sn += 1
        xc += spw
    y += ROW_SPR

    # ── 6. Preparar Ambientes ─────────────────────────────────────────────
    _act_row(draw, y, "Preparar Ambientes", COL_A, COL_B, C_PREP,
             F, PAD, COL_A, ROW_ACT, BAR_R)
    y += ROW_ACT

    # ── 7. Actividades ────────────────────────────────────────────────────
    for i, act in enumerate(actividades):
        color  = BARRA_COLORES_RGB[(i + 1) % len(BARRA_COLORES_RGB)]
        bar_px = act["semanas"] * COL_W
        _act_row(draw, y, act["torre"], COL_A+COL_B, bar_px, color,
                 F, PAD, COL_A, ROW_ACT, BAR_R)
        y += ROW_ACT

    # ── 8. Gestión del Proyecto ───────────────────────────────────────────
    _act_row(draw, y, "Gestión del Proyecto",
             COL_A, COL_B + total_semanas * COL_W, C_GESTION,
             F, PAD, COL_A, ROW_ACT, BAR_R)

    # ── Exportar ──────────────────────────────────────────────────────────
    out = io.BytesIO()
    img.save(out, format="PNG", compress_level=1)
    out.seek(0)
    return out.getvalue()


def _act_row(draw, y, label, bar_x, bar_w, fill,
             F, PAD, COL_A, ROW_ACT, BAR_R):
    """Etiqueta col A + barra coloreada, con rounded corners."""
    _rr(draw, (PAD, y+PAD//2, COL_A-PAD, y+ROW_ACT-PAD//2), BAR_R, fill)
    bb = F["hdr"].getbbox("Ag")
    th = bb[3] - bb[1]
    _lft(draw, (PAD*2, y+(ROW_ACT-th)//2),
         label, F["hdr"], C_WHITE, mw=COL_A-PAD*4)
    if bar_w > PAD:
        _rr(draw, (bar_x+PAD//2, y+PAD//2,
                   bar_x+bar_w-PAD//2, y+ROW_ACT-PAD//2), BAR_R, fill)
