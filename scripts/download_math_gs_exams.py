"""
CRDP Lebanon - Math GS Grade 12 Official Exams Downloader (English only)
Downloads 20 Mathematics (General Sciences) English exams from crdp.org
"""

import urllib.request
import os

OUTPUT_FOLDER = "Math_GS_Exams_English"

EXAMS = [
    ("Math_GS_English_2004_Session1",   "https://www.crdp.org/sites/default/files/201702280646201.pdf"),
    ("Math_GS_English_2004_Session2",   "https://www.crdp.org/sites/default/files/201704110844251.pdf"),
    ("Math_GS_English_2006_Session1",   "https://www.crdp.org/sites/default/files/201703200855543.pdf"),
    ("Math_GS_English_2006_Session2",   "https://www.crdp.org/sites/default/files/201703220934195.pdf"),
    ("Math_GS_English_2008_Session1",   "https://www.crdp.org/sites/default/files/201703091101223.pdf"),
    ("Math_GS_English_2008_Session2",   "https://www.crdp.org/sites/default/files/201703100100035.pdf"),
    ("Math_GS_English_2012_Session1",   "https://www.crdp.org/sites/default/files/201702210912275.pdf"),
    ("Math_GS_English_2012_Session2",   "https://www.crdp.org/sites/default/files/201702271244093.pdf"),
    ("Math_GS_English_2015_Session1",   "https://www.crdp.org/sites/default/files/201701251233053.pdf"),
    ("Math_GS_English_2015_Session2",   "https://www.crdp.org/sites/default/files/201702061134475.pdf"),
    ("Math_GS_English_2016_Session1",   "https://www.crdp.org/sites/default/files/201702071056524.pdf"),
    ("Math_GS_English_2016_Session2",   "https://www.crdp.org/sites/default/files/201702130129155.pdf"),
    ("Math_GS_English_2017_Session1",   "https://www.crdp.org/sites/default/files/201708100850071.pdf"),
    ("Math_GS_English_2017_Session2",   "https://www.crdp.org/sites/default/files/201804111053295.pdf"),
    ("Math_GS_English_2019_Session1",   "https://www.crdp.org/sites/default/files/201909171131361.pdf"),
    ("Math_GS_English_2019_Session2",   "https://www.crdp.org/sites/default/files/201910091244225.pdf"),
    ("Math_GS_English_2019_Exceptional","https://www.crdp.org/sites/default/files/202006091115255.pdf"),
    ("Math_GS_English_2021_Regular",    "https://www.crdp.org/sites/default/files/SG_Math_2021_1_En.pdf"),
    ("Math_GS_English_2021_Exceptional","https://www.crdp.org/sites/default/files/SG_Math_2021_2_En.pdf"),
    ("Math_GS_English_2024_Session1",   "https://www.crdp.org/sites/default/files/SG_Math_2024_1_En.pdf"),
]

def download_exams():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0"}
    success, failed = 0, 0

    for name, url in EXAMS:
        filename = os.path.join(OUTPUT_FOLDER, f"{name}.pdf")
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                with open(filename, "wb") as f:
                    f.write(response.read())
            print(f"✓ {name}.pdf")
            success += 1
        except Exception as e:
            print(f"✗ {name}: {e}")
            failed += 1

    print(f"\nDone: {success} downloaded, {failed} failed.")
    print(f"Files saved to: {os.path.abspath(OUTPUT_FOLDER)}/")

if __name__ == "__main__":
    download_exams()
