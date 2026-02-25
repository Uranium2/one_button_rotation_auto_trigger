import re
import os
import requests
from selenium import webdriver

ALL_CLASSES_SPECS = {
    "death-knight": ["blood", "frost", "unholy"],
    "demon-hunter": ["devourer", "havoc", "vengeance"],
    "druid": ["balance", "feral", "guardian", "restoration"],
    "evoker": ["augmentation", "devastation", "preservation"],
    "hunter": ["beast-mastery", "marksmanship", "survival"],
    "mage": ["arcane", "fire", "frost"],
    "monk": ["brewmaster", "mistweaver", "windwalker"],
    "paladin": ["holy", "retribution", "protection"],
    "priest": ["discipline", "holy", "shadow"],
    "rogue": ["assassination", "outlaw", "subtlety"],
    "shaman": ["elemental", "enhancement", "restoration"],
    "warlock": ["affliction", "demonology", "destruction"],
    "warrior": ["arms", "fury", "protection"],
}


def scrape_icon_urls(wow_class, spec, driver, output_dir):
    class_out = wow_class.replace("-", "_")
    spec_out = spec.replace("-", "_")
    page_url = f"https://www.wowhead.com/talent-calc/{wow_class}/{spec}"
    icon_outfile = f"{output_dir}/{class_out}_{spec_out}_spell_icon_urls.txt"
    debug_html_outfile = f"{output_dir}/{class_out}_{spec_out}_debug.html"
    driver.get(page_url)
    print(f"Scraping {page_url}")

    html = driver.execute_script(
        "return document.getElementsByTagName('html')[0].innerHTML"
    )
    # with open(debug_html_outfile, "w", encoding="utf-8") as f:
    #     f.write(html)

    prefixes = ["spell", "ability", "inv"]
    urls = set()
    for prefix in prefixes:
        pat = rf'https://wow.zamimg.com/images/wow/icons/(small|medium|large)/{prefix}[^"\s>&)]*?\.jpg'
        for m in re.finditer(pat, html, re.IGNORECASE):
            url = m.group(0)
            url = url.replace("/small/", "/large/").replace("/medium/", "/large/")
            urls.add(url)
    large_urls = sorted(urls)

    with open(icon_outfile, "w", encoding="utf-8") as f:
        for url in large_urls:
            f.write(url + "\n")
    print(
        f"  → {len(large_urls)} spell/ability/inv .jpg icon URLs saved to {icon_outfile}"
    )


def download_icon_images_from_txt(
    wow_class, spec, txt_dir="data", out_root="data/icons"
):
    class_out = wow_class.replace("-", "_")
    spec_out = spec.replace("-", "_")
    txt_file = f"{txt_dir}/{class_out}_{spec_out}_spell_icon_urls.txt"
    target_dir = f"{out_root}/{class_out}/{spec_out}"
    os.makedirs(target_dir, exist_ok=True)
    if not os.path.isfile(txt_file):
        print(f"Cannot find {txt_file}")
        return
    with open(txt_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]
    print(f"Downloading {len(urls)} icons for {wow_class}/{spec} ...")
    for i, url in enumerate(urls, 1):
        filename = os.path.basename(url.split("?")[0])  # ignore URL params if present
        outfile = os.path.join(target_dir, filename)
        if os.path.exists(outfile):
            continue  # skip if file already exists
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                with open(outfile, "wb") as outimg:
                    outimg.write(resp.content)
            else:
                print(f"FAILED {url} [{resp.status_code}]")
        except Exception as e:
            print(f"Error downloading {url}: {e}")
    print(f"Done: All icons downloaded to {target_dir}\n")


def main():
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    driver = webdriver.Chrome()
    for wow_class, specs in ALL_CLASSES_SPECS.items():
        for spec in specs:
            try:
                scrape_icon_urls(wow_class, spec, driver, output_dir)
            except Exception as e:
                print(f"Failed for {wow_class}/{spec}: {e}")
    driver.quit()

    # Now, download for all
    for wow_class, specs in ALL_CLASSES_SPECS.items():
        for spec in specs:
            try:
                download_icon_images_from_txt(wow_class, spec)
            except Exception as e:
                print(f"(Download fail) {wow_class}/{spec}: {e}")


if __name__ == "__main__":
    main()
