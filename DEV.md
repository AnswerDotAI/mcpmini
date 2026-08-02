# Developer guide

The implementation, its examples, and its tests are one story in `nbs/00_core.ipynb`; read it top to bottom. This file holds the context around it: which protocol era is implemented and why, what is deliberately absent, and where the design came from.

## Protocol era

The server and client speak the 2025-11-25-era protocol (`initialize` handshake, `tools/*`, `ping`), which is what shipping clients negotiate: Claude Code 2.1.220 proposes `protocolVersion: "2025-11-25"` in a classic handshake (verified by wiretap 2026-08-02; no `server/discover`, no `_meta` protocol fields). The 2026-07-28 stateless revision is the design target though: dispatch is already a pure message-to-reply function with no per-connection state, no sessions are minted, and the transports own all remaining ceremony — so adopting the new era when clients arrive should be additive (per-request `_meta`, `server/discover`) rather than a redesign. `PROTO_VERSIONS` is the supported list, newest first.

## The 2026-07-28 upgrade, concretely

What adopting the stateless era means for this codebase, from the 2026-07-28 changelog and transport spec (read 2026-08-02; the SEP numbers are the spec's own references). Nothing here should start until a client we care about negotiates the new era — the wiretap methodology above answers that in minutes.

Server (mostly SEP-2575):

- Implement `server/discover` (MUST): supported versions, capabilities, identity. It doubles as the old-vs-new probe on stdio, so it's also the interop hinge: a modern client MAY call it before anything else.
- Handle handshake-less requests: read `io.modelcontextprotocol/protocolVersion`, `clientCapabilities`, and `clientInfo` from each request's `_meta`; put `serverInfo` in each result's `_meta`; return `UnsupportedProtocolVersionError` (`-32022`) on mismatch. Keep answering `initialize` for old-era clients — dual-era is a dispatch branch, not a fork.
- Add the required `resultType: "complete"` field to every result (old clients ignore it; new clients require it).
- Streamable HTTP hardening: require and validate `MCP-Protocol-Version` (against body `_meta`; `HeaderMismatch` `-32020` on conflict), `Mcp-Method`, and `Mcp-Name` headers; unknown method becomes HTTP 404 + `-32601` (the body distinguishes us from a legacy server's 404). Our existing behaviors — no sessions, 405 on GET/DELETE, ignore `Mcp-Session-Id` and `Last-Event-ID` — are exactly what the new spec prescribes; nothing to remove.
- `tools/list` (and friends) must return the `CacheableResult` fields `ttlMs` and `cacheScope`, and SHOULD list tools in deterministic order (ours already is: registration order).
- `ping` and `logging/setLevel` are gone in the new era; keep them for old clients, don't advertise them.
- Once the server streams (kernel work): closing a request's SSE response stream IS that request's cancellation, and there is no resumability — a broken stream means the client re-issues with a fresh id.

Client:

- Modern-first with fallback: attempt a new-era request; on HTTP 400, inspect the body — a recognized modern JSON-RPC error means "modern server, fix the request", anything else means fall back to `initialize` (the spec's own compatibility recipe).
- Stamp every request's `_meta` (protocolVersion, clientInfo, clientCapabilities) and the three HTTP headers; treat a missing `resultType` from an old server as `"complete"`.
- The one genuinely new obligation: `x-mcp-header` support is a client MUST — mirror annotated tool params into `Mcp-Param-{name}` headers (base64 sentinel encoding for non-ASCII values), and reject tool definitions whose annotations are invalid.

Upgrade paths that stay optional extensions/patterns, relevant to the kernel-server consumer:

- MRTR (SEP-2322): server-initiated interaction becomes `resultType: "input_required"` + client retry with `inputResponses` — the natural carrier for a kernel's `input()`.
- Tasks (`io.modelcontextprotocol/tasks`, SEP-2663): durable task handles polled via `tasks/get`, mid-flight input via `tasks/update` — the carrier for long-running cells that outlive connections. Opt-in per request from both sides, so blocking execute remains the compatible default.
- `subscriptions/listen` replaces the old GET stream for change notifications; we emit none today, so nothing is lost by ignoring it until there's something to notify.
## Deliberately absent

- **Session minting** (`Mcp-Session-Id`): legal to omit in the old era, removed in 2026-07-28. The client echoes ids from servers that mint (the FastMCP interop test covers this).
- **SSE response streaming, server side**: a server may answer any POST with plain JSON, and this one always does. Streaming earns its place when there are progress notifications to carry — which arrives with long-running tool work (the jupygate-backed kernel server), not before. The client parses SSE bodies, since other servers send them.
- **OAuth**: auth is a static bearer token in raw ASGI middleware (`auth_app`, constant-time compare). The SDK's `token_verifier`/`AuthSettings` model an OAuth resource server, which is ceremony for a personal token. This design (and the token flag conventions) comes from clikernel PR #25.
- **Sampling, roots, logging**: deprecated in 2026-07-28; new implementations shouldn't add them.
- **Legacy HTTP+SSE transport** (2024-11-05): deprecated since 2025-03-26; nothing we talk to speaks it.

## Auth policy

Capability and policy are separated: `create_app` takes whatever token it's given (including none), while `serve_mcp` — the deployment entry point — refuses a non-loopback bind without a token unless `no_token=True` says auth lives elsewhere (VPN, fronting proxy). Jupyter's tokenless-by-default years are the cautionary tale for the default; the flag is the trust-the-user escape.

## Tests

The notebook is the test suite (`nbdev-test`, safe: servers bind loopback ephemeral ports only, and everything token-spending is `#| eval: false`). Interop runs against the official SDK in both directions — its client against our server, our client against FastMCP — because self-consistency proves nothing about the wire. The live sections drive Claude Code's real client headless via the Agent SDK (stdio via the installed `mcpmini` script, HTTP with a bearer header); rerun them manually when the protocol or Claude Code moves. The `mcp` dev dep exists for the interop cells.

## Consumers

Built as the MCP layer under the planned jupygate-backed clikernel rework (kernel handles as tool arguments, per the 2026 handle model), and for solveit-side mounting: `create_app` returns a plain ASGI app precisely so a fasthtml/starlette host can mount it beside other routes with auth shared at the host layer.
