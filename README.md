# Maquettes prospects

Landing pages de démonstration générées pour la prospection.
Chaque maquette est en ligne sur `https://mohamedscaler.github.io/maquettes/<slug>/` (non indexée par Google).

## Ajouter un prospect

Créer `prospects/<slug>/fiche.json` puis pousser sur `main`. GitHub Actions télécharge les photos,
génère la page et la publie (~1 min).

```json
{
  "nom": "Dupont Épaves",
  "tel": "06 12 34 56 78",
  "whatsapp": "06 12 34 56 78",
  "email": "",
  "couleur": "#d9480f",
  "logo": "https://… (facultatif)",
  "zone_en": "dans le Val-de-Marne",
  "zone_nom": "Val-de-Marne et alentours",
  "zone_phrase": "Créteil, Vitry, Ivry et tout le Val-de-Marne.",
  "departements": [["94", "Val-de-Marne"], ["75", "Paris"]],
  "horaires": "7j/7",
  "agrement": "",
  "rachat": true,
  "societe": "",
  "avis": {"note": "4,9", "nombre": 12, "lien": "https://…", "liste": [{"auteur": "Karim D.", "texte": "…"}]},
  "photos": ["https://…", "https://…"],
  "instagram": "@dupontepaves",
  "source": "capture Instagram"
}
```

Règles : on n'invente rien. Agrément, avis, e-mail : seulement si confirmés, sinon laissés vides
(les blocs correspondants sont masqués). Ce qui manque est listé dans `prospects/<slug>/manquants.txt`.

Le modèle (`modele/epaviste/`) vient de la landing L'Epaviste IDF, sans ses photos, textes légaux,
numéros ni suivi publicitaire. Ne jamais y ajouter les photos de ce client.

Test en local : `python outils/generer.py <slug>`
