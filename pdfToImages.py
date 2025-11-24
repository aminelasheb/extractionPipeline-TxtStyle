import os
import subprocess
import sys
from pathlib import Path


def pdf_to_images_best_quality(pdf_path, output_folder, dpi=450,
                               all_pages=True, first_page=None, last_page=None):
    pdf_path = Path(pdf_path)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    device = "png16m"   # 24-bit PNG
    gs = "gswin64c" if os.name == "nt" else "gs"

    # On génère d'abord des fichiers temporaires : tmp-001.png, tmp-002.png, ...
    tmp_pattern = str(output_folder / "tmp-%03d.png")

    cmd = [
        gs,
        "-dSAFER",
        "-dBATCH",
        "-dNOPAUSE",
        "-dTextAlphaBits=4",
        "-dGraphicsAlphaBits=4",
        "-sDEVICE=" + device,
        f"-r{dpi}",
        "-sOutputFile=" + tmp_pattern,
    ]

    if not all_pages:
        if first_page is None or last_page is None:
            raise ValueError("first_page and last_page must be set when all_pages is False")
        cmd.append(f"-dFirstPage={first_page}")
        cmd.append(f"-dLastPage={last_page}")

    cmd.append(str(pdf_path))

    print("[RUN] Ghostscript command:")
    print(" ".join(map(str, cmd)))

    subprocess.run(cmd, check=True)

    # Renommage : tmp-001.png -> page_X.png
    # Si all_pages=True : on commence à 1 -> page_1.png, page_2.png, ...
    # Sinon : on commence à first_page -> page_15.png, etc.
    start_page = first_page if (first_page is not None) else 1

    index = 1
    while True:
        tmp_file = output_folder / f"tmp-{index:03d}.png"
        if not tmp_file.exists():
            break

        page_num = start_page + (index - 1)
        new_file = output_folder / f"page_{page_num}.png"

        if new_file.exists():
            new_file.unlink()

        tmp_file.rename(new_file)
        index += 1

    print("\n[OK] Done! Images saved in:", output_folder.resolve())


if __name__ == "__main__":
    # Usage: python pdfToImages.py <pdf_path> <output_folder> <all(true|false)> [first_page] [last_page] [dpi]
    if len(sys.argv) < 4:
        print("Usage: python pdfToImages.py <pdf_path> <output_folder> <all(true|false)> [first_page] [last_page] [dpi]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_folder = sys.argv[2]
    all_flag = sys.argv[3].lower().strip()

    if all_flag == "true" or all_flag == "":
        all_pages = True
        first_page = None
        last_page = None
    else:
        all_pages = False
        if len(sys.argv) < 6:
            print("Error: need first_page and last_page when all_flag is false")
            sys.exit(1)
        first_page = int(sys.argv[4])
        last_page = int(sys.argv[5])

    dpi = int(sys.argv[6]) if len(sys.argv) >= 7 else 450

    pdf_to_images_best_quality(
        pdf_path,
        output_folder,
        dpi=dpi,
        all_pages=all_pages,
        first_page=first_page,
        last_page=last_page,
    )
