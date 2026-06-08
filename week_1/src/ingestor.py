import email
from email.message import Message
from pathlib import Path
import quopri


def _extract_html(part: Message) -> str | None:
    payload = part.get_payload(decode=True)
    charset = part.get_content_charset() or "utf-8"

    if payload is None:
        raw_payload = part.get_payload()
        if not isinstance(raw_payload, str):
            return None
        # decode quoted printable to original form, showing clean text
        payload = quopri.decodestring(raw_payload.encode("utf-8"))

    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def ingest_all_mhtml(input_dir, output_dir):
    success = 0
    failed = 0
    source_dir = Path(input_dir)
    target_dir = Path(output_dir)

    if not source_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {source_dir}")
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {source_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)

    for source_file in sorted(source_dir.glob("*.mhtml")):
        extracted = False

        try:
            with source_file.open("rb") as file_handle:
                msg = email.message_from_bytes(file_handle.read())
                if not msg:
                    print(f"⚠️ No HTML content found in: {source_file.name}")
                    failed += 1
                    continue

            for part in msg.walk():
                if part.get_content_type() != "text/html":
                    continue

                decoded_html = _extract_html(part)
                if decoded_html is None:
                    continue

                output_file = target_dir / f"{source_file.stem}.html"
                output_file.write_text(decoded_html, encoding="utf-8")
                extracted = True
                break
        except Exception as error:
            failed += 1
            print(f"❌ Failed: {source_file.name} ({error})")
            continue

        if extracted:
            print(f"✅ Extracted: {source_file.name}")
            success += 1
        else:
            failed += 1
            print(f"❌ Failed: {source_file.name} (no text/html content found)")

    print("📊 Bronze Summary:")
    print(f"Total {success + failed} | Extracted: {success} | Failed: {failed}")
