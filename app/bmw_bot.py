import os
import sys
import json
import time
import asyncio
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Set
from logging.handlers import TimedRotatingFileHandler

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.exceptions import TelegramNetworkError
from dotenv import load_dotenv

# =========================
# Configuration
# =========================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_IDS = [int(x) for x in os.getenv("CHAT_IDS", "").split(",") if x.strip()]
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
MAX_RETRIES = 3
TELEGRAM_DELAY = 1.2

GS_CRED = os.getenv("GS_CRED", "bmwparser111-4e64ca22a559.json")
GSHEET_NAME = os.getenv("GSHEET_NAME", "bmw_parser_data")

LOGDIR = "logs"
APP_LOG = os.path.join(LOGDIR, "app.log")
ERR_LOG = os.path.join(LOGDIR, "errors.log")
os.makedirs(LOGDIR, exist_ok=True)

# =========================
# Logging
# =========================
def setup_logging():
    logger = logging.getLogger("bmw_monitor")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    info_handler = TimedRotatingFileHandler(APP_LOG, when="midnight", backupCount=14, encoding="utf-8")
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(fmt)

    err_handler = logging.FileHandler(ERR_LOG, encoding="utf-8")
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(fmt)

    logger.handlers.clear()
    logger.addHandler(info_handler)
    logger.addHandler(err_handler)
    return logger

_logger = setup_logging()

def log_info(msg: str):
    print(msg, flush=True)
    _logger.info(msg)

def log_error(msg: str, exc: Optional[Exception] = None):
    print(msg, flush=True)
    if exc is not None:
        _logger.exception(f"{msg} | EXC: {exc}")
    else:
        _logger.error(msg)

# =========================
# Utilities
# =========================
def tail_file(path: str, max_bytes: int = 80000) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - max_bytes), os.SEEK_SET)
        return f.read().decode("utf-8", errors="ignore")

def html_escape_strict(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&#39;")
    )

def extract_last_cycle_block(text: str) -> str:
    """
    Returns log block:
    - completed cycle: [GSHEET Connection successful?] + [New cycle ...] ... [*] Cycle completed.
    - in progress:     [GSHEET Connection successful?] + [New cycle ...] ... <to end of file>
    If not found - last 40 lines.
    """
    lines = text.strip().splitlines()
    if not lines:
        return "Log is empty."

    # positions of cycle starts
    starts = [i for i, ln in enumerate(lines) if "] New monitoring cycle" in ln]
    if not starts:
        return "\n".join(lines[-40:])

    start = starts[-1]

    # end of cycle (if any)
    end = None
    for j in range(start, len(lines)):
        if "[*] Cycle completed" in lines[j]:
            end = j

    # pull "[GSHEET] Connection successful" a bit above the start (within 50 lines)
    gs_idx = None
    for k in range(start - 1, max(-1, start - 50), -1):
        if "[GSHEET] Connection successful" in lines[k]:
            gs_idx = k
            break

    block_start = gs_idx if gs_idx is not None else start
    block_end = (end + 1) if end is not None and end >= start else len(lines)
    block = "\n".join(lines[block_start:block_end]).strip()
    return block if block else "\n".join(lines[-40:])

def format_price(price) -> str:
    try:
        return f"{int(price):,}".replace(",", ".")
    except Exception:
        return str(price)

def check_image_url(url: str) -> bool:
    try:
        resp = requests.head(url, timeout=5)
        return resp.status_code == 200
    except Exception:
        return False

def car_url(vssId: str) -> str:
    return f"https://www.bmw.de/de-de/sl/gebrauchtwagen#/details/{vssId}"

def _to_plain_str(val) -> str:
    """Normalize localized/complex values to a string."""
    if val is None:
        return "—"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        for k in ("de_DE", "default_DE", "en_GB", "en_US"):
            v = val.get(k)
            if isinstance(v, str) and v.strip():
                return v
        for v in val.values():
            if isinstance(v, str) and v.strip():
                return v
        return json.dumps(val, ensure_ascii=False)
    if isinstance(val, list) and val:
        return _to_plain_str(val[0])
    return str(val)

