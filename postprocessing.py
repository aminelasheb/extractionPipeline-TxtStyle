import os
import json
# Assure-toi d'avoir fait : pip install json_repair
from json_repair import repair_json

# =========================
# CONFIGURATION
# =========================
# Dossier contenant les fichiers JSON bruts générés par Gemini
INPUT_DIR = r"C:\Users\lasheb\PycharmProjects\extractionPipeline-TS\extractionOutStyle"

# Dossier pour sauvegarder les versions corrigées
OUTPUT_DIR = r"C:\Users\lasheb\PycharmProjects\extractionPipeline-TS\extractionOutStyle_Cleaned"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def pre_clean_string(text: str) -> str:
    """
    Nettoyage chirurgical des erreurs de backslashs générées par le LLM
    AVANT de tenter de réparer la structure JSON.
    """
    # 1. Retirer les balises Markdown ```json ... ```
    t = text.strip()
    if t.startswith("```json"):
        t = t[7:].strip()
    if t.startswith("```"):
        t = t[3:].strip()
    if t.endswith("```"):
        t = t[:-3].strip()

    # -----------------------------------------------------------
    # RÉPARATIONS DES BACKSLASHS (Ordre important)
    # -----------------------------------------------------------

    # A. Sauts de ligne : \\n devient \n
    # Le LLM écrit souvent 2 chars (\ + n), on veut le caractère de contrôle.
    t = t.replace("\\\\n", "\\n")

    # B. Cas critique des guillemets avec 3 backslashs : \\\" devient \"
    # C'est ton erreur actuelle : \color{\\\" -> le parser voit 3 barres.
    # On remplace par \" (1 barre + guillemet) pour que ce soit un guillemet échappé valide.
    t = t.replace('\\\\\\"', '\\"')

    # C. Cas critique des guillemets avec 2 backslashs : \\" devient \"
    # Cela arrive quand le LLM essaie d'échapper le backslash devant le guillemet.
    # Dans une string JSON, \\" signifie "Backslash littéral + Fin de string".
    # Cela CASSE le json. On remplace par \" (Guillemet échappé).
    t = t.replace('\\\\"', '\\"')

    # D. LaTeX général : \\\\bf devient \\bf (4 barres -> 2 barres)
    # Pour avoir un seul backslash littéral en JSON, il en faut 2 dans le code source.
    # Si le LLM en met 4, on réduit à 2.
    t = t.replace("\\\\\\\\", "\\\\")

    # E. Nettoyage résiduel (3 barres -> 2 barres)
    # Au cas où il reste des \\\bf
    t = t.replace("\\\\\\", "\\\\")

    return t


def fix_and_save(filename):
    in_path = os.path.join(INPUT_DIR, filename)
    out_path = os.path.join(OUTPUT_DIR, filename)

    try:
        with open(in_path, "r", encoding="utf-8") as f:
            raw_content = f.read()
    except Exception as e:
        print(f"[ERR] Erreur lecture {filename}: {e}")
        return

    # 1. Pré-nettoyage manuel (slashs)
    pre_cleaned = pre_clean_string(raw_content)

    # 2. Utilisation de json_repair pour la structure
    # Cette librairie est très forte pour fermer les accolades manquantes
    # ou ignorer les virgules en trop, une fois que les strings sont propres (étape 1).
    try:
        # repair_json renvoie un objet python (dict/list) directement
        data = repair_json(pre_cleaned, return_objects=True)

        # 3. Sauvegarde propre
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] Succes : {filename}")

    except Exception as e:
        print(f"[ERR] Echec total sur : {filename}")
        print(f"      Raison : {e}")

        # Sauvegarde du fichier cassé (mais pré-nettoyé) pour inspection
        with open(out_path.replace(".json", "_BROKEN.txt"), "w", encoding="utf-8") as f:
            f.write(pre_cleaned)


def main():
    if not os.path.exists(INPUT_DIR):
        print(f"[ERR] Le dossier {INPUT_DIR} n'existe pas.")
        return

    files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".json")]
    print(f"Traitement de {len(files)} fichiers dans {INPUT_DIR}...")

    for f in files:
        fix_and_save(f)

    print("Post-traitement termine.")


if __name__ == "__main__":
    main()