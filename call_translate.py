
import argparse
import dowser_analyse
import os
import sys
import tempfile
from pathlib import Path

#from transformers import pipeline
import requests
import whisper
from pymongo import MongoClient

from dowser_analyse import analyze_text

print("Imports finished")

# ============================== CONFIG ====================================

MONGO_URI = "mongodb://bhupikk:bhupikm%40%40991@65.2.183.203:27017/?authSource=admin"
DB_NAME = "DOWSER"


COLLECTIONS_TO_SEARCH = ["DomesticCalls", "InternationalCalls", "ReserveCalls"]

ID_FIELD = "uniqueid"

AUDIO_FIELD = "recordingpath"

AUDIO_SOURCE_TYPE = "url"

S3_BUCKET = "your-bucket-name"

DEFAULT_TARGET_LANG = "english"

WHISPER_MODEL = "whisper-1"
TRANSLATION_MODEL = "gpt-4o-mini"   

OUTPUT_DIR = "./call_outputs"


print("Loading Whisper model...")
whisper_model = whisper.load_model("base")

print("Whisper model loaded successfully")


print("Starting function definitions...")

def get_db():
    print("=" * 50)
    print("Using Mongo URI:")
    print(MONGO_URI)
    print("=" * 50)

    mongo_client = MongoClient(MONGO_URI)

    # Verify connection
    print("Pinging MongoDB...")
    print(mongo_client.admin.command("ping"))

    db = mongo_client[DB_NAME]

    print(f"Connected to database: {DB_NAME}")
    print("Collections:")
    print(db.list_collection_names())

    return db


def fetch_call_records(call_ids):
    """
    Fetch call documents by ID_FIELD, searching across every collection in
    COLLECTIONS_TO_SEARCH (Domestic / International / Reserve). Each returned
    record gets a "_source_collection" tag so we know where it came from.
    """
    db = get_db()
    remaining = set(call_ids)
    records = []

    for coll_name in COLLECTIONS_TO_SEARCH:
        if not remaining:
            break
        collection = db[coll_name]
        query = {ID_FIELD: {"$in": list(remaining)}}
        matches = list(collection.find(query))
        for m in matches:
            m["_source_collection"] = coll_name
            records.append(m)
            remaining.discard(m.get(ID_FIELD))

    if remaining:
        print(f"⚠️  No DB record found in any collection for: {sorted(remaining)}", file=sys.stderr)

    return records


def download_audio_to_tempfile(record):
    """
    Resolves the audio location for a record into a local temp file pathranscribe
    that can be passed to Whisper. Handles url / local_path / s3.
    """
    audio_ref = record.get(AUDIO_FIELD)

    print("=" * 60)
    print("Call ID:", record.get(ID_FIELD))
    print("Recording URL:", audio_ref)
    print("=" * 60)

    if not audio_ref:
        raise ValueError(f"No '{AUDIO_FIELD}' found on record {record.get(ID_FIELD)}")

    suffix = Path(audio_ref).suffix or ".mp3"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)

    if AUDIO_SOURCE_TYPE == "url":
        print("Downloading:", audio_ref)

        resp = requests.get(audio_ref, timeout=60)
        
        print("Status Code:", resp.status_code)
        print("Content-Type:", resp.headers.get("Content-Type"))
        
        resp.raise_for_status()
        
        tmp.write(resp.content)
        
        print("Downloaded", len(resp.content), "bytes")

        tmp.close()
        print("Temporary file:", tmp.name)
        return tmp.name



def transcribe_audio(local_audio_path):

    print("Transcribing (original language)...")

    transcript_result = whisper_model.transcribe(
        local_audio_path,
        task="transcribe"
    )

    print("Translating to English...")

    translation_result = whisper_model.transcribe(
        local_audio_path,
        task="translate"
    )

    transcript = transcript_result["text"]
    translation = translation_result["text"]
    detected_language = transcript_result.get("language", "unknown")

    return transcript, translation, detected_language


def process_call(record, target_lang):
    call_id = record.get(ID_FIELD)
    source_collection = record.get("_source_collection", "unknown")
    print(f"\n=== Processing call: {call_id} (found in {source_collection}) ===")

    local_path = None

    try:
        local_path = download_audio_to_tempfile(record)

        transcript, translation, detected_lang = transcribe_audio(local_path)

        analysis = analyze_text({
            "text": translation,
            "language": detected_lang
        })
        
       
        print("\n========== CALL ANALYSIS ==========")
        print(f"Airline      : {analysis['airline']}")
        print(f"Call Nature  : {analysis['callnature']}")
        print(f"Route        : {analysis['route']}")
        print(f"Keywords     : {analysis['keywords']}")
        print(f"Numbers      : {analysis['numbers']}")
        print("==================================\n")
       

    finally:
        if local_path and os.path.exists(local_path):
            os.remove(local_path)


    result = {

    "call_id": call_id,
    "source_collection": source_collection,
    "calltime": record.get("calltime"),
    "calltype": record.get("calltype"),
    "custnumber": record.get("custnumber"),
    "duration": record.get("duration"),
    "extension": record.get("extension"),
    "source": record.get("source"),
    "tfn": record.get("tfn"),
    "detected_language": detected_lang,
    "transcript": transcript,
    "translated_to": target_lang,
    "translation": translation,
    "airline": analysis["airline"],
    "callnature": analysis["callnature"],
    "route": analysis["route"],
    "keywords": analysis["keywords"],
    }

    print(f"--- Transcript ({detected_lang}) ---\n{transcript}")
    print(f"\n--- Translation ({target_lang}) ---\n{translation}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe + translate call audio by call ID."
    )

    parser.add_argument(
        "call_ids",
        help="Comma-separated call IDs"
    )

    parser.add_argument(
        "--target-lang",
        default=DEFAULT_TARGET_LANG,
        help=f"Language to translate transcript into (default: {DEFAULT_TARGET_LANG})",
    )

    args = parser.parse_args()

    call_ids = [
        uid.strip()
        for uid in args.call_ids.split(",")
        if uid.strip()
    ]

    records = fetch_call_records(call_ids)

    if not records:
        print("No matching call records found.")
        sys.exit(1)

    results = []

    for record in records:
        try:
            result = process_call(record, args.target_lang)
            results.append(result)

        except Exception as e:
            print(f"❌ Failed to process {record.get(ID_FIELD)}: {e}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    json_path = os.path.join(
        OUTPUT_DIR,
        "results.json"
    )

    import json

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            results,
            f,
            indent=4,
            ensure_ascii=False,
            default=str
        )

    print(f"\nJSON saved to: {json_path}")

    print(
        f"\nDone. Processed {len(results)}/{len(records)} call(s) successfully."
    )


if __name__ == "__main__":
    print("Entering main()")
    main()
