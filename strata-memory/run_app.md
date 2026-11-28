cd /Users/dheeban/Documents/my_projects/ai-engineering-lab/strata-memory
source .venv/bin/activate
strata-api



---

### Option 1: Using the `--port` (or `-p`) CLI Flag *(Recommended)*

#### For the REST API (`strata-api`):
```bash
strata-api --port 9000
# or short form:
strata-api -p 9000
```
*(You can also specify the host with `-H` or `--host`, e.g. `strata-api -H 127.0.0.1 -p 9000`)*

#### For the MCP Server in SSE Mode (`strata-mcp`):
```bash
strata-mcp --transport sse --port 8500
```

---

### Option 2: Using Environment Variables in Terminal

Prefix the command with `STRATA_API_PORT`:

```bash
STRATA_API_PORT=9000 strata-api
```

---

### Option 3: Setting it in `.env` File

Add or edit the port in your `strata-memory/.env` file:

```ini
STRATA_API_PORT=9000
STRATA_API_HOST=0.0.0.0
```

Then simply launch:
```bash
strata-api
```
The server will automatically start on `http://0.0.0.0:9000`.