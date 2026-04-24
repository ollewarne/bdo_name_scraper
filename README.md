# BDO Name Scraper

Python scraper that checks name availability (character and family) across NA and EU regions in Black Desert Online.  
This page displays data collected with this scraper [BDO names](https://bdo-names.soew.se/)

## What it does

Reads names from `.txt` files in `word_files/`, checks each name against the BDO adventure page for all region/type combinations, and stores results in a PostgreSQL database.

## Things I'm working on

- [ ] add a queue and concurrency to speed up scraping large lists of names

## Requirements

- PostgreSQL database
- A proxy list URL (HTTP proxies)
- A Discord webhook URL

## Setup

1. Install dependencies:

```
pip install -r requirements.txt
```

2. Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://user:password@host:port/dbname
PROXY_LIST_URL=https://your-proxy-list-url
WEBHOOK_URL=https://discord.com/api/webhooks/...
```

3. Initialize the database:

```
python init_db.py
```

4. Add name files to `word_files/`. Each file should be a `.txt` with one name per line. The filename (without extension) becomes the category name.

## Usage

```
python scraper.py
```
