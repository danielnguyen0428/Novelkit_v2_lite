"""NovelKit web surface — FastAPI HTTP API + React SPA over the tool registry.

This package is the operable Frontend surface for novelkit-hermes. The backend
(``webapp.api``) wraps the registered ``novelkit_*`` tools through the same
hub-and-spoke ``delegate_tool`` seam the CLI uses, so the UI reaches tools
exactly the way the CLI and cron do. The frontend (``webapp/frontend``) is a
React + Vite SPA that talks to that API and is built to static assets the API
can serve as a single deployable unit (or hosted separately behind a CDN to
scale the read path).
"""
