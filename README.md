Multilingual Call Transcription & Analysis Pipeline

An end-to-end Python pipeline that retrieves customer call recordings from MongoDB, transcribes multilingual audio using OpenAI Whisper, translates conversations into English, and extracts structured business insights using NLP.

## Features
- Fetches call records from MongoDB
- Downloads call recordings from remote URLs
- Transcribes audio in its original language
- Generates English translations
- Detects spoken language automatically
- Extracts airline names using variant mapping and false-positive filtering
- Predicts call nature (Sales / New Booking / Potential / Non-Sales)
- Detects travel routes
- Extracts keywords
- Extracts numbers and monetary values
- Exports results as structured JSON

## Workflow

```
MongoDB
    │
    ▼
Fetch Call Record
    │
    ▼
Download Audio
    │
    ▼
OpenAI Whisper
    ├── Original Transcript
    └── English Translation
              │
              ▼
       NLP Analysis Engine
              │
              ├── Airline Detection
              ├── Route Detection
              ├── Keyword Extraction
              ├── Number Extraction
              └── Call Nature Prediction
              │
              ▼
         JSON Output
```
## Tech Stack

- Python
- OpenAI Whisper
- MongoDB
- Requests
- Regular Expressions
- JSON
- argparse
## Project Structure

```
call_translation_pipeline/
│
├── call_translate.py          # Main pipeline
├── dowser_analyse.py          # NLP analysis module
├── airline_variants.json      # Airline aliases
├── keywords.txt               # Business keywords
├── call_outputs/
│   └── results.json
└── README.md
```
## Running the Project

Single Call ID

```bash
python call_translate.py ********
```

Multiple Call IDs

```bash
python call_translate.py 
```
## Example Output

```json
{
    "call_id": "********",
    "language": "fr",
    "transcript": "Bonjour, bienvenue chez Condor...",
    "translation": "Hello, welcome to Condor...",
    "airline": "Condor",
    "callnature": "Sales",
    "route": "Paris -> Frankfurt",
    "keywords": "refund,price",
    "numbers": "250"
}
```

## NLP Features

### Airline Detection
- Airline variant mapping
- Alias support
- False-positive filtering
- Ordered airline detection
- Multiple airline extraction

### Call Classification
- Sales
- New Booking
- Potential
- Non-Sales

### Information Extraction
- Travel Route
- Keywords
- Numeric values
- Currency values

## Future Improvements
- Speaker diarization
- Sentiment analysis
- Intent classification using LLMs
- Call summarization
- REST API deployment
- Dashboard integration
- Batch processing
- Vector search for transcripts


## License

This project is intended for learning and internal use.
