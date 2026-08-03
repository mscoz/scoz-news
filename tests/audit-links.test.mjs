import assert from "node:assert/strict";
import { mkdtemp, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  auditUrl,
  loadAuditItems,
} from "../scripts/audit-links.mjs";

async function editionFile() {
  const directory = await mkdtemp(path.join(os.tmpdir(), "scoz-news-audit-"));
  const file = path.join(directory, "2026-07-27.json");
  await writeFile(
    file,
    JSON.stringify({
      items: {
        meta: [{ title: "Meta", url: "https://example.com/meta" }],
        google: [{ title: "Google", url: "https://example.com/google" }],
        ppc: [],
        mkt: [],
        ia: [],
      },
    }),
  );
  return file;
}

test("loads links and categories from one weekly JSON edition", async () => {
  const file = await editionFile();

  const { items } = await loadAuditItems(file);

  assert.deepEqual(items, [
    { category: "meta", title: "Meta", url: "https://example.com/meta" },
    { category: "google", title: "Google", url: "https://example.com/google" },
  ]);
});

test("rejects HTML because the weekly audit runs before the build", async () => {
  await assert.rejects(
    loadAuditItems("index.html"),
    /informe um arquivo semanal JSON/i,
  );
});

test("records anti-bot responses as restricted rather than broken", async () => {
  const request = async () => ({
    ok: false,
    status: 403,
    url: "https://example.com/restricted",
    body: { cancel: async () => {} },
  });

  const result = await auditUrl("https://example.com/restricted", request);

  assert.equal(result.ok, true);
  assert.equal(result.restricted, true);
});

test("records a Reddit anti-bot response as restricted", async () => {
  const request = async () => ({
    ok: false,
    status: 429,
    url: "https://www.reddit.com/oembed",
  });

  const result = await auditUrl(
    "https://www.reddit.com/r/ads/comments/example/story",
    request,
  );

  assert.equal(result.ok, true);
  assert.equal(result.restricted, true);
});

test("checks a successful Reddit link without reading its body", async () => {
  const request = async () => ({
    ok: true,
    status: 200,
    url: "https://www.reddit.com/r/ads/comments/example/story",
    body: { cancel: async () => {} },
  });

  const result = await auditUrl(
    "https://www.reddit.com/r/ads/comments/example/story",
    request,
  );

  assert.equal(result.ok, true);
  assert.equal(result.status, 200);
});

test("rejects a genuinely broken link", async () => {
  const request = async () => ({
    ok: false,
    status: 404,
    url: "https://example.com/missing",
    body: { cancel: async () => {} },
  });

  const result = await auditUrl("https://example.com/missing", request);

  assert.equal(result.ok, false);
  assert.match(result.reason, /HTTP 404/);
});
