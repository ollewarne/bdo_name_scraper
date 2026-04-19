import requests
import time
import random
from datetime import datetime, timezone
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Name, Category, NameCategory
from sqlalchemy.exc import OperationalError
from logger import setup_logger

logger = setup_logger()
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "keepalives": 1,
        "keepalives_idle": 60,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "connect_timeout": 10,
    },
)
Session = sessionmaker(bind=engine)

NAMES_DIR = os.path.join(os.path.dirname(__file__), "./word_files")

PROXY_LIST_URL = os.getenv("PROXY_LIST_URL")
if not PROXY_LIST_URL:
    raise ValueError("PROXY_LIST_URL not set")

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL not set")

MAX_RETRIES = 10
MAX_PROXY_RETRIES = 3000
PROXY_TIMEOUT = 2
PROXY_FAILED = "proxy failed"

CHAR_TYPE = 1
FAMILY_TYPE = 2

SEARCH_TYPES = [CHAR_TYPE, FAMILY_TYPE]
REGIONS = ["NA", "EU"]

COLUMN_MAP = {
    ("NA", CHAR_TYPE): "available_na_char",
    ("NA", FAMILY_TYPE): "available_na_family",
    ("EU", CHAR_TYPE): "available_eu_char",
    ("EU", FAMILY_TYPE): "available_eu_family",
}


def load_proxies(url):
    proxies = requests.get(url)
    proxy_list = []
    for proxy in proxies.text.splitlines():
        if proxy.strip():
            proxy_list.append(proxy.strip())
    return proxy_list


def validate_proxy(proxy):
    proxy_dict = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
    try:
        requests.get(
            "https://httpbin.org/ip", proxies=proxy_dict, timeout=PROXY_TIMEOUT
        )
        return proxy_dict
    except Exception:
        return None


def get_working_proxy(proxies):
    print("looking for working proxy")
    for i in range(MAX_PROXY_RETRIES):
        print(f"attempt {i}", end="\r", flush=True)
        proxy = validate_proxy(random.choice(proxies))
        if proxy:
            print("found working proxy")
            return proxy
    assert WEBHOOK_URL is not None
    requests.post(WEBHOOK_URL, json={"content": "Failed: exhausted all proxy retries"})
    logger.warning("exhausted all proxy retries")
    return None


def check_name(name, region, search_type, proxy):
    if not proxy:
        return PROXY_FAILED
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                f"https://www.naeu.playblackdesert.com/en-US/Adventure?checkSearchText=False&region={region}&searchType={search_type}&searchKeyword={name}",
                proxies=proxy,
                timeout=15,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
            )
            if response.status_code == 429:
                time.sleep(2**attempt)
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            if not soup.find("div", class_="container adventure"):
                return PROXY_FAILED
            return soup.find("li", class_="no_result")
        except requests.exceptions.Timeout:
            return PROXY_FAILED
        except Exception:
            time.sleep(0.5)
            continue

    print("unable to do the check")
    return PROXY_FAILED


if __name__ == "__main__":
    requests.post(WEBHOOK_URL, json={"content": "started scraping names"})
    logger.info("started scraping names")
    proxies = load_proxies(PROXY_LIST_URL)
    proxy = get_working_proxy(proxies)
    logger.info(f"found working proxy {proxy}")

    session = Session()

    name_files = os.listdir(NAMES_DIR)

    for filename in name_files:
        if not filename.endswith(".txt"):
            continue
        category_lable = "unknown"
        try:
            category_lable = os.path.splitext(filename)[0].replace("_", " ").title()
            category_obj = (
                session.query(Category).filter_by(name=category_lable).first()
            )
            if not category_obj:
                category_obj = Category(name=category_lable)
                session.add(category_obj)
                session.flush()

            with open(os.path.join(NAMES_DIR, filename)) as file:
                names = file.readlines()
                for name in names:
                    try:
                        name_obj = (
                            session.query(Name).filter_by(name=name.strip()).first()
                        )
                        if not name_obj:
                            name_obj = Name(name=name.strip())
                            session.add(name_obj)
                            session.flush()

                        for region in REGIONS:
                            for search_type in SEARCH_TYPES:
                                available = 0
                                result = check_name(
                                    name.strip(), region, search_type, proxy
                                )
                                while result == PROXY_FAILED:
                                    proxy = get_working_proxy(proxies)
                                    if proxy is None:
                                        session.close()
                                        raise SystemExit(1)
                                    result = check_name(
                                        name.strip(), region, search_type, proxy
                                    )
                                if result:
                                    available = 1
                                col = COLUMN_MAP[(region, search_type)]
                                setattr(name_obj, col, available)
                                name_obj.last_checked = datetime.now(timezone.utc)
                                logger.info(f"added {name} - {col} - available: {available}")

                        existing = (
                            session.query(NameCategory)
                            .filter_by(name_id=name_obj.id, category_id=category_obj.id)
                            .first()
                        )
                        if not existing:
                            session.add(
                                NameCategory(
                                    name_id=name_obj.id, category_id=category_obj.id
                                )
                            )

                        if not any(
                            [
                                name_obj.available_eu_family,
                                name_obj.available_eu_char,
                                name_obj.available_na_family,
                                name_obj.available_na_char,
                            ]
                        ):
                            session.delete(name_obj)
                            logger.warning(f"{name} not available at all, deleting")
                        try:
                            session.commit()
                        except OperationalError as e:
                            requests.post(
                                WEBHOOK_URL,
                                json={"content": f"FATAL: DB connection lost - {e}"},
                            )
                            logger.error(f"fatal error: DB connection lost - {e}")
                            session.close()
                            raise SystemExit(1)
                        except Exception as e:
                            requests.post(
                                WEBHOOK_URL,
                                json={
                                    "content": f"FAILED: DB commit error on name '{name.strip()}' - {e}"
                                },
                            )
                            logger.warning(f"DB commit error on {name} - {e}")
                            session.rollback()
                            session.close()
                            session = Session()
                            continue
                        time.sleep(0.5)
                    except OperationalError as e:
                        requests.post(
                            WEBHOOK_URL,
                            json={"content": f"FATAL: DB connection lost - {e}"},
                        )
                        logger.error(f"fatal error: DB connection lost - {e}")
                        session.close()
                        raise SystemExit(1)
                    except Exception as e:
                        requests.post(
                            WEBHOOK_URL,
                            json={
                                "content": f"WARNING: DB error on name '{name.strip()}' - {e}"
                            },
                        )
                        logger.warning(f"DB commit error on {name} - {e}")
                        session.rollback()
                        session.close()
                        session = Session()
                        continue
        except OperationalError as e:
            requests.post(
                WEBHOOK_URL,
                json={"content": f"FATAL: DB connection lost - {e}"},
            )
            logger.error(f"fatal error: DB connection lost - {e}")
            session.close()
            raise SystemExit(1)
        except Exception as e:
            requests.post(
                WEBHOOK_URL,
                json={"content": f"WARNING: DB error on name '{category_lable}' - {e}"},
            )
            logger.warning(f"DB commit error on {category_lable} - {e}")
            session.rollback()
            session.close()
            session = Session()
            continue

    session.close()
    print("done scraping")
    logger.info("scraping done")
    requests.post(WEBHOOK_URL, json={"content": "done scraping names"})
