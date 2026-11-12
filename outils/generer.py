#!/usr/bin/env python3
"""Génère les maquettes à partir des fiches prospects.

Entrée : prospects/<slug>/fiche.json   (petite fiche écrite par Claude ou à la main)
Sortie : <slug>/index.html, theme.css, main.js, img/   (publiés par GitHub Pages)

Usage : python outils/generer.py            → toutes les fiches
        python outils/generer.py <slug>     → une seule
"""
import colorsys, html, json, re, shutil, sys, urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
MODELES = RACINE / "modele"
COULEUR_DEFAUT = "#d9480f"   # orange dépanneuse (volontairement différent de la landing d'origine)

# Couleurs de la landing d'origine → remplacées par le thème du prospect
ORIGINE_HEX = {"dark": "#0b2a1e", "green": "#2f7d1f", "hover": "#266a18", "light": "#6cc04a", "soft": "#eaf4e4"}
ORIGINE_RGB = {"dark2": "8, 30, 21", "dark": "11, 42, 30", "light": "108, 192, 74", "green": "47, 125, 31"}

e = lambda s: html.escape(str(s or ""), quote=True)


# ---------- Couleurs ----------
def hex_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3: h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

def rgb_hex(r, g, b):
    return "#%02x%02x%02x" % tuple(round(max(0, min(1, v)) * 255) for v in (r, g, b))

def luminance(rgb):
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = map(f, rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contraste_blanc(rgb):
    return 1.05 / (luminance(rgb) + 0.05)

def theme(base):
    """Palette complète dérivée d'une seule couleur de marque."""
    h, l, s = colorsys.rgb_to_hls(*hex_rgb(base))
    s = max(s, 0.45)
    # Bouton : assez foncé pour un texte blanc lisible (contraste AA ≥ 4,5)
    lb = min(l, 0.5)
    while contraste_blanc(colorsys.hls_to_rgb(h, lb, s)) < 4.6 and lb > 0.05:
        lb -= 0.01
    btn = colorsys.hls_to_rgb(h, lb, s)
    t = {
        "green": rgb_hex(*btn),
        "hover": rgb_hex(*colorsys.hls_to_rgb(h, lb * 0.85, s)),
        "light": rgb_hex(*colorsys.hls_to_rgb(h, 0.62, min(1, s + 0.1))),
        "soft": rgb_hex(*colorsys.hls_to_rgb(h, 0.94, min(0.6, s))),
        "dark": rgb_hex(*colorsys.hls_to_rgb(h, 0.11, min(0.6, s))),
        "dark2": rgb_hex(*colorsys.hls_to_rgb(h, 0.075, min(0.6, s))),
    }
    return t

def rgb_txt(hx):
    return ", ".join(str(round(v * 255)) for v in hex_rgb(hx))

def css_theme(css, t):
    for k, v in ORIGINE_HEX.items():
        css = re.sub(re.escape(v), t[k], css, flags=re.I)
    css = re.sub("#08221a", t["dark2"], css, flags=re.I)   # fond du pied de page
    css = css.replace("%23" + ORIGINE_HEX["green"][1:], "%23" + t["green"][1:])
    for k, v in ORIGINE_RGB.items():
        css = css.replace(f"rgba({v},", f"rgba({rgb_txt(t[k])},")
    css += """
/* Logo texte (quand le prospect n'a pas de logo exploitable) */
.logo_texte { font-family: var(--font-head); font-weight: 800; font-size: 1.6rem; line-height: 1; color: var(--color-ink); text-transform: uppercase; letter-spacing: .02em; }
.logo_texte span { color: var(--color-green); }
.footer_component .logo_texte { color: #fff; }
.footer_component .logo_texte span { color: var(--color-green-light); }
.footer_logo.is-texte { background: none; padding: 0; }
.footer_logo.is-texte .logo_texte { font-size: 2rem; }
"""
    return css


# ---------- Téléphone ----------
def telephone(brut):
    chiffres = re.sub(r"\D", "", brut or "")
    if chiffres.startswith("33"): chiffres = "0" + chiffres[2:]
    if len(chiffres) != 10: raise SystemExit(f"téléphone invalide : {brut!r}")
    affiche = " ".join(chiffres[i:i + 2] for i in range(0, 10, 2))
    return affiche, "+33" + chiffres[1:], "33" + chiffres[1:], chiffres[:2] in ("06", "07")


# ---------- Images ----------
def telecharger(url, cible):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh) maquettes"})
    with urllib.request.urlopen(req, timeout=30) as r, open(cible, "wb") as f:
        shutil.copyfileobj(r, f)
    if cible.stat().st_size < 2000:
        cible.unlink(); raise OSError("image vide")

