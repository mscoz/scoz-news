#!/usr/bin/env node

import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const DATA_DIR = "data";
const REQUEST_TIMEOUT_MS = 12_000;
const ALLOWED_RESTRICTED_STATUSES = new Set([401, 403, 429]);
const GENERIC_NOT_FOUND_PATTERNS = [
  "article_not_found",
  "/404",
  "page-not-found",
  "page_not_found",
];

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

function parseRedditPath(url) {
  const match = url.match(/reddit\.com\/r\/([^/]+)\/comments\/([^/]+)/i);
  if (!match) return null;
  return { subreddit: match[1].toLowerCase(), postId: match[2].toLowerCase() };
}

async function fetchWithTimeout(url) {
  return fetch(url, {
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
  const response = await fetchWithTimeout(url);
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

async function auditItem(item, category) {
  const url = item.url?.trim();
  if (!url) {
    return { ok: false, category, title: item.title, url: "", reason: "URL vazia" };
  }

  try {
    const result = url.includes("reddit.com/")
      ? await auditRedditUrl(url)
      : await auditHttpUrl(url);
    return { category, title: item.title, url, ...result };
  } catch (error) {
    return {
      ok: false,
      category,
      title: item.title,
      url,
      reason: `${error.name}: ${error.message}`,
    };
  }
}

async function main() {
  const weekFile = process.argv[2] || (await latestWeekFile());
  const data = JSON.parse(await readFile(weekFile, "utf8"));
  const items = Object.entries(data.items).flatMap(([category, categoryItems]) =>
    categoryItems.map((item) => ({ item, category })),
  );

  const results = [];
  for (const { item, category } of items) {
    const result = await auditItem(item, category);
    results.push(result);
    const marker = result.ok ? "OK" : "ERRO";
    console.log(`${marker} [${category}] ${item.title}`);
    if (!result.ok) console.log(`  ${result.reason}: ${result.url}`);
  }

  const failures = results.filter((result) => !result.ok);
  console.log(`\n${weekFile}: ${results.length} link(s), ${failures.length} erro(s)`);
  if (failures.length) process.exitCode = 1;
}

await main();