def get_model_text(car: dict) -> str:
    m = car["vehicleSpecification"]["modelAndOption"]["model"]
    for key in ("marketingName", "salesDesignation", "modelDescription", "modelName"):
        if key in m:
            return _to_plain_str(m[key])
    return "—"

def get_gearbox(car: dict) -> str:
    mo = car["vehicleSpecification"]["modelAndOption"]
    return _to_plain_str(mo.get("transmission"))

def get_fuel(car: dict) -> str:
    mo = car["vehicleSpecification"]["modelAndOption"]
    return _to_plain_str(mo.get("baseFuelType") or mo.get("degreeOfElectrificationBasedFuelType"))

def get_price(car: dict) -> int:
    p = car.get("price", {}) or {}
    return p.get("grossSalesPrice") or p.get("modelSalesPriceGross") or 0

def get_mileage(car: dict) -> int:
    return car["vehicleLifeCycle"]["mileage"]["km"]

def format_car(car: dict):
    vssId = car["vssId"]
    model = get_model_text(car)
    price = format_price(get_price(car))
    mileage = get_mileage(car)
    gearbox = get_gearbox(car)
    fuel = get_fuel(car)
    url = car_url(vssId)
    msg = (
        f"<b>{model}</b>\n"
        f"<b>vssId:</b> <code>{vssId}</code>\n"
        f"💶 <b>Price:</b> {price} €\n"
        f"🛣️ <b>Mileage:</b> {mileage} km\n"
        f"⚙️ <b>Transmission:</b> {gearbox}\n"
        f"⛽️ <b>Fuel type:</b> {fuel}\n"
        f'<a href="{url}">Details</a>'
    )
    img_url = None
    if car.get("images"):
        for img in car["images"]:
            u = img.get("url")
            if u and check_image_url(u):
                img_url = u
                break
    return img_url, msg

# =========================
# BMW API (filters as in beta) + reliable pagination
# =========================
def build_beta_filters() -> dict:
    return {
        "searchContext": [{
            "model": {"marketingModelRange": {"value": ["X3_G01"]}},
            "degreeOfElectrificationBasedFuelType": {"value": ["DIESEL", "GASOLINE"]},
            "technicalData": {"powerBasedOnDegreeOfElectrificationPs": [{"maxValue": 200}]},
            "usedCarData": {"mileageRanges": [{"minValue": 0, "maxValue": 60000}]},
            "initialRegistrationDateRanges": [{"minValue": "2021-01-01", "maxValue": "2022-12-31"}]
        }],
        "resultsContext": {"sort": [{"by": "PRODUCTION_DATE", "order": "DESC"}]}
    }

def get_all_bmw_lots(data: dict, max_per_page: int = 100) -> List[dict]:
    url_base = "https://stolo-data-service.prod.stolo.eu-central-1.aws.bmw.cloud/vehiclesearch/search/de-de/gebrauchtwagen"
    headers = {
        "user-agent": "Mozilla/5.0",
        "content-type": "application/json",
        "origin": "https://www.bmw.de",
        "referer": "https://www.bmw.de/",
    }

    MAX_PAGES = 50
    all_hits: List[dict] = []
    seen_ids: Set[str] = set()
    start_index = 0
    total_expected: Optional[int] = None
    last_first_id: Optional[str] = None
    page = 0

    for attempt in range(MAX_RETRIES):
        try:
            while page < MAX_PAGES:
                url = f"{url_base}?maxResults={max_per_page}&startIndex={start_index}&brand=BMW&context=results-page"
                log_info(f"BMW API: startIndex={start_index}, page={page+1}")

                resp = requests.post(url, headers=headers, json=data, timeout=30)
                if resp.status_code not in (200, 201):
                    log_error(f"BMW API: {resp.status_code} {resp.text[:300]}")
                    if resp.status_code == 502:
                        time.sleep(5)
                        continue
                    break

                j = resp.json()
                hits = j.get("hits", []) or []

                if total_expected is None:
                    total_expected = j.get("totalResults") or j.get("total") or (j.get("pagination") or {}).get("total")
                    if total_expected:
                        log_info(f"BMW API: total_expected={total_expected}")

                if not hits:
                    log_info("BMW API: empty page -> stop")
                    break

                first_id = hits[0].get("vehicle", {}).get("vssId")
                if first_id and last_first_id == first_id:
                    log_info(f"BMW API: first record repeated ({first_id}) -> stop pagination")
                    break
                last_first_id = first_id

                new_unique = 0
                for h in hits:
                    vid = h.get("vehicle", {}).get("vssId")
                    if not vid or vid in seen_ids:
                        continue
                    seen_ids.add(vid)
                    all_hits.append(h)
                    new_unique += 1

                log_info(f" [+] Unique on page: {new_unique}, total: {len(all_hits)}")

                if len(hits) < max_per_page:
                    log_info("BMW API: last page (< max_per_page) -> stop")
                    break
                if total_expected and len(all_hits) >= total_expected:
                    log_info("BMW API: reached total_expected -> stop")
                    break

                start_index += max_per_page
                page += 1
            break
        except Exception as e:
            log_error(f"BMW API: attempt {attempt+1}/{MAX_RETRIES} failed", e)
            if attempt < MAX_RETRIES - 1:
                time.sleep(10)
            else:
                log_error("BMW API: all attempts exhausted - returning collected")
                return all_hits
    return all_hits

