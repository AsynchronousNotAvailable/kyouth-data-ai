import json
from pathlib import Path

from bs4 import BeautifulSoup

from src.dao.JobListing import JobListing


def process_all_html(input_dir, output_dir):
    success = 0
    skipped = 0
    source_dir = Path(input_dir)
    target_dir = Path(output_dir)

    if not source_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {source_dir}")
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Input directory is not a directory: {source_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)

    print("🥈 Silver:")

    for html_file in sorted(source_dir.glob("*.html")):
        try:
            with html_file.open("r", encoding="utf-8") as file_handle:
                html_content = file_handle.read()

            if not html_content:
                print(f"⚠️ No HTML content found in: {html_file.name}")
                skipped += 1
                continue

            soup = BeautifulSoup(html_content, "html.parser")

            meta_tag = soup.find("meta", attrs={"property": "og:url"})
            title_tag = soup.find("meta", attrs={"property": "og:title"})
            desc_tag = soup.find("meta", attrs={"property": "og:description"})
            company_tag = soup.find("span", attrs={"data-automation": "advertiser-name"})
            company_h4_tag = soup.find("h4", class_="mcr1dbi9")
            company_span_fallback = soup.select_one("div.mcr1dbhh.mcr1db6l span.l304fg4")

            source_id = None
            if meta_tag and meta_tag.has_attr("content"):
                full_url = meta_tag["content"]
                source_id = full_url.rstrip("/").split("/")[-1]

            job_title = title_tag["content"] if title_tag and title_tag.has_attr("content") else None
            job_desc = desc_tag["content"] if desc_tag and desc_tag.has_attr("content") else None
            company_name = (
                company_tag.get_text(separator=" ", strip=True) if company_tag else None
            ) or (# NTT, Sitecore, Optimum Infosolutions, and Tech Mahindra
                company_h4_tag.get_text(separator=" ", strip=True) if company_h4_tag else None
            ) or (# Emerson Process Management Manufacturing (M) Sdn Bhd
                company_span_fallback.get_text(separator=" ", strip=True) if company_span_fallback else None
            )

            missing_fields = []
            if not job_title:
                missing_fields.append("job_title")
            if not job_desc:
                missing_fields.append("description")
            if not company_name:
                missing_fields.append("company")

            if missing_fields:
                for field in missing_fields:
                    print(f"⚠️ Missing {field} in: {html_file.name}")
                skipped += 1
                continue

            job_listing = JobListing(
                source_id=source_id,
                job_title=job_title,
                description=job_desc,
                company=company_name,
            )

            output_file = target_dir / f"{html_file.stem}.json"
            output_file.write_text(
                json.dumps(job_listing.to_json(), ensure_ascii=False),
                encoding="utf-8",
            )

            print(f"✅ Processed: {html_file.name}")
            success += 1

        except Exception as error:
            print(f"❌ Failed: {html_file.name} ({error})")
            skipped += 1

    print()
    print("📊 Silver Summary:")
    print(f"Total: {success + skipped} | Processed: {success} | Skipped: {skipped}")
