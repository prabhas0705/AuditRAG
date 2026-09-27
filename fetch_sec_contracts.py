"""
fetch_sec_contracts.py - Downloads real SEC EDGAR Exhibit 10 material contracts.
Zero third-party pip dependencies; uses standard library urllib and html.
"""

import os
import re
import html
import urllib.request
from typing import Dict, List

SEC_CONTRACTS = [
    {
        "filename": "Tesla_ABL_Credit_Agreement_2015.txt",
        "title": "Tesla Motors, Inc. - ABL Credit Agreement ($500M+ Syndicated Facility)",
        "url": "https://www.sec.gov/Archives/edgar/data/1318605/000119312515222013/d942001dex101.htm",
        "company": "Tesla, Inc.",
        "type": "Credit Facility Agreement"
    },
    {
        "filename": "Tesla_Credit_Agreement_Second_Amendment_2015.txt",
        "title": "Tesla Motors, Inc. - Second Amendment to ABL Credit Agreement",
        "url": "https://www.sec.gov/Archives/edgar/data/1318605/000156459016013195/tsla-ex1028b_206.htm",
        "company": "Tesla, Inc.",
        "type": "Contract Amendment"
    },
    {
        "filename": "Tesla_Credit_Agreement_Third_Amendment_2016.txt",
        "title": "Tesla Motors, Inc. - Third Amendment to ABL Credit Agreement",
        "url": "https://www.sec.gov/Archives/edgar/data/1318605/000156459016013195/tsla-ex1028c_207.htm",
        "company": "Tesla, Inc.",
        "type": "Contract Amendment"
    },
    {
        "filename": "Tesla_Panasonic_Battery_Supply_Notice_2015.txt",
        "title": "Tesla Motors, Inc. - Notification of Adding Panasonic Energy Corp to Supply Agreement",
        "url": "https://www.sec.gov/Archives/edgar/data/1318605/000156459016013195/tsla-ex1025a_208.htm",
        "company": "Tesla, Inc.",
        "type": "Commercial Supply Agreement"
    },
    {
        "filename": "Tesla_CFO_Employment_Offer_2015.txt",
        "title": "Tesla Motors, Inc. - Offer Letter to Jason Wheeler (CFO)",
        "url": "https://www.sec.gov/Archives/edgar/data/1318605/000156459016013195/tsla-ex1012_209.htm",
        "company": "Tesla, Inc.",
        "type": "Executive Employment Agreement"
    },
    {
        "filename": "Tesla_2019_Equity_Incentive_RSU_Agreement_2026.txt",
        "title": "Tesla, Inc. - Amended and Restated 2019 Equity Incentive Plan RSU Agreement",
        "url": "https://www.sec.gov/Archives/edgar/data/1318605/000162828026003952/tsla-2025x12x31xex1010.htm",
        "company": "Tesla, Inc.",
        "type": "Equity Compensation Agreement"
    },
    {
        "filename": "Google_dMarc_Merger_Agreement_2006.txt",
        "title": "Google Inc. - Agreement and Plan of Merger with dMarc Broadcasting & U.S. Bank",
        "url": "https://www.sec.gov/Archives/edgar/data/1288776/000119312507044494/dex1021.htm",
        "company": "Google Inc.",
        "type": "M&A Agreement"
    },
    {
        "filename": "Apple_2014_Employee_Stock_Plan_2017.txt",
        "title": "Apple Inc. - 2014 Employee Stock Plan (Amended and Restated)",
        "url": "https://www.sec.gov/Archives/edgar/data/320193/000032019317000070/a10-kexhibit1082017.htm",
        "company": "Apple Inc.",
        "type": "Equity Plan"
    },
    {
        "filename": "Microsoft_COO_Employment_Agreement_2005.txt",
        "title": "Microsoft Corporation - Offer of Employment to Kevin Turner (COO)",
        "url": "https://www.sec.gov/Archives/edgar/data/789019/000119312505157825/dex101.htm",
        "company": "Microsoft Corporation",
        "type": "Executive Employment Agreement"
    }
]

def clean_sec_html(raw_html: str) -> str:
    """Converts SEC EDGAR HTML exhibits into clean, structured paragraphs."""
    # Replace breaks and table row endings with newlines
    text = re.sub(r'<(p|div|tr|h\d|br)[^>]*>', '\n\n', raw_html, flags=re.IGNORECASE)
    text = re.sub(r'</(p|div|tr|h\d)>', '\n\n', text, flags=re.IGNORECASE)
    # Remove script and style tags
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Strip remaining HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Normalize whitespaces
    lines = [line.strip() for line in text.splitlines()]
    clean_lines = []
    for line in lines:
        if line:
            clean_lines.append(re.sub(r'[ \t]+', ' ', line))
        else:
            clean_lines.append('')
    collapsed = '\n'.join(clean_lines)
    collapsed = re.sub(r'\n{3,}', '\n\n', collapsed)
    return collapsed.strip()

def download_and_prepare_corpus(output_dir: str = "sec_corpus"):
    """Fetches SEC EDGAR contracts, cleans them, and writes them to output_dir."""
    os.makedirs(output_dir, exist_ok=True)
    headers = {"User-Agent": "AuditRAG-Benchmark auditor@auditrag.org"}

    print("=" * 70)
    print("  FETCHING REAL SEC EDGAR MATERIAL CONTRACTS (EXHIBIT 10)")
    print("=" * 70)

    total_chars = 0
    total_files = 0

    for item in SEC_CONTRACTS:
        target_path = os.path.join(output_dir, item["filename"])
        print(f"\n[+] Fetching {item['title']}...")
        print(f"    URL: {item['url']}")

        try:
            req = urllib.request.Request(item["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw_html = resp.read().decode("utf-8", errors="ignore")
                cleaned = clean_sec_html(raw_html)

                # Prepend contract header for clear citation
                header = (
                    f"================================================================================\n"
                    f"DOCUMENT: {item['filename']}\n"
                    f"COMPANY: {item['company']}\n"
                    f"CONTRACT TITLE: {item['title']}\n"
                    f"TYPE: {item['type']}\n"
                    f"SOURCE: SEC EDGAR ({item['url']})\n"
                    f"================================================================================\n\n"
                )
                full_content = header + cleaned

                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(full_content)

                chars = len(full_content)
                total_chars += chars
                total_files += 1
                print(f"    [OK] Saved {item['filename']} ({chars:,} chars, ~{chars // 4:,} tokens)")
        except Exception as e:
            print(f"    [!] Error downloading {item['filename']}: {e}")

    print("\n" + "=" * 70)
    print(f"  DOWNLOAD COMPLETE: {total_files}/{len(SEC_CONTRACTS)} contracts saved to '{output_dir}/'")
    print(f"  TOTAL CORPUS SIZE: {total_chars:,} characters (~{total_chars // 4:,} tokens)")
    print("=" * 70)

if __name__ == "__main__":
    download_and_prepare_corpus()
