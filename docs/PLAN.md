# API Test Machine - Development Plan

## Current Status

**Version:** 0.2.0

### Completed Features

- [x] Core async test engine with httpx
- [x] Rate limiting (token bucket algorithm)
- [x] Template variable substitution
- [x] Pass/fail thresholds
- [x] FastAPI Control API
- [x] Typer CLI
- [x] SvelteKit Web Dashboard
- [x] MCP Server for LLM agents
- [x] Agent scheduler
- [x] Authentication support (Bearer, API Key, Basic)
- [x] **Multi-endpoint testing**
  - Round-robin, weighted, and sequential distribution
  - Per-endpoint metrics
  - UI support in webapp
- [x] **SQLite persistent storage**
  - SQLAlchemy 2.0 async models
  - Alembic migrations
  - JSON fallback for development
- [x] **Storage status dashboard**
  - Database metrics and health monitoring
  - Runs by status/day charts
  - Top tests leaderboard

### In Progress

- [ ] WebSocket real-time updates
- [ ] Per-endpoint metrics in results display

## Roadmap

### Phase 1: Core Stability (Current) - COMPLETE

Focus on reliability and usability of existing features.

**Completed:**
- [x] Add database persistence (SQLite)
- [x] Storage status monitoring
- [x] JSON to SQLite migration support

**Remaining:**
- [ ] Improve error handling and reporting
- [ ] Add request/response assertion capabilities
- [ ] Expand test coverage to 90%+

### Phase 2: Enhanced Testing

Advanced testing capabilities.

**Tasks:**
- [ ] Custom scripting support (pre/post request hooks)
- [ ] Response validation (JSON schema, regex)
- [ ] Data-driven testing (CSV/JSON data sources)
- [ ] Scenario-based testing (chained requests)
- [ ] gRPC support

### Phase 3: Scale & Distribution

Distributed testing for higher loads.

**Tasks:**
- [ ] Worker pool architecture
- [ ] Distributed execution across nodes
- [ ] Results aggregation from multiple workers
- [ ] Cloud deployment templates (AWS, GCP, Azure)

### Phase 4: Observability

Better insights and integration.

**Tasks:**
- [ ] Prometheus metrics export
- [ ] OpenTelemetry tracing
- [ ] Grafana dashboard templates
- [ ] Slack/PagerDuty alerting
- [ ] CI/CD integration (GitHub Actions, GitLab CI)

### Phase 5: Enterprise Features

Production-ready capabilities.

**Tasks:**
- [ ] User authentication and authorization
- [ ] Team workspaces
- [ ] Test history and trending
- [ ] Scheduled test reports (email, Slack)
- [ ] API versioning

## Technical Debt

- [ ] Fix datetime deprecation warnings (use timezone-aware)
- [ ] Resolve TypeScript errors in webapp charts
- [ ] Add proper form label associations (a11y)
- [ ] Improve error messages for invalid specs

## Design Decisions Log

### 2025-01-26: SQLite Persistent Storage

**Decision:** Implement SQLite as default storage with JSON fallback.

**Implementation:**
- SQLAlchemy 2.0 async with aiosqlite
- StorageInterface protocol for pluggable backends
- Alembic for schema migrations
- Storage status dashboard for monitoring

**Rationale:**
- SQLite is zero-config and portable
- Async support maintains performance
- Protocol pattern allows future PostgreSQL support

### 2025-01-25: Multi-Endpoint Feature

**Decision:** Add optional `endpoints` array to TestSpec rather than creating a separate MultiEndpointTestSpec.

**Rationale:**
- Maintains backward compatibility
- Single code path with conditional handling
- Simpler API surface

**Trade-offs:**
- TestSpec model is more complex
- Validation logic needs to handle both modes

### Previous Decisions

**Async-first architecture:** All I/O uses async/await for scalability.

**Pydantic v2:** Chosen for performance and better validation.

## Contributing

See the main README for development setup. Key areas needing contribution:

1. **Testing:** More integration tests, especially for multi-endpoint scenarios
2. **Documentation:** API documentation, more examples
3. **Performance:** Profiling and optimization
4. **Features:** Pick items from the roadmap above

## Changelog

### v0.2.0 (2025-01-26)
- Added SQLite persistent storage with Alembic migrations
- Added storage status dashboard with charts
- Added JSON to SQLite migration support
- Added `/api/v1/storage/status` endpoint

### v0.1.0 (2025-01-25)
- Added multi-endpoint testing feature
- Added distribution strategies (round-robin, weighted, sequential)
- Added per-endpoint metrics collection
- Added webapp support for multi-endpoint tests
