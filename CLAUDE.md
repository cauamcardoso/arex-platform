# AIREX - AI Readiness Explorer

## What This Is
AIREX is an open-source Flask web platform that helps academic institutions assess, compare, and improve their AI readiness. Built by UTEP AAII, launched with a CAHSI-HACU consortium of 542 Hispanic-Serving Institutions as Phase I pilot.

**Live**: Deployed on Render (auto-deploys from `main` branch)
**Repo**: https://github.com/cauamcardoso/arex-platform

## Project Rules (Non-Negotiable)
- **No em dashes** anywhere in the codebase
- **No absolutes or superlatives** (avoid "best", "only", "revolutionary", etc.)
- Badge links: AAII links to https://www.utep.edu/aaii/, CAHSI links to https://cahsi.utep.edu/
- Name: AIREX (AI Readiness Explorer) - formerly "AI Readiness Atlas" then "AREX"

## Stack
- **Backend**: Flask + Gunicorn, Python
- **Frontend**: Single-file HTML templates with embedded CSS + JS (no frameworks)
- **Data**: JSON files (no database)
- **Deployment**: Render (render.yaml), auto-deploy on push to main

## File Structure
```
src/app.py              # Flask app, all routes
templates/
  home.html             # Landing page (hero, journey section, consortium, CTA)
  readiness.html        # AI Readiness concept page (pillars, levels, methodology)
  atlas.html            # Interactive map of institutions
  assessment.html       # 25-question self-assessment tool
  institution.html      # Individual institution profile page
  toolkit.html          # Resource repository with AI chatbot search
  news.html             # Curated AI-in-education news feed
data/
  institutions.json     # 542 institutions dataset
  resources/resources.json  # 18 curated resources
  news/news.json        # 16 curated news articles
```

## Key Domain Concepts

### Five Pillars of AI Readiness
1. Teaching and Learning
2. Policy and Governance
3. Ethics and Equity
4. Research and Innovation
5. Infrastructure

### Four Developmental Levels
1. Exploring (1.0-2.0)
2. Building (2.1-3.0)
3. Advancing (3.1-4.0)
4. Leading (4.1-5.0)

### Assessment Scoring
- 25 questions total, 5 per pillar, 1-5 Likert scale
- Pillar average = mean of 5 questions in that pillar
- Overall score = mean of 5 pillar averages
- All scoring is client-side JavaScript (no server-side computation)
- Anonymous, no data stored

## Design System

### Landing Page (home.html)
- Hero: Dark gradient (#0f172a to #1d4ed8) with animated floating orbs, grid shimmer, gradient text
- Stats card: Glassmorphism, consortium context (CAHSI-HACU HSI AI Readiness Consortium)
- Journey section: 6 scroll-animated steps with CSS art illustrations
  - Each illustration has **glassmorphism** (backdrop-filter blur, translucent gradients, glass border, hover lift)
  - IntersectionObserver triggers fade-in animations
  - Alternating left/right layout (odd: visual left, even: reversed)
- Consortium section: Dark background, 3 org cards (CAHSI, HACU, UTEP AAII)
- Vision paragraph about long-term network expansion

### AI Readiness Page (readiness.html)
- **Light theme** with sophisticated accents (NOT dark theme)
- CSS variables: `--bg-primary: #ffffff`, `--bg-secondary: #f8f7ff`, `--bg-tertiary: #f1f0fb`
- Accent colors: `--accent-purple: #8b5cf6`, `--accent-indigo: #6366f1`, `--accent-cyan: #06b6d4`
- Gradient text on section headings: `linear-gradient(135deg, #4f46e5, #7c3aed, #06b6d4)`
- Aurora orbs at low opacity (6-8%) for ambient effect
- Cards use light glassmorphism with indigo-tinted borders
- Hero and CTA sections are dark (kept as accent)
- Sections: Hero, Definition, Who This Is For (3 personas), Five Pillars (5 cards), Four Levels (4 cards + progress bar), How the Score Works (methodology), How to Use Your Results (4 guidance steps), A Note on Our Approach, CTA

### Icons
- All icons are **inline SVG** (Lucide-style, stroke-based, `currentColor`)
- NO emojis or HTML entities anywhere
- Consistent 24x24 viewBox, stroke-width 2, rounded caps/joins
- Icons adapt color from parent text color via `currentColor`

### Common Patterns
- `backdrop-filter: blur()` for glass effects
- `transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1)` for premium-feel transitions
- IntersectionObserver for scroll-triggered animations
- Mobile-first responsive with breakpoints at 768px and 1024px
- Header is fixed, 64px height, glass effect

## Routes
| Route | Template | Description |
|-------|----------|-------------|
| `/` | home.html | Landing page |
| `/readiness` | readiness.html | AI Readiness framework explainer |
| `/atlas` | atlas.html | Interactive institution map |
| `/assessment` | assessment.html | Self-assessment tool |
| `/institution/<id>` | institution.html | Individual institution profile |
| `/repository` | toolkit.html | Resource repository + AI search |
| `/toolkit` | redirect to /repository | Legacy redirect |
| `/news` | news.html | Curated AI education news |

## Recent Changes (Latest First)
1. **Glassmorphism journey illustrations + SVG icons** - All CSS art panels use frosted glass; all emojis replaced with inline SVGs across 6 templates
2. **Light theme readiness page** - Converted from dark SaaS theme back to light with sophisticated accents
3. **AIREX vision text** - Added long-term network expansion vision to consortium section
4. **Dark SaaS theme (reverted)** - OneText-inspired dark theme was applied then reverted to light
5. **Hero stats card redesign** - Phase I Pilot badge, consortium heading, 4-stat grid
6. **Readiness page expansion** - Added Who This Is For, Methodology, Results Guidance, Design Note sections

## Development
```bash
# Run locally
cd src && python3 app.py
# or
flask run

# Deploy
git push origin main  # Auto-deploys to Render
```

## What Needs Work Next
- Content refinement and copy review across all pages
- Real assessment data integration (currently sample data)
- Resource repository expansion (currently 18 resources)
- News feed automation (currently 16 manually curated articles)
- Mobile testing and polish
- Accessibility audit
