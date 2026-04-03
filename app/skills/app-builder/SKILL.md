---
name: app-builder
description: "Loaded when user asks to scaffold or build a full-stack app"
effort: medium
user-invocable: false
allowed-tools: Read
---

# App Builder Skill

## Project Type Detection

| Keywords | Project Type | Primary Agents |
|----------|--------------|----------------|
| landing, website, marketing | Static Site | frontend-specialist |
| dashboard, admin, crud | Web App | frontend + backend |
| api, rest, graphql | API Only | backend-specialist |
| mobile, ios, android | Mobile App | mobile-developer |
| cli, command, terminal | CLI Tool | backend-specialist |
| game, unity, godot | Game | game-developer |
| ai, ml, rag | AI/ML | rag-engineer |
| e-commerce, shop, store | E-commerce | backend + frontend |

---

## Tech Stack Selection (2025)

### Web Applications

| Scenario | Stack |
|----------|-------|
| Full-stack, SSR | Next.js 14+ (App Router) |
| SPA with API | React + Vite |
| Vue ecosystem | Nuxt 3 |
| Static/Blog | Astro |
| E-commerce | Next.js + Medusa/Shopify |

### Mobile Applications

| Scenario | Stack |
|----------|-------|
| Cross-platform (JS team) | React Native + Expo |
| Cross-platform (any) | Flutter |
| iOS only | SwiftUI |
| Android only | Kotlin + Jetpack Compose |

### Backend/API

| Scenario | Stack |
|----------|-------|
| Node.js, edge-ready | Hono |
| Node.js, high perf | Fastify |
| Python, async | FastAPI |
| PHP, full-featured | Laravel |
| E-commerce | Magento/Sylius/PrestaShop |

### Database

| Scenario | Stack |
|----------|-------|
| General purpose | PostgreSQL |
| Serverless | Neon (PG), Turso (SQLite) |
| Document store | MongoDB |
| Vector search | PostgreSQL + pgvector |
| Cache | Redis / Upstash |

---

## Project Templates

### Next.js Full-Stack

```
project/
├── src/
│   ├── app/              # App Router
│   │   ├── (auth)/       # Auth group
│   │   ├── api/          # API routes
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/       # Shared components
│   │   └── ui/           # UI primitives
│   ├── lib/              # Utilities
│   └── server/           # Server-only code
├── prisma/               # Database schema
├── public/
├── next.config.ts
├── tailwind.config.ts
└── package.json
```

### FastAPI Backend

```
project/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   ├── core/             # Config, security
│   ├── models/           # Pydantic models
│   ├── db/               # Database
│   └── main.py
├── tests/
├── alembic/              # Migrations
├── pyproject.toml
└── Dockerfile
```

### React Native + Expo

```
project/
├── app/                  # Expo Router
│   ├── (tabs)/
│   ├── _layout.tsx
│   └── index.tsx
├── components/
├── hooks/
├── store/                # State management
├── services/             # API clients
├── app.json
└── package.json
```

---

## Agent Coordination

### New Project Flow

```
1. project-planner     → Task breakdown
2. database-architect  → Schema design
3. backend-specialist  → API implementation
4. frontend-specialist → UI implementation
5. test-engineer       → Test coverage
6. devops-implementer  → Deployment
```

### Feature Addition Flow

```
1. explorer-agent      → Understand codebase
2. project-planner     → Plan changes
3. [appropriate agent] → Implement
4. test-engineer       → Add tests
5. code-reviewer       → Review
```

---

## Common Patterns

### Authentication
- JWT for APIs
- Session for web apps
- OAuth for third-party

### State Management
- Server state: TanStack Query
- Client state: Zustand/Jotai
- Form state: React Hook Form

### Styling
- Tailwind CSS as default
- CSS Modules for isolation
- Styled Components for dynamic

### Testing
- Unit: Jest/Vitest
- E2E: Playwright
- API: Supertest

---

## Best Practices

- ✅ Start with TypeScript
- ✅ Add linting (ESLint/Biome)
- ✅ Use environment variables
- ✅ Set up CI/CD from start
- ✅ Document as you build

- ❌ Don't skip tests
- ❌ Don't hardcode config
- ❌ Don't ignore accessibility
- ❌ Don't over-engineer early
