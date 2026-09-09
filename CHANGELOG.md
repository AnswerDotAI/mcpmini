# Release notes

<!-- do not remove -->

## 0.0.5

### New Features

- HTTPTransport: extract `_request_headers` and make delete return the response, clearing the session id on success or 404 ([#8](https://github.com/AnswerDotAI/mcpmini/issues/8))


## 0.0.4

### New Features

- Add HTTPTransport.delete, ending the server-side MCP session ([#7](https://github.com/AnswerDotAI/mcpmini/pull/7)), thanks to [@jph00](https://github.com/jph00)

### Bugs Squashed

- Update CLI flags for fastcore.script hyphenation ([#5](https://github.com/AnswerDotAI/mcpmini/pull/5)), thanks to [@jph00](https://github.com/jph00)


## 0.0.3

### New Features

- Add server-initiated elicitation over stdio: MCPServer.elicit, request correlation in `serve_stdio`, and `on_request` in StdioTransport ([#4](https://github.com/AnswerDotAI/mcpmini/issues/4))


## 0.0.2

### New Features

- init release
