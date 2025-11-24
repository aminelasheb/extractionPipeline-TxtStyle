import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DIRS_TO_RESET = ["files", "files_style", "files_images", "output", "files-out", "extractionOutStyle", "extractionOut"]


def reset_directories():
    for directory in DIRS_TO_RESET:
        dir_path = BASE_DIR / directory
        shutil.rmtree(dir_path, ignore_errors=True)
        os.makedirs(dir_path, exist_ok=True)
        print(f"[OK] Reset: {dir_path}")


def run_script(script_name, *args):
    script_path = BASE_DIR / script_name

    if not script_path.exists():
        print(f"[ERR] Script not found: {script_path}")
        sys.exit(1)

    print(f"\n[RUN] Running {script_name}...")

    process = subprocess.Popen(
        [sys.executable, str(script_path), *map(str, args)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    for line in iter(process.stdout.readline, ''):
        if line:
            print(line, end="")
        else:
            break

    process.stdout.close()
    process.wait()

    if process.returncode == 0:
        print(f"[OK] {script_name} finished successfully")
    else:
        print(f"[ERR] {script_name} failed. Stopping pipeline.")
        sys.exit(1)


if __name__ == "__main__":

    pdf_path = Path(
        r"C:\Users\lasheb\Desktop\PFE\PFE\les manuels scolaires\manual_CE1_FRANCAIS_MAGNARD.pdf"
    )

    # =========================
    # 🔧 CONTRÔLE DES PAGES
    # =========================
    ALL_PAGES = False          # True = tout le PDF, False = sous-ensemble
    FIRST_PAGE = 12             # 1-based
    LAST_PAGE = 16           # 1-based, inclus

    if ALL_PAGES:
        all_flag = "true"
        first_page = ""
        last_page = ""
    else:
        all_flag = "false"
        first_page = str(FIRST_PAGE)
        last_page = str(LAST_PAGE)
    # =========================

    reset_directories()

    # PDF -> images (Ghostscript)
    run_script(
        "pdfToImages.py",
        pdf_path,
        BASE_DIR / "files",
        all_flag,
        first_page,
        last_page
    )

    # PDF -> CSV style/texte (PyMuPDF)
    run_script(
        "pdfToTxtStyle.py",
        pdf_path,
        BASE_DIR / "files_style",
        all_flag,
        first_page,
        last_page
    )


    run_script("detectImages.py")
    run_script("cropImages.py")
    run_script("drawBoxes.py")
    run_script("extraction-gemini-vision.py")

    print("\n[DONE] All tasks completed successfully!")
