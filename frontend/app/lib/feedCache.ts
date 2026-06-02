/**
 * feedCache.ts — Lightweight IndexedDB cache for feed data
 *
 * Stale-while-revalidate pattern: cached stories render instantly on repeat
 * visits while fresh data fetches in the background. No external dependencies
 * — raw IndexedDB with Promise wrappers (~0 bytes added to bundle vs idb-keyval).
 *
 * TTL is advisory — callers get stale data and decide whether to revalidate.
 * All operations fail silently (cache is optional, never blocks rendering).
 */

const DB_NAME = "void-feed-cache";
const STORE = "cache";
const VERSION = 1;

/** 35 minutes — pipeline runs 3x daily (~8h apart), brief staleness is acceptable */
const TTL_MS = 35 * 60 * 1000;

export interface CacheEntry<T> {
  data: T;
  timestamp: number;
  edition: string;
}

/** Open (or create) the IndexedDB database. SSR-safe: rejects when indexedDB is absent. */
function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("IndexedDB not available"));
      return;
    }
    const req = indexedDB.open(DB_NAME, VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/**
 * Retrieve a cached entry by key. Returns null on miss or any error.
 * The entry is returned even if stale — caller decides via `isFresh()`.
 */
export async function cacheGet<T>(key: string): Promise<CacheEntry<T> | null> {
  try {
    const db = await openDB();
    return new Promise((resolve) => {
      const tx = db.transaction(STORE, "readonly");
      const req = tx.objectStore(STORE).get(key);
      req.onsuccess = () => {
        const entry = req.result as CacheEntry<T> | undefined;
        resolve(entry ?? null);
      };
      req.onerror = () => resolve(null);
    });
  } catch {
    return null;
  }
}

/**
 * Store data under key with current timestamp and edition tag.
 * Fails silently — cache writes must never block the UI.
 */
export async function cacheSet<T>(key: string, data: T, edition: string): Promise<void> {
  try {
    const db = await openDB();
    const entry: CacheEntry<T> = { data, timestamp: Date.now(), edition };
    return new Promise((resolve) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put(entry, key);
      tx.oncomplete = () => resolve();
      tx.onerror = () => resolve();
    });
  } catch {
    // fail silently — cache is optional
  }
}

/** Check whether a cache entry is within the TTL window. */
export function isFresh(entry: CacheEntry<unknown>): boolean {
  return Date.now() - entry.timestamp < TTL_MS;
}
