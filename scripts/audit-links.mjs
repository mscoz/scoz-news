#!/usr/bin/env node

import { access, readdir, readFile } from "node:fs/promises";
import path from "node:path";

const DATA_DIR = "data";
const DEFAULT_HTML = "index.html";
const REQUEST_TIMEOUT_MS = 12_000;
const CONCURRENCY = 12;
const ALLOWED_RESTRICTED_STATUSES = new Set([401, 403, 429]);
const GENERIC_NOT_FOUND_PATTERNS = [
  "article_not_found",
  "/404",
  "page-not-found",
  "page_not_found",
];

async function fileExists(filePath) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function latestWeekFile() {
  const files = (await readdir(DATA_DIR))
    .filter((file) => file.endsWith(".json"))
    .sort()
    .reverse();

  if (!files.length) {
    throw new Error(`Nenhum arquivo JSON encontrado em ${DATA_DIR}/`);
  }

  return path.join(DATA_DIR, files[0]);
}

async function defaultSourcePath() {
  if (await fileExists(DEFAULT_HTML)) return DEFAULT_HTML;
  return latestWeekFile();
}

function parseItemsFromHtml(html) {
  const items = [];
  const panels = html.split(/(?=<div class="tab-panel)/);
  const itemRe =
    /<div class="acc-item"[^>]*>[\s\S]*?<span class="acc-title">([^<]*)<\/span>[\s\S]*?class="btn-link" href="([^"]+)"/g;

  for (const chunk of panels) {
    const panelMatch = chunk.match(/data-panel="([^"]+)"/);
    if (!panelMatch) continue;
    const category = panelMatch[1];
    let match;
    while ((match = itemRe.exec(chunk)) !== null) {
      items.push({ category, title: match[1].trim(), url: match[2] });
    }
  }

  return items;
}

async function loadAuditItems(sourcePath) {
  if (sourcePath.endsWith(".html")) {
    const html = await readFile(sourcePath, "utf8");
    return { sourcePath, items: parseItemsFromHtml(html) };
  }

  const data = JSON.parse(await readFile(sourcePath, "utf8"));
  if (!data?.items || typeof data.items !== "object") {
    throw new Error("JSON invalido: campo items ausente");
  }

  const items = Object.entries(data.items).flatMap(([category, categoryItems]) =>
    categoryItems.map((item) => ({ category, title: item.title, url: item.url })),
  );
  return { sourcePath, items };
}

function parseRedditPath(url) {
  const match = url.match(/reddit\.com\/r\/([^/]+)\/comments\/([^/]+)/i);
  if (!match) return null;
  return { subreddit: match[1].toLowerCase(), postId: match[2].toLowerCase() };
}

async function fetchWithTimeout(url, method = "GET") {
  return fetch(url, {
    method,
    redirect: "follow",
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    headers: { "user-agent": "scoz-news-link-audit/1.0" },
  });
}

async function auditRedditUrl(url) {
  const requested = parseRedditPath(url);
  if (!requested) return { ok: false, reason: "formato Reddit invalido" };

  const endpoint = `https://www.reddit.com/oembed?url=${encodeURIComponent(url)}`;
  const response = await fetchWithTimeout(endpoint);
  if (!response.ok) {
    return { ok: false, reason: `Reddit oEmbed HTTP ${response.status}` };
  }

  const payload = await response.json();
  const canonicalUrl = payload.html?.match(
    /https:\/\/www\.reddit\.com\/r\/[^/"<]+\/comments\/[^/"<]+\/[^"<]*/i,
  )?.[0];
  const canonical = canonicalUrl ? parseRedditPath(canonicalUrl) : null;

  if (!canonical) {
    return { ok: false, reason: "Reddit oEmbed sem URL canonica" };
  }

  if (
    requested.subreddit !== canonical.subreddit ||
    requested.postId !== canonical.postId
  ) {
    return {
      ok: false,
      reason: `Reddit aponta para r/${canonical.subreddit}, nao r/${requested.subreddit}`,
    };
  }

  return { ok: true, status: response.status, finalUrl: canonicalUrl };
}

async function auditHttpUrl(url) {
  let response = await fetchWithTimeout(url, "HEAD");
  if (response.status === 405 || response.status === 501) {
    response = await fetchWithTimeout(url, "GET");
  }
  await response.body?.cancel?.();

  const statusAllowed =
    response.ok || ALLOWED_RESTRICTED_STATUSES.has(response.status);
  const lowerFinalUrl = response.url.toLowerCase();
  const genericNotFound = GENERIC_NOT_FOUND_PATTERNS.some((pattern) =>
    lowerFinalUrl.includes(pattern),
  );

  if (!statusAllowed) {
    return { ok: false, reason: `HTTP ${response.status}`, finalUrl: response.url };
  }

  if (genericNotFound) {
    return {
      ok: false,
      reason: "redirecionou para pagina generica de nao encontrado",
      finalUrl: response.url,
    };
  }

  return { ok: true, status: response.status, finalUrl: response.url };
}

async function auditUrl(url) {
  const trimmed = url?.trim();
  if (!trimmed) {
    return { ok: false, reason: "URL vazia", url: trimmed || "" };
  }

  try {
    const result = parseRedditPath(trimmed)
      ? await auditRedditUrl(trimmed)
      : await auditHttpUrl(trimmed);
    return { url: trimmed, ...result };
  } catch (error) {
    return {
      ok: false,
      url: trimmed,
      reason: `${error.name}: ${error.message}`,
    };
  }
}

async function mapPool(items, concurrency, fn) {
  const results = new Array(items.length);
  let index = 0;

  async function worker() {
    while (index < items.length) {
      const current = index++;
      results[current] = await fn(items[current], current);
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(concurrency, items.length) }, worker),
  );
  return results;
}

async function main() {
  const sourcePath = process.argv[2] || (await defaultSourcePath());
  const { items } = await loadAuditItems(sourcePath);
  if (!items.length) {
    throw new Error(`Nenhuma noticia encontrada em ${sourcePath}`);
  }

  const urlCache = new Map();
  async function auditCached(entry) {
    const url = entry.url?.trim();
    if (!url) {
      return { ok: false, category: entry.category, title: entry.title, url: "", reason: "URL vazia" };
    }
    if (!urlCache.has(url)) {
      urlCache.set(url, auditUrl(url));
    }
    const result = await urlCache.get(url);
    return { category: entry.category, title: entry.title, ...result };
  }

  const results = await mapPool(items, CONCURRENCY, auditCached);
  let failureCount = 0;

  for (const result of results) {
    const marker = result.ok ? "OK" : "ERRO";
    console.log(`${marker} [${result.category}] ${result.title}`);
    if (!result.ok) {
      failureCount++;
      console.log(`  ${result.reason}: ${result.url}`);
    }
  }

  console.log(`\n${sourcePath}: ${results.length} link(s), ${failureCount} erro(s)`);
  if (failureCount) process.exitCode = 1;
}

await main();
