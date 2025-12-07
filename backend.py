# backend.py
import asyncio
import websockets
import threading
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import random
import queue

from storage import AsyncStorage

logger = logging.getLogger("binance_ingestor")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


class BinanceIngestor:
    def __init__(self, symbols: List[str], out_queue: "queue.Queue[Dict[str,Any]]", db_path: Optional[str] = None, csv_dir: Optional[str] = "csv_data", reconnect_secs: float = 3.0):
        self.symbols = [s.lower() for s in symbols]
        self.out_queue = out_queue
        self.reconnect_secs = reconnect_secs
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.running = False
        # pass csv_dir so storage writes CSVs where we want
        self._storage = AsyncStorage(db_path or "ticks.db", csv_dir=csv_dir)
        self._demo_mode = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws_tasks: List[asyncio.Task] = []
        self._log_lines: List[str] = []

    def is_running(self) -> bool:
        return bool(self.running)

    def start(self):
        if self._thread and self._thread.is_alive():
            self._log("Ingestor already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.running = True
        self._log("Ingestor thread started")

    def stop(self, wait_seconds: float = 4.0):
        self._log("Stop requested")
        self._stop_event.set()
        if self._loop and self._loop.is_running():
            try:
                fut = asyncio.run_coroutine_threadsafe(self._shutdown_async(), self._loop)
                fut.result(timeout=wait_seconds)
            except Exception as e:
                self._log(f"Error during async shutdown: {e}")
        if self._thread:
            self._thread.join(timeout=wait_seconds)
        self.running = False
        self._log("Ingestor stopped")

    def _run_loop(self):
        try:
            loop = asyncio.new_event_loop()
            self._loop = loop
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._main())
        except Exception as e:
            self._log(f"Unhandled exception in ingestor thread: {e}")
        finally:
            try:
                if self._loop and not self._loop.is_closed():
                    self._loop.close()
            except Exception:
                pass
            self._loop = None
            self.running = False
            self._log("Background loop exited")

    async def _main(self):
        self._log("Async main started")
        try:
            await self._storage.start()
        except Exception as e:
            self._log(f"Storage start error: {e}")

        for s in self.symbols:
            t = asyncio.create_task(self._run_symbol_loop(s))
            self._ws_tasks.append(t)

        if self._demo_mode:
            self._ws_tasks.append(asyncio.create_task(self._demo_injector(0.1)))

        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            self._log("Main cancelled")
        finally:
            for t in list(self._ws_tasks):
                t.cancel()
            await asyncio.sleep(0.05)
            try:
                await self._storage.close()
            except Exception as e:
                self._log(f"Storage close error: {e}")
            self._log("Async main exiting")

    async def _run_symbol_loop(self, symbol: str):
        url = f"wss://fstream.binance.com/ws/{symbol}@trade"
        backoff = self.reconnect_secs
        while not self._stop_event.is_set() and not self._demo_mode:
            try:
                self._log(f"Connecting {symbol} -> {url}")
                async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                    self._log(f"Connected {symbol}")
                    backoff = self.reconnect_secs
                    async for message in ws:
                        if self._stop_event.is_set():
                            break
                        try:
                            j = json.loads(message)
                        except Exception:
                            continue
                        tick = self._normalize(j)
                        if tick:
                            await self._handle_tick(tick)
            except asyncio.CancelledError:
                self._log(f"Symbol task cancelled {symbol}")
                break
            except Exception as e:
                self._log(f"WS error {symbol}: {e}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 1.5, 30.0)
                continue
        self._log(f"Exiting ws loop for {symbol}")

    def _normalize(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            ts_ms = int(msg.get("E", msg.get("T", time.time() * 1000)))
            symbol = msg.get("s") or msg.get("symbol") or "UNKNOWN"
            price_f = None
            for k in ("p","price","c"):
                if k in msg:
                    try:
                        price_f = float(msg[k])
                        break
                    except Exception:
                        continue
            if price_f is None:
                return None
            size_f = 0.0
            for k in ("q","l","qty","size"):
                if k in msg:
                    try:
                        size_f = float(msg[k])
                        break
                    except Exception:
                        continue
            iso_ts = datetime.utcfromtimestamp(ts_ms / 1000.0).isoformat() + "Z"
            return {"symbol": symbol.upper(), "ts": iso_ts, "price": price_f, "size": size_f}
        except Exception:
            return None

    async def _handle_tick(self, tick: Dict[str, Any]):
        try:
            self.out_queue.put_nowait(tick)
        except queue.Full:
            try:
                self.out_queue.put(tick, timeout=0.1)
            except Exception:
                pass
        try:
            await self._storage.enqueue_tick(tick)
        except Exception as e:
            self._log(f"Storage enqueue error: {e}")

    async def _demo_injector(self, interval_secs: float = 0.2):
        self._log("Demo injector started")
        while not self._stop_event.is_set() and self._demo_mode:
            for sym in self.symbols:
                now_ms = int(time.time() * 1000)
                base = 90000 if sym.lower().startswith("btc") else (3000 if sym.lower().startswith("eth") else 100)
                price = base + (random.random() - 0.5) * (base * 0.002)
                tick = {"symbol": sym.upper(), "ts": datetime.utcfromtimestamp(now_ms / 1000.0).isoformat() + "Z", "price": round(price, 2), "size": round(random.random() * 0.5, 6)}
                try:
                    await self._handle_tick(tick)
                except Exception:
                    pass
            await asyncio.sleep(interval_secs)
        self._log("Demo injector exiting")

    def enable_demo_mode(self, enable: bool = True):
        self._demo_mode = bool(enable)
        self._log(f"Demo mode set to {self._demo_mode}")
        if self._demo_mode and self._loop and self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self._demo_injector(0.15), self._loop)
            except Exception:
                pass

    def inject_demo_tick_sync(self, sym: str = "btcusdt"):
        now_ms = int(time.time() * 1000)
        base = 90000 if sym.lower().startswith("btc") else 3000
        price = base + (random.random() - 0.5) * (base * 0.002)
        tick = {"symbol": sym.upper(), "ts": datetime.utcfromtimestamp(now_ms / 1000.0).isoformat() + "Z", "price": round(price, 2), "size": round(random.random() * 0.5, 6)}
        try:
            self.out_queue.put_nowait(tick)
        except queue.Full:
            try:
                self.out_queue.put(tick, timeout=0.1)
            except Exception:
                pass
        if self._loop and self._loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self._storage.enqueue_tick(tick), self._loop)
            except Exception:
                pass

    async def _shutdown_async(self):
        self._log("Shutdown: cancelling tasks")
        for t in list(self._ws_tasks):
            try:
                t.cancel()
            except Exception:
                pass
        self._ws_tasks.clear()
        self._demo_mode = False
        await asyncio.sleep(0.05)
        try:
            await self._storage.close()
        except Exception as e:
            self._log(f"Shutdown storage error: {e}")

    def _log(self, msg: str):
        s = f"{datetime.utcnow().isoformat()} {msg}"
        self._log_lines.append(s)
        logger.info(msg)

    def get_logs(self, last_n: int = 200):
        return self._log_lines[-last_n:]
