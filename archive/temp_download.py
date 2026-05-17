from pathlib import Path
from urllib.parse import quote
import time
import zipfile
import requests

MISSISSIPPI_COUNTIES = [
    "Adams", "Alcorn", "Amite", "Attala", "Benton", "Bolivar", "Calhoun",
    "Carroll", "Chickasaw", "Choctaw", "Claiborne", "Clarke", "Clay",
    "Coahoma", "Copiah", "Covington", "DeSoto", "Forrest", "Franklin",
    "George", "Greene", "Grenada", "Hancock", "Harrison", "Hinds",
    "Holmes", "Humphreys", "Issaquena", "Itawamba", "Jackson", "Jasper",
    "Jefferson", "Jefferson Davis", "Jones", "Kemper", "Lafayette",
    "Lamar", "Lauderdale", "Lawrence", "Leake", "Lee", "Leflore",
    "Lincoln", "Lowndes", "Madison", "Marion", "Marshall", "Monroe",
    "Montgomery", "Neshoba", "Newton", "Noxubee", "Oktibbeha", "Panola",
    "Pearl River", "Perry", "Pike", "Pontotoc", "Prentiss", "Quitman",
    "Rankin", "Scott", "Sharkey", "Simpson", "Smith", "Stone",
    "Sunflower", "Tallahatchie", "Tate", "Tippah", "Tishomingo",
    "Tunica", "Union", "Walthall", "Warren", "Washington", "Wayne",
    "Webster", "Wilkinson", "Winston", "Yalobusha", "Yazoo",
]

BASE_URL = "https://maris.mississippi.edu/MARISdata/Aerial/NAIP/NAIP_2025"

DOWNLOAD_DIR = Path("F:\\Desktop\\review_assist\\temp_zips")
EXTRACT_DIR = Path("F:\\Desktop\\review_assist\\sources\\aerial_base_maps\\maris_naip_2025")
REMOTE_FILENAME_OVERRIDES = {
    "Jefferson Davis": "JeffersonDavis_NAIP_2025.zip",
    "Pearl River": "PearlRiver_NAIP_2025.zip",
    "Walthall": "WALTHALL_NAIP_20254.zip",
}

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 local-environmental-screening-cache"
})


def download_county(county: str) -> Path | None:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{county}_NAIP_2025.zip"
    remote_filename = REMOTE_FILENAME_OVERRIDES.get(county, filename)
    out_path = DOWNLOAD_DIR / filename

    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"Already downloaded: {filename}")
        return out_path

    tmp_path = out_path.with_suffix(".zip.part")
    if tmp_path.exists():
        print(f"Removing incomplete download: {tmp_path.name}")
        tmp_path.unlink()

    urls = [
        f"{BASE_URL}/{remote_filename}",
        f"{BASE_URL}/{quote(remote_filename)}",
    ]

    for url in urls:
        print(f"Trying: {url}")

        try:
            with session.get(url, stream=True, timeout=180) as r:
                if r.status_code == 404:
                    continue

                r.raise_for_status()

                with tmp_path.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

                tmp_path.rename(out_path)
                print(f"Saved: {out_path}")
                return out_path

        except Exception as e:
            print(f"Failed attempt for {filename}: {e}")

    if tmp_path.exists():
        tmp_path.unlink()

    print(f"Could not download: {filename}")
    return None


def unzip_file(zip_path: Path) -> None:
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

    county_name = zip_path.name.replace("_NAIP_2025.zip", "")
    county_extract_dir = EXTRACT_DIR / county_name

    if county_extract_dir.exists() and any(county_extract_dir.iterdir()):
        print(f"Already unzipped: {county_name}")
        return

    county_extract_dir.mkdir(parents=True, exist_ok=True)

    print(f"Unzipping: {zip_path.name}")

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(county_extract_dir)

        print(f"Extracted to: {county_extract_dir}")

    except zipfile.BadZipFile:
        print(f"Bad zip file: {zip_path}")
    except Exception as e:
        print(f"Failed unzip for {zip_path.name}: {e}")


def completed_county_zips() -> dict[str, Path]:
    completed = {}
    for zip_path in DOWNLOAD_DIR.glob("*_NAIP_2025.zip"):
        if zip_path.stat().st_size <= 0:
            continue

        county_name = zip_path.name.replace("_NAIP_2025.zip", "")
        completed[county_name] = zip_path

    return completed


def completed_county_extracts() -> dict[str, Path]:
    completed = {}
    if not EXTRACT_DIR.exists():
        return completed

    for county_dir in EXTRACT_DIR.iterdir():
        if not county_dir.is_dir() or not any(county_dir.iterdir()):
            continue

        completed[county_dir.name] = county_dir

    return completed


def missing_counties() -> list[str]:
    completed = set(completed_county_zips()) | set(completed_county_extracts())
    return [county for county in MISSISSIPPI_COUNTIES if county not in completed]


def main():
    downloaded = []
    counties_to_download = missing_counties()

    if counties_to_download:
        print("Missing completed county zips:")
        for county in counties_to_download:
            print(f"- {county}")
    else:
        print("All Mississippi county zips are already present.")

    for county in counties_to_download:
        zip_path = download_county(county)

        if zip_path:
            downloaded.append(zip_path)

        time.sleep(0.5)

    print("\nDownload phase complete.")
    print(f"Downloaded/found {len(downloaded)} zip files.")

    print("\nStarting unzip phase...")

    for zip_path in sorted(DOWNLOAD_DIR.glob("*_NAIP_2025.zip")):
        unzip_file(zip_path)

    print("\nDone.")


if __name__ == "__main__":
    main()
