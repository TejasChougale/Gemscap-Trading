# storage.py
import aiosqlite
import asyncio
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import csv

DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS ticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    ts TEXT NOT NULL,
    price REAL NOT NULL,
    size REAL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ticks_symbol_ts ON ticks(symbol, ts);
"""

class AsyncStorage:
    """
    Async storage manager using aiosqlite with a background writer queue.
    - Saves ticks to SQLite in batches (WAL mode)
    - Appends each tick to per-symbol CSV files and a combined ticks_all.csv in a background thread
    Methods:
      - start(): initialize DB and spawn writer task
      - enqueue_tick(tick): push tick to writer queue (async)
      - close(): flush queue and close DB
      - fetch_recent(limit): async read
    """

    def __init__(self, path: Optional[str] = "ticks.db", csv_dir: Optional[str] = "csv_data"):
        self.path = path or "ticks.db"
        self.csv_dir = csv_dir or "csv_data"
        self._queue: asyncio.Queue = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None
        self._db: Optional[aiosqlite.Connection] = None
        self._running = False
        os.makedirs(self.csv_dir, exist_ok=True)

    async def start(self):
        """Initialize DB and start writer task (should be called on the event loop)."""
        # ensure parent dir exists
        db_dir = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(db_dir, exist_ok=True)
        self._db = await aiosqlite.connect(self.path, timeout=30.0)
        # use WAL and busy timeout to reduce locks
        await self._db.execute("PRAGMA journal_mode=WAL;")
        await self._db.execute("PRAGMA synchronous=NORMAL;")
        await self._db.execute("PRAGMA busy_timeout=5000;")
        # initialize schema
        await self._db.executescript(DB_SCHEMA)
        await self._db.commit()
        self._running = True
        # spawn writer task on current loop
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._writer_loop())

    async def _writer_loop(self):
        """Consume queue and write to sqlite in batches; also append to CSVs using thread executor."""
        if self._db is None:
            return
        while self._running:
            try:
                # wait for at least one tick (timeout so we can check _running)
                try:
                    first = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                batch = [first]
                # drain up to 200 more quickly
                for _ in range(200):
                    try:
                        item = self._queue.get_nowait()
                        batch.append(item)
                    except asyncio.QueueEmpty:
                        break

                # write batch to sqlite transaction
                try:
                    await self._db.execute("BEGIN")
                    stmt = "INSERT INTO ticks (symbol, ts, price, size) VALUES (?, ?, ?, ?)"
                    for t in batch:
                        try:
                            await self._db.execute(stmt, (t['symbol'], t['ts'], float(t['price']), float(t.get('size', 0.0))))
                        except Exception:
                            # ignore per-row failures
                            continue
                    await self._db.commit()
                except Exception:
                    # attempt to rollback in case of error
                    try:
                        await self._db.rollback()
                    except Exception:
                        pass

                # append batch to CSV files off the event loop (thread)
                try:
                    await asyncio.to_thread(self._append_batch_to_csv, batch)
                except Exception:
                    # don't let CSV failures kill the writer
                    pass

            except Exception:
                # swallow and sleep briefly to keep loop alive
                await asyncio.sleep(0.2)
                continue

    def _append_batch_to_csv(self, batch: List[Dict[str, Any]]):
        """
        Synchronous function run in a thread to append ticks to CSVs.
        Writes:
         - csv_dir/ticks_all.csv  (global)
         - csv_dir/{SYMBOL}.csv   (per-symbol)
        """
        # header for CSV files
        header = ["symbol", "ts", "price", "size"]
        all_path = os.path.join(self.csv_dir, "ticks_all.csv")
        # open global combined file in append mode
        try:
            first_all = not os.path.exists(all_path)
            with open(all_path, "a", newline="", encoding="utf-8") as f_all:
                writer_all = csv.writer(f_all)
                if first_all:
                    writer_all.writerow(header)
                for t in batch:
                    writer_all.writerow([t.get("symbol"), t.get("ts"), t.get("price"), t.get("size", 0.0)])
        except Exception:
            # best-effort: ignore CSV write errors
            pass

        # per-symbol files (group by symbol to minimize opens)
        per_sym = {}
        for t in batch:
            sym = str(t.get("symbol") or "UNKNOWN").upper()
            if sym not in per_sym:
                per_sym[sym] = []
            per_sym[sym].append(t)

        for sym, rows in per_sym.items():
            try:
                sym_file = os.path.join(self.csv_dir, f"{sym}.csv")
                first_sym = not os.path.exists(sym_file)
                with open(sym_file, "a", newline="", encoding="utf-8") as f_sym:
                    writer = csv.writer(f_sym)
                    if first_sym:
                        writer.writerow(header)
                    for t in rows:
                        writer.writerow([t.get("symbol"), t.get("ts"), t.get("price"), t.get("size", 0.0)])
            except Exception:
                # ignore per-symbol write failures
                pass

    async def enqueue_tick(self, tick: Dict[str, Any]):
        """Put a tick into the write queue (async)."""
        try:
            await self._queue.put(tick)
        except Exception:
            pass

    async def close(self):
        """Stop writer, flush remaining items and close DB."""
        self._running = False
        # give writer a short moment to flush
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=1.0)
            except Exception:
                try:
                    self._task.cancel()
                    await asyncio.sleep(0.05)
                except Exception:
                    pass
        if self._db:
            try:
                await self._db.commit()
            except Exception:
                pass
            try:
                await self._db.close()
            except Exception:
                pass
            self._db = None

    async def fetch_recent(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Fetch recent ticks (async)."""
        if not os.path.exists(self.path):
            return []
        # try to use open connection if available
        if self._db:
            try:
                cur = await self._db.execute("SELECT symbol, ts, price, size FROM ticks ORDER BY id DESC LIMIT ?", (limit,))
                rows = await cur.fetchall()
                return [dict(r) for r in rows]
            except Exception:
                pass
        # fallback: open temporary read connection
        conn = await aiosqlite.connect(self.path)
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT symbol, ts, price, size FROM ticks ORDER BY id DESC LIMIT ?", (limit,))
        rows = await cur.fetchall()
        await conn.close()
        return [dict(r) for r in rows]