def recuperer_images(fiche, dossier_fiche, sortie):
    """Télécharge logo + photos une seule fois dans <slug>/img/. Renvoie les chemins relatifs."""
    img = sortie / "img"; img.mkdir(parents=True, exist_ok=True)
    def une(src, nom):
        if not src: return None
        for ext in (".jpg", ".png", ".webp", ".svg"):
            if (img / (nom + ext)).exists(): return f"img/{nom}{ext}"
        local = dossier_fiche / src
        ext = Path(src.split("?")[0]).suffix.lower()
        ext = ext if ext in (".jpg", ".jpeg", ".png", ".webp", ".svg") else ".jpg"
        ext = ".jpg" if ext == ".jpeg" else ext
        cible = img / (nom + ext)
        try:
            if local.exists(): shutil.copy(local, cible)
            else: telecharger(src, cible)
            return f"img/{nom}{ext}"
        except Exception as err:
            print(f"  ⚠ image ignorée ({nom}) : {err}")
            return None
    logo = une(fiche.get("logo"), "logo")
    photos = [p for i, s in enumerate(fiche.get("photos", [])) if (p := une(s, f"photo-{i + 1}"))]
    return logo, photos

def placeholder(sortie, t):
    """Visuel neutre aux couleurs du prospect quand il manque des photos."""
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 900"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t['dark']}"/><stop offset="1" stop-color="{t['green']}"/></linearGradient></defs><rect width="1200" height="900" fill="url(#g)"/><g transform="translate(450 300) scale(12.5)" fill="none" stroke="{t['light']}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" opacity=".55"><path d="M1 16V6h10v10M11 9h5l3 4v3h-2M1 16h2m6 0h6"/><circle cx="6" cy="17" r="2"/><circle cx="17" cy="17" r="2"/></g></svg>"""
    (sortie / "img").mkdir(parents=True, exist_ok=True)
    (sortie / "img" / "visuel.svg").write_text(svg, encoding="utf-8")
    return "img/visuel.svg"


# ---------- Blocs HTML ----------
ETOILES = '<span class="stars" aria-label="5 étoiles">' + '<svg aria-hidden="true"><use href="#i-star"/></svg>' * 5 + "</span>"

def logo_texte(nom):
    mots = nom.split()
    if len(mots) > 1:
        return f'<span class="logo_texte">{e(" ".join(mots[:-1]))} <span>{e(mots[-1])}</span></span>'
    return f'<span class="logo_texte">{e(nom)}</span>'

def construire(fiche, logo, photos, visuel, t):
    nom = fiche["nom"].strip()
    tel, e164, wa_tel, mobile = telephone(fiche["tel"])
    wa = telephone(fiche["whatsapp"])[2] if fiche.get("whatsapp") else wa_tel
    horaires = fiche.get("horaires") or "7j/7"
    zone_en = fiche.get("zone_en") or "dans votre secteur"          # ex. « dans le Val-de-Marne »
    zone_nom = fiche.get("zone_nom") or "Tout le secteur"            # ex. « Val-de-Marne et alentours »
    deps = fiche.get("departements") or []
    agr = (fiche.get("agrement") or "").strip()
    rachat = fiche.get("rachat", True)
    email = (fiche.get("email") or "").strip()
    avis = fiche.get("avis") or {}

    P = photos or [visuel]
    p = lambda i: P[i % len(P)]

    v = {
        "nom": e(nom),
        "nom_js": e(nom).replace("'", "\\'"),
        "tel": tel, "tel_e164": e164, "wa": wa,
        "horaires": e(horaires),
        "c_dark": t["dark"],
        "titre_page": e(f"Enlèvement d'épave gratuit {zone_en} | {nom}" + (" – Centre VHU agréé" if agr else "")),
        "meta_desc": e(f"Enlèvement d'épave gratuit {zone_en}, {horaires}. " + (f"Centre VHU agréé n° {agr}. " if agr else "") + f"Tél. {tel}"),
        "favicon": f'<link rel="icon" href="{logo}">' if logo else "",
        "logo_nav": f'<img src="{logo}" alt="Logo {e(nom)}" style="height:60px;width:auto">' if logo else logo_texte(nom),
        "logo_footer": (f'<div class="footer_logo"><img src="{logo}" alt="Logo {e(nom)}"></div>' if logo
                        else f'<div class="footer_logo is-texte">{logo_texte(nom)}</div>'),
        "hero_sous_titre": e(fiche.get("hero_sous_titre") or f"{fiche.get('zone_phrase') or 'Intervention rapide sur tout le secteur.'} On se déplace sous 24h."),
        "perk_delai": e(fiche.get("perk_delai") or f"Intervention rapide, {horaires}"),
        "zone_en": e(zone_en), "zone_nom": e(zone_nom),
        "zones_texte": e(fiche.get("zones_texte") or f"{zone_nom}, {horaires}. Autres secteurs sur demande."),
        "cta_texte": e("Gratuit, " + ("agréé préfecture, " if agr else "") + f"partout {zone_en}."),
        "photo_hero": p(0), "photo_s1": p(1), "photo_s2": p(2), "photo_fond1": p(3),
        "photo_e1": p(4), "photo_e2": p(5), "photo_e3": p(6), "photo_fond2": p(7),
    }

    # Agrément VHU : affiché uniquement s'il est renseigné (jamais inventé)
    if agr:
        badge = '<img src="../modele/communs/centre-vhu-agree.png" alt="Logo officiel Centre VHU agréé"'
        v["bloc_vhu_hero"] = f'<div class="hero_vhu">{badge} width="109" height="58"><span><strong>Centre VHU agréé</strong> n° {e(agr)}</span></div>'
        v["bloc_vhu_footer"] = f'<div class="footer_vhu">{badge} width="101" height="54" loading="lazy"><span>Agrément préfectoral<br>n° {e(agr)}</span></div>'
        v["perk_2"] = f'<div class="perks_item" data-reveal><span class="perks_icon"><svg class="" aria-hidden="true"><use href="#i-shield"/></svg></span><div><strong>Agréé préfecture</strong><span>Centre VHU n° {e(agr)}</span></div></div>'
    else:
        v["bloc_vhu_hero"] = v["bloc_vhu_footer"] = ""
        v["perk_2"] = f'<div class="perks_item" data-reveal><span class="perks_icon"><svg class="" aria-hidden="true"><use href="#i-pin"/></svg></span><div><strong>Sur tout le secteur</strong><span>{e(zone_nom)}</span></div></div>'

    v["carte_rachat"] = ('<div class="service_card" data-reveal><span class="service_icon"><svg class="" aria-hidden="true"><use href="#i-hand"/></svg></span><div><h3>Rachat de véhicule</h3><p>S’il a encore de la valeur.</p></div></div>' if rachat else "")
    v["footer_rachat"] = '<li><a href="#services">Rachat de véhicule</a></li>' if rachat else ""

    v["contact_email"] = (f'<li><svg class="icon" aria-hidden="true"><use href="#i-mail"/></svg><a href="mailto:{e(email)}">{e(email)}</a></li>' if email else "")
    v["footer_email"] = f'<li><a href="mailto:{e(email)}">{e(email)}</a></li>' if email else ""

    # Départements
    v["options_dep"] = "".join(f"<option>{e(n)} – {e(nm)}</option>" for n, nm in deps) + "<option>Autre département</option>"
    v["zones_grille"] = "".join(f'<div class="zone_item" data-reveal><span class="zone_number">{e(n)}</span><span>{e(nm)}</span></div>' for n, nm in deps)
    v["footer_zones"] = "".join(f"<li>{e(nm)} ({e(n)})</li>" for n, nm in deps[:4]) + (f'<li><a href="#zones">{e(zone_nom)}</a></li>' if len(deps) > 4 or not deps else "")

    # Avis : uniquement réels, fournis dans la fiche
    if avis.get("note") and avis.get("nombre"):
        lien = e(avis.get("lien") or "#")
        v["hero_avis"] = f'<a href="{lien}" target="_blank" rel="noopener" class="hero_rating">{ETOILES}{e(avis["note"])} · {e(avis["nombre"])} avis Google</a>'
        v["badge_avis"] = f'<a href="{lien}" target="_blank" rel="noopener" class="google_badge" data-reveal><strong>{e(avis["note"])}</strong><div>{ETOILES}<span style="display:block">{e(avis["nombre"])} avis sur Google</span></div></a>'
    else:
        v["hero_avis"] = v["badge_avis"] = ""
    liste = avis.get("liste") or []
    v["cartes_avis"] = "".join(
        f'<figure class="review_card">{ETOILES}<blockquote>« {e(a["texte"])} »</blockquote><figcaption class="review_author"><span class="review_avatar">{e(a["auteur"][:1].upper())}</span><span>{e(a["auteur"])}<small>Avis Google</small></span></figcaption></figure>'
        for a in liste)

    # Galerie : seulement avec de vraies photos du prospect (au moins 4)
    if len(photos) >= 4:
        alt = e(f"Enlèvement d'épave par {nom}")
        item = lambda src: f'<div class="gallery_item"><img src="{src}" alt="{alt}" loading="lazy" width="900" height="1200"></div>'
        moitie = len(photos) // 2
        r1, r2 = (photos[:moitie] * 8)[:8], (photos[moitie:] * 8)[:8]
        v["galerie_1"], v["galerie_2"] = "".join(map(item, r1)), "".join(map(item, r2))
        v["footer_credit"] = "Photos : interventions de l'entreprise"
    else:
        v["galerie_1"] = v["galerie_2"] = ""
        v["footer_credit"] = "Maquette de démonstration"

    v["footer_bas"] = e(f"© 2026 {nom}" + (f" · {fiche['societe']}" if fiche.get("societe") else ""))
    return v, {"galerie": len(photos) >= 4, "avis": bool(liste)}

def remplir(texte, v, blocs):
    for nom, garder in blocs.items():
        motif = re.compile(rf"<!--SI {nom}-->(.*?)<!--FIN {nom}-->", re.S)
        texte = motif.sub(lambda m: m.group(1) if garder else "", texte)
    texte = re.sub(r"\{\{(\w+)\}\}", lambda m: str(v[m.group(1)]), texte)
    reste = re.findall(r"\{\{\w+\}\}", texte)
    if reste: raise SystemExit(f"champs non remplis : {reste}")
    return texte


def manquants(fiche, logo, photos):
    m = []
    if not logo: m.append("logo (logo texte utilisé)")
    if len(photos) < 4: m.append(f"photos ({len(photos)} trouvées, galerie masquée)" if photos else "photos (visuels neutres utilisés)")
    if not fiche.get("agrement"): m.append("n° d'agrément VHU (badge masqué)")
    if not (fiche.get("avis") or {}).get("liste"): m.append("avis Google (section masquée)")
    if not fiche.get("departements"): m.append("départements")
    if not fiche.get("email"): m.append("e-mail")
    return m


def generer(dossier_fiche):
    fiche = json.loads((dossier_fiche / "fiche.json").read_text(encoding="utf-8"))
    slug = dossier_fiche.name
    modele = MODELES / fiche.get("modele", "epaviste")
    sortie = RACINE / slug
    sortie.mkdir(exist_ok=True)
    t = theme(fiche.get("couleur") or COULEUR_DEFAUT)
    logo, photos = recuperer_images(fiche, dossier_fiche, sortie)
    visuel = placeholder(sortie, t)
    v, blocs = construire(fiche, logo, photos, visuel, t)
    (sortie / "index.html").write_text(remplir((modele / "index.html").read_text(encoding="utf-8"), v, blocs), encoding="utf-8")
    (sortie / "main.js").write_text(remplir((modele / "main.js").read_text(encoding="utf-8"), v, {}), encoding="utf-8")
    (sortie / "theme.css").write_text(css_theme((modele / "styles.css").read_text(encoding="utf-8"), t), encoding="utf-8")
    m = manquants(fiche, logo, photos)
    (dossier_fiche / "manquants.txt").write_text("\n".join(m) + "\n", encoding="utf-8")
    print(f"✓ {slug} — {len(photos)} photo(s), logo {'oui' if logo else 'non'}" + (f" — manque : {', '.join(m)}" if m else ""))


if __name__ == "__main__":
    cibles = [RACINE / "prospects" / a for a in sys.argv[1:]] or sorted(d for d in (RACINE / "prospects").iterdir() if (d / "fiche.json").exists())
    for d in cibles:
        generer(d)
