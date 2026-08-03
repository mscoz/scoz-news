#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

const REQUEST_TIMEOUT_MS = 12_000;
const CONCURRENCY = 12;
const ALLOWED_RESTRICTED_STATUSES = new Set([401, 403, 429]);
const GENERIC_NOT_FOUND_PATTERNS = [
  "article_not_found",
  "/404",
  "page-not-found",
  "page_not_found",
];

export async function loadAuditItems(sourcePath) {
  if (!sourcePath?.endsWith(".json")) {
    throw new Error(
      "Informe um arquivo semanal JSON, por exemplo data/2026-07-27.json",
    );
  }

  const data = JSON.parse(await readFile(sourcePath, "utf8"));
  if (!data?.items || typeof data.items !== "object") {
    throw new Error("JSON invalido: campo items ausente");
  }

  const items = Object.entries(data.items).flatMap(([category, categoryItems]) => {
    if (!Array.isArray(categoryItems)) {
      throw new Error(`JSON invalido: categoria ${category} deve ser uma lista`);
    }
    return categoryItems.map((item) => ({
      category,
      title: item.title,
      url: item.url,
    }));
  });
  return { sourcePath, items };
}

async function fetchWithTimeout(url, method = "GET") {
  return fetch(url, {
    method,
    redirect: "follow",
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    headers: { "user-agent": "scoz-news-link-audit/1.0" },
  });
}

async function auditHttpUrl(url, request = fetchWithTimeout) {
  let response = await request(url, "HEAD");
  if (response.status === 405 || response.status === 501) {
    response = await request(url, "GET");
  }
  await response.body?.cancel?.();

  const restricted = ALLOWED_RESTRICTED_STATUSES.has(response.status);
  const statusAllowed = response.ok || restricted;
  const lowerFinalUrl = response.url.toLowerCase();
  const genericNotFound = GENERIC_NOT_FOUND_PATTERNS.some((pattern) =>
    lowerFinalUrl.includes(pattern),
  );

  if (!statusAllowed) {
    return {
      ok: false,
      reason: `HTTP ${response.status}`,
      finalUrl: response.url,
    };
  }

  if (genericNotFound) {
    return {
      ok: false,
      reason: "redirecionou para pagina generica de nao encontrado",
      finalUrl: response.url,
    };
  }

  return {
    ok: true,
    restricted,
    status: response.status,
    finalUrl: response.url,
  };
}

export async function auditUrl(url, request = fetchWithTimeout) {
  const trimmed = url?.trim();
  if (!trimmed) {
    return { ok: false, reason: "URL vazia", url: trimmed || "" };
  }

  try {
    const result = await auditHttpUrl(trimmed, request);
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
  const [sourcePath, ...extraArgs] = process.argv.slice(2);
  if (!sourcePath || extraArgs.length) {
    throw new Error(
      "Uso: node scripts/audit-links.mjs data/AAAA-MM-DD.json",
    );
  }

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
    const marker = result.ok
      ? result.restricted
        ? "RESTRITO"
        : "OK"
      : "ERRO";
    console.log(`${marker} [${result.category}] ${result.title}`);
    if (!result.ok) {
      failureCount++;
      console.log(`  ${result.reason}: ${result.url}`);
    }
  }

  console.log(`\n${sourcePath}: ${results.length} link(s), ${failureCount} erro(s)`);
  if (failureCount) process.exitCode = 1;
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  await main();
}
