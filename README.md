# extractionPipeline-TxtStyle

Version mise à jour du pipeline d'extraction MALIN avec **extraction texte + style** pour PDF natifs.

<p align="center">
  <img src="pipeline.png" width="100%">
</p>

## Vue d’ensemble

Pipeline d’extraction d’exercices à partir de PDF scolaires :

- Ghostscript — PDF → images  
- YOLOv11x — détection exercices / illustrations  
- OpenCV — annotation + découpe  
- PDFMiner — extraction texte + style  
- Gemini Vision — structuration des exercices (version 2.5 flash)

## Pourquoi ajouter le style ?

Certaines exercices utilisent des **mots stylés** (couleur, gras, italique…) au sein d’un bloc de texte au style uniforme.  
Pour les distinguer correctement, nous avons ajouté une étape **Text/Style Map**.

En ajoutant cette étape, on a constaté que **l’extraction globale s’améliore nettement**.  
Les prompts Gemini sont encore en phase d’optimisation (non finaux),  
mais **le pipeline est pratiquement stabilisé**.

---

## Pré-requis

- Python 3.10+  
- Ghostscript installé (PDF → images)  
- Clé API Gemini → fichier `apikey.txt` à la racine  
- Poids YOLOv11x (`.pt`) dans `./detImages/`  


---

## Configuration

Les dossiers et chemins sont centralisés dans `main.py` :

* `pdf_path (main)` : PDF d’entrée
* `files` : pages converties en images
* `files_style` : texte/style d’une page (sortie PDFMiner)
* `files_out` : images annotées avec les IDs des illustrations
* `output` : détections YOLO + crops
* `extractionOut` / `extractionOutStyle` : sorties finales

> **À adapter selon ton environnement**.  

---

## Quickstart

1. Déposer le PDF dans le main.
2. Configurer :
 - `ALL_PAGES`, `FIRST_PAGE`, `LAST_PAGE`
 - `STYLE_MODE = True/False` (extraction-gemini-vision.py)
3. Lancer :
```

python main.py

````
4. Récupérer les JSON :
- `extractionOut/` (sans style)
- `extractionOutStyle/` (avec style)

---

## Sorties

Possibilité en **deux formats JSON** (l’utilisateur choisit dans **Patty**) :

### 1. JSON **avec style**
- `\bf{}`, `\it{}`, `\color{"txt",#HEX}`  
- références images : `\image{id}`  
- utilisé quand la mise en forme contient une information importante  
- activé via :
```python
STYLE_MODE = True
````

### 2. JSON **sans style**

* texte simplifié sans balises
* images référencées avec `\image{id}`
* préféré pour les traitements downstream simples
* activé via :

  ```python
  STYLE_MODE = False
  ```

---

## Nouveau schéma JSON

```json
{
  "$defs": {
    "Exercise": {
      "properties": {
        "id": {
          "anyOf": [{ "type": "string" }, { "type": "null" }],
          "default": null
        },
        "type": {
          "const": "exercise",
          "type": "string",
          "default": "exercise"
        },
        "images": {
          "type": "boolean",
          "default": false
        },
        "image_type": {
          "type": "string",
          "enum": ["none", "single", "ordered", "unordered", "composite"],
          "default": "none"
        },
        "properties": {
          "$ref": "#/$defs/Properties",
          "default": {
            "number": null,
            "instruction": null,
            "labels": [],
            "statement": null,
            "hint": null,
            "example": null,
            "references": null
          }
        }
      },
      "type": "object"
    },
    "Properties": {
      "properties": {
        "number": {
          "anyOf": [{ "type": "string" }, { "type": "null" }],
          "default": null
        },
        "instruction": {
          "anyOf": [{ "type": "string" }, { "type": "null" }],
          "default": null
        },
        "labels": {
          "type": "array",
          "items": { "type": "string" },
          "default": []
        },
        "statement": {
          "anyOf": [{ "type": "string" }, { "type": "null" }],
          "default": null
        },
        "hint": {
          "anyOf": [{ "type": "string" }, { "type": "null" }],
          "default": null
        },
        "example": {
          "anyOf": [{ "type": "string" }, { "type": "null" }],
          "default": null
        },
        "references": {
          "anyOf": [{ "type": "string" }, { "type": "null" }],
          "default": null
        }
      },
      "type": "object"
    }
  },
  "items": { "$ref": "#/$defs/Exercise" },
  "type": "array"
}
