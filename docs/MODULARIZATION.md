# Modularization Analysis: API Test Machine

## Current Architecture

The project consists of 6 main components:

| Component | Purpose | Independence |
|-----------|---------|--------------|
| `engine/` | Core async load test execution | Fully independent |
| `api/` | FastAPI REST server | Depends on engine, agent |
| `agent/` | Scheduler & orchestration | Depends on engine models |
| `cli/` | Command-line interface | HTTP client only |
| `mcp_server/` | LLM agent integration | HTTP client only |
| `webapp/` | SvelteKit dashboard | HTTP client only |

**Current Deployment**: Single uvicorn process with embedded scheduler.

---

## Modularization Options

### Option A: Keep Monolithic (Status Quo)
Single codebase, single deployment.

### Option B: Extract Engine as Library
Publish `engine/` as separate PyPI package.

### Option C: Separate API and Agent Servers
Run API and scheduler as independent processes.

### Option D: Full Microservices
Engine, API, Scheduler, Storage as separate services.

---

## Pros and Cons

### Option A: Monolithic

| Pros | Cons |
|------|------|
| Simple deployment (single process) | Scheduler blocks on API |
| No network latency between components | Can't scale components independently |
| Easier debugging (single codebase) | Single point of failure |
| Shared memory (no serialization) | Harder to deploy different versions |
| Lower operational complexity | Testing requires full stack |

**Best for**: Small-medium deployments, development, single-tenant use.

---

### Option B: Engine as Library

| Pros | Cons |
|------|------|
| Reusable in other projects | Version coordination needed |
| Cleaner dependency graph | Two repos to maintain |
| Can version independently | Release process more complex |
| Minimal risk (already decoupled) | Import path changes required |
| Enables alternative front-ends | PyPI publishing overhead |

**Effort**: Low (2-4 hours)
**Best for**: When you want to reuse engine elsewhere.

---

### Option C: Separate API and Agent

| Pros | Cons |
|------|------|
| Independent scaling | Network latency overhead |
| Scheduler failure doesn't affect API | Need process manager (systemd, Docker) |
| Can restart scheduler without API downtime | Configuration sync complexity |
| Better fault isolation | Debugging across processes harder |
| Can run multiple scheduler instances | Need health checks / monitoring |

**Effort**: Medium (4-8 hours)
**Best for**: Production deployments needing reliability.

---

### Option D: Full Microservices

| Pros | Cons |
|------|------|
| Maximum scalability | Distributed system complexity |
| Technology flexibility per service | Need service discovery |
| Independent deployment cycles | Higher operational overhead |
| Team can own separate services | Eventual consistency issues |
| Horizontal scaling per component | Need message queue or event bus |
| Polyglot possible (Go engine?) | 3-5x more infrastructure |

**Effort**: High (weeks of work)
**Best for**: Large scale, multi-team, high-traffic.

---

## Component Coupling Analysis

```
cli ──────┐
mcp_server├──> [HTTP] ──> api ──> engine
webapp ───┘                 └──> agent ──> [HTTP back to api]
```

**Tight Coupling Points**:
1. `api.routes` imports `engine.executor` directly
2. `api.database` maps `engine.models` to SQL
3. `api.app` lifespan creates `agent.orchestrator`
4. `agent` models import `engine.TestSpec`

**Loose Coupling Points**:
1. `cli`, `mcp_server`, `webapp` are pure HTTP clients
2. Storage interface allows swappable backends
3. Agent communicates via HTTP (already decoupled)

---

## Separation Effort Estimates

| Separation | Effort | Risk | Benefit |
|------------|--------|------|---------|
| Extract engine as library | 2-4 hrs | Low | High reuse |
| CLI as separate package | 1-2 hrs | Very Low | Distribution |
| MCP server as separate package | 1-2 hrs | Very Low | Distribution |
| Agent as standalone service | 4-8 hrs | Medium | Scalability |
| Full microservices | Weeks | High | Max scale |

---

## Recommendations

### For Current Use Case
**Stay monolithic** (Option A). The complexity of distributed systems isn't justified for a load testing tool that typically runs on a single machine.

### If Reuse is a Priority
**Extract engine as library** (Option B). The engine is already well-isolated and could be published to PyPI with minimal effort.

### If Scaling is Needed
**Separate API and Agent** (Option C). This provides meaningful isolation without full microservices complexity.

### Avoid Unless Necessary
**Full microservices** (Option D). The operational overhead isn't justified unless you have:
- Multiple teams working on the project
- Need for independent deployment of components
- Traffic levels requiring horizontal scaling

---

## Decision Factors

Consider modularization if:
- [ ] Multiple teams will work on different components
- [ ] Components need different scaling profiles
- [ ] You want to reuse engine in other projects
- [ ] You need fault isolation (scheduler crash shouldn't affect API)
- [ ] You want to deploy updates to one component without touching others

Keep monolithic if:
- [x] Single developer or small team
- [x] Single deployment target
- [x] Simplicity is more valuable than scalability
- [x] No need to reuse components elsewhere

---

## Document History

This is a discussion document for informing architecture decisions. No implementation is planned without explicit decision to proceed.
