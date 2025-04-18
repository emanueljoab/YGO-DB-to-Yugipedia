# YGO-DB-to-Yugipedia

This script extracts Decks from the [Yu-Gi-Oh! Card Database](https://www.db.yugioh-card.com/yugiohdb/) and formats them for [Yugipedia's Decklist template](https://yugipedia.com/wiki/Template:Decklist).

## Features

- **Extract Decks:** Pulls Deck data directly from the Official Yu-Gi-Oh! Card Database.
- **Format Decklists:** Converts the extracted data into a structured format that follows the {{Decklist}} template on Yugipedia.
- **Clipboard support:** The formatted Decklist is automatically copied to your clipboard.
- **Saves to file:** The Decklist is saved as a `.txt` file inside the `Decklists` folder.

## Usage

1. Download and extract the ZIP file.
2. Run `start.bat`.

## Notes

- No dependency installation or setup required; all runtime components are bundled.
- Only public Decks work. Make sure your Decks are public.
- If a card wasn't released in the TCG, its Japanese name will be displayed.
- The script is Windows-only.