def extract_id_dict_from_hits(hits: List[dict]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for h in hits:
        v = h.get("vehicle")
        if v and "vssId" in v:
            out[v["vssId"]] = v
    return out

def compare_ids(old_ids: Set[str], new_ids: Set[str]) -> Tuple[Set[str], Set[str]]:
    return new_ids - old_ids, old_ids - new_ids

# =========================
# Google Sheets helpers
# =========================
def gs_open_sheet():
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_file(GS_CRED, scopes=[
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ])
    gc = gspread.authorize(creds)
    return gc.open(GSHEET_NAME).sheet1

def sheet_index_by_vssid(sheet) -> Dict[str, int]:
    values = sheet.get_all_values()
    if not values:
        return {}
    header = {name.strip(): i for i, name in enumerate(values[0])}
    if "vssId" not in header:
        log_error("In the Google Sheet header there is no column 'vssId'")
        return {}
    col = header["vssId"]
    idx: Dict[str, int] = {}
    for r, row in enumerate(values[1:], start=2):
        if col < len(row):
            v = (row[col] or "").strip()
            if v:
                idx[v] = r
    return idx

def header_index_map(sheet) -> dict:
    values = sheet.get_all_values()
    if not values:
        return {}
    return {name.strip(): i for i, name in enumerate(values[0])}

def row_is_incomplete(row: list, hmap: dict) -> bool:
    need = ["vssId","model","price","mileage","gearbox","fuel","url","date_added"]
    for key in need:
        idx = hmap.get(key)
        if idx is None or idx >= len(row):
            return True
        if (row[idx] or "").strip() == "":
            return True
    return False

def build_full_row(car: dict) -> list:
    return [
        car["vssId"],
        get_model_text(car),
        get_price(car),
        get_mileage(car),
        get_gearbox(car),
        get_fuel(car),
        car_url(car["vssId"]),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]

def update_row_A_H(sheet, row_idx: int, car: dict):
    sheet.update(range_name=f"A{row_idx}:H{row_idx}", values=[build_full_row(car)], value_input_option="RAW")

def add_or_update_row_to_sheet(sheet, car: dict, sheet_idx: Dict[str, int]):
    v = car["vssId"]
    if v in sheet_idx and sheet_idx[v] > 1:
        update_row_A_H(sheet, sheet_idx[v], car)
    else:
        sheet.append_row(build_full_row(car), value_input_option="RAW")

def repair_incomplete_rows(sheet, new_dict: dict) -> int:
    values = sheet.get_all_values()
    if not values:
        return 0
    hmap = header_index_map(sheet)
    repaired = 0
    for r, row in enumerate(values[1:], start=2):
        v_idx = hmap.get("vssId")
        if v_idx is None or v_idx >= len(row):
            continue
        vss = (row[v_idx] or "").strip()
        if not vss or not row_is_incomplete(row, hmap):
            continue
        car = new_dict.get(vss)
        if not car:
            continue
        try:
            update_row_A_H(sheet, r, car)
            repaired += 1
        except Exception as e:
            log_error(f"[GSHEET] Error repairing row vssId={vss} (row={r})", e)
    return repaired

def dedupe_vssid_rows(sheet) -> int:
    """Removes duplicates by vssId, keeping the first instance."""
    values = sheet.get_all_values()
    if not values:
        return 0
    header = {name.strip(): i for i, name in enumerate(values[0])}
    col = header.get("vssId")
    if col is None:
        log_error("In the Google Sheet header there is no column 'vssId'")
        return 0

    seen: Dict[str, int] = {}
    to_delete: List[int] = []
    for r, row in enumerate(values[1:], start=2):
        v = (row[col] if col < len(row) else "").strip()
        if not v:
            continue
        if v in seen:
            to_delete.append(r)
        else:
            seen[v] = r

    for r in sorted(to_delete, reverse=True):
        try:
            sheet.delete_rows(r)
            log_info(f"[GSHEET] DEDUPE: removed duplicate (row={r})")
        except Exception as e:
            log_error(f"[GSHEET] DEDUPE: failed to delete row {r}", e)
    return len(to_delete)

# =========================
# Telegram helpers
# =========================
async def tg_send_with_retry(coro_factory, attempts=3, base_delay=1.0) -> bool:
    for i in range(attempts):
        try:
            await coro_factory()
            return True
        except TelegramNetworkError as e:
            log_error(f"[TELEGRAM] Network error, try {i+1}/{attempts}", e)
        except Exception as e:
            log_error("[TELEGRAM] Send failed", e)
            break
        await asyncio.sleep(base_delay * (2 ** i))
    return False

# =========================
# Telegram bot
# =========================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(Command("status"))
async def status_handler(message: types.Message):
    try:
        raw = tail_file(APP_LOG, 80000)  # take more to ensure we capture the cycle
        if not raw:
            await message.answer("Log file is missing.")
            return
        block = extract_last_cycle_block(raw)
        safe = html_escape_strict(block)
        await message.answer(f"<pre>{safe}</pre>", parse_mode=ParseMode.HTML)
    except Exception as e:
        log_error("Error in /status", e)
        await message.answer("Failed to read log.")

@dp.message(Command("logs"))
async def logs_handler(message: types.Message):
    try:
        if not os.path.exists(APP_LOG):
            await message.answer("Log file is missing.")
            return
        await message.answer_document(document=FSInputFile(APP_LOG), caption="Full log (app.log)")
    except Exception as e:
        log_error("Error in /logs", e)
        await message.answer("Failed to send log.")

@dp.message(Command("errors"))
async def errors_handler(message: types.Message):
    try:
        if not os.path.exists(ERR_LOG):
            await message.answer("Error log file is missing.")
            return
        await message.answer_document(document=FSInputFile(ERR_LOG), caption="Error log (errors.log)")
    except Exception as e:
        log_error("Error in /errors", e)
        await message.answer("Failed to send error log.")

@dp.message(Command("restart"))
async def restart_handler(message: types.Message):
    try:
        user_id = message.from_user.id if message.from_user else None
        if ADMIN_IDS and user_id not in ADMIN_IDS:
            await message.answer("Insufficient permissions for /restart.")
            return
        await message.answer("♻️ Restarting...")
    except Exception as e:
        log_error("Error before restart", e)
    asyncio.get_running_loop().call_later(
        0.5, lambda: os.execv(sys.executable, [sys.executable] + sys.argv)
    )

# =========================
# Main monitoring
# =========================
async def monitor_loop(data: dict):
    # Google Sheet connection
    try:
        sheet = gs_open_sheet()
        log_info("[GSHEET] Connection successful")
    except Exception as e:
        log_error("[GSHEET] Connection error", e)
        sheet = None

    # One-time deduplication on startup
    if sheet:
        try:
            d = dedupe_vssid_rows(sheet)
            if d:
                log_info(f"[GSHEET] DEDUPE: removed duplicates: {d}")
        except Exception as e:
            log_error("[GSHEET] DEDUPE: startup error", e)

    while True:
        cycle_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_info(f"[{cycle_ts}] New monitoring cycle")

        # 1) Get fresh lots
        hits = await asyncio.to_thread(get_all_bmw_lots, data)
        new_dict = extract_id_dict_from_hits(hits)
        new_ids = set(new_dict.keys())
        log_info(f"[+] Received cars (unique): {len(new_ids)}")

        if sheet:
            # Periodic deduplication
            try:
                d = dedupe_vssid_rows(sheet)
                if d:
                    log_info(f"[GSHEET] DEDUPE: removed duplicates: {d}")
            except Exception as e:
                log_error("[GSHEET] DEDUPE: cycle error", e)

            # 2) Table state
            try:
                sheet_idx = sheet_index_by_vssid(sheet)  # {vssId: row}
                old_ids = set(sheet_idx.keys())
            except Exception as e:
                log_error("[GSHEET] Error reading sheet index", e)
                sheet_idx = {}
                old_ids = set()
        else:
            sheet_idx = {}
            old_ids = set()

        # 2b) Repair incomplete rows
        if sheet:
            try:
                repaired = repair_incomplete_rows(sheet, new_dict)
                if repaired:
                    log_info(f"[GSHEET] Repaired rows: {repaired}")
            except Exception as e:
                log_error("[GSHEET] Error repairing incomplete rows", e)

        # 3) Deltas by vssId
        added, removed = compare_ids(old_ids, new_ids)
        log_info(f"[DIFF] added={len(added)} removed={len(removed)}")

        # 4a) Remove disappeared ones (by descending indices), alerts after fact
        if sheet and removed:
            rows_to_delete: List[Tuple[int, str]] = []
            for v in removed:
                r = sheet_idx.get(v)
                if r:
                    rows_to_delete.append((r, v))
            rows_to_delete.sort(key=lambda x: x[0], reverse=True)

            actually_deleted: List[str] = []
            for r, v in rows_to_delete:
                try:
                    sheet.delete_rows(r)
                    log_info(f"[GSHEET] Deleted row vssId={v} (row={r})")
                    actually_deleted.append(v)
                except Exception as e:
                    log_error(f"[GSHEET] Failed to delete vssId={v} (row={r})", e)

            for v in actually_deleted:
                txt = (
                    "❌ Lot disappeared from results\n"
                    f"<b>vssId:</b> <code>{v}</code>\n"
                    f'<a href="{car_url(v)}">Card</a>'
                )
                for chat_id in CHAT_IDS:
                    ok = await tg_send_with_retry(lambda: bot.send_message(chat_id, txt))
                    if ok:
                        log_info(f"[TG] GONE {v} → chat {chat_id}")
                    await asyncio.sleep(TELEGRAM_DELAY)

        # 4b) Add new ones (update if already exists, otherwise append)
        if sheet and added:
            added_cnt = 0
            sheet_idx = sheet_index_by_vssid(sheet)  # re-read index after deletions
            for v in added:
                car = new_dict.get(v)
                if not car:
                    continue
                try:
                    add_or_update_row_to_sheet(sheet, car, sheet_idx)
                    added_cnt += 1
                except Exception as e:
                    log_error(f"[GSHEET] Error adding/updating {v}", e)
            if added_cnt:
                log_info(f"[GSHEET] Added/updated rows: {added_cnt}")

        # 5) Alerts about new lots
        for v in added:
            car = new_dict.get(v)
            if not car:
                continue
            img_url, msg = format_car(car)
            for chat_id in CHAT_IDS:
                if img_url:
                    ok = await tg_send_with_retry(lambda: bot.send_photo(chat_id, photo=img_url, caption=msg))
                else:
                    ok = await tg_send_with_retry(lambda: bot.send_message(chat_id, msg))
                if ok:
                    log_info(f"[TG] NEW {v} → chat {chat_id}")
                await asyncio.sleep(TELEGRAM_DELAY)

        log_info("[*] Cycle completed.")
        await asyncio.sleep(POLL_INTERVAL)

async def main():
    data = build_beta_filters()
    monitor_task = asyncio.create_task(monitor_loop(data))
    await dp.start_polling(bot)
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    try:
        if not BOT_TOKEN or not CHAT_IDS:
            print("Configuration error: check .env (BOT_TOKEN, CHAT_IDS)", flush=True)
            sys.exit(1)
        asyncio.run(main())
    except KeyboardInterrupt:
        log_info("=== BMW Monitor stopped by KeyboardInterrupt ===")
    except Exception as e:
        log_error("=== Unhandled exception at top-level ===", e)