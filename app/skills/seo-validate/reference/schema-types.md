# Schema.org JSON-LD Templates

Reference for `seo-validate` Category 3 (Structured Data). Required properties for the rich-result-eligible types, with JSON-LD templates.

Source: Schema.org vocabulary + Google Search Central rich-results requirements.

## Base Format

All JSON-LD is embedded in `<script type="application/ld+json">` blocks, usually in `<head>` or the top of `<body>`:

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "...",
  ...
}
</script>
```

**Universal required properties** (checked by Category 3):
- `@context` — always `https://schema.org`.
- `@type` — valid Schema.org type name.

Multiple types on one page: use an array:

```html
<script type="application/ld+json">
[
  { "@context": "https://schema.org", "@type": "Organization", ... },
  { "@context": "https://schema.org", "@type": "WebSite", ... }
]
</script>
```

---

## Article

For blog posts, news, editorial content.

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "Article headline (max 110 chars for Google rich results)",
  "image": [
    "https://example.com/16x9.jpg",
    "https://example.com/4x3.jpg",
    "https://example.com/1x1.jpg"
  ],
  "datePublished": "2026-04-09T08:00:00+00:00",
  "dateModified": "2026-04-10T12:00:00+00:00",
  "author": [{
    "@type": "Person",
    "name": "Jane Doe",
    "url": "https://example.com/authors/jane-doe"
  }],
  "publisher": {
    "@type": "Organization",
    "name": "ExampleCo",
    "logo": {
      "@type": "ImageObject",
      "url": "https://example.com/logo.png"
    }
  },
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": "https://example.com/blog/article-slug"
  },
  "description": "Short description of the article"
}
```

**Required** (Category 3 flags absence): `headline`, `author`, `datePublished`, `image`.
**Strongly recommended**: `dateModified`, `publisher`, `mainEntityOfPage`.

Subtypes: `NewsArticle`, `BlogPosting`, `TechArticle`, `OpinionNewsArticle`.

---

## FAQPage

Triggers rich FAQ results in SERP.

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is X?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "X is ..."
      }
    },
    {
      "@type": "Question",
      "name": "How much does X cost?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "X costs $..."
      }
    }
  ]
}
```

**Required**: `mainEntity` array with ≥2 `Question` items, each with `name` + `acceptedAnswer.text`.

Google restriction: FAQ rich results only shown for authoritative government/health sites as of August 2023 — but the markup still helps LLM extraction (GEO).

---

## HowTo

For step-by-step instructional content.

```json
{
  "@context": "https://schema.org",
  "@type": "HowTo",
  "name": "How to reset your password",
  "description": "Steps to reset your account password",
  "totalTime": "PT5M",
  "supply": [
    { "@type": "HowToSupply", "name": "Email access" }
  ],
  "tool": [
    { "@type": "HowToTool", "name": "Web browser" }
  ],
  "step": [
    {
      "@type": "HowToStep",
      "name": "Go to the login page",
      "text": "Navigate to https://example.com/login",
      "url": "https://example.com/login"
    },
    {
      "@type": "HowToStep",
      "name": "Click 'Forgot password'",
      "text": "On the login page, click the 'Forgot password' link."
    }
  ]
}
```

**Required**: `name`, `step` array with ≥2 `HowToStep` items.

---

## BreadcrumbList

Breadcrumb trails in SERP.

```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {
      "@type": "ListItem",
      "position": 1,
      "name": "Home",
      "item": "https://example.com/"
    },
    {
      "@type": "ListItem",
      "position": 2,
      "name": "Blog",
      "item": "https://example.com/blog"
    },
    {
      "@type": "ListItem",
      "position": 3,
      "name": "Article Title"
    }
  ]
}
```

**Required**: `itemListElement` array with `position`, `name`, and `item` (except last). Last item omits `item` since it's the current page.

---

## Organization

Defines your company/brand for Knowledge Graph.

```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "ExampleCo",
  "url": "https://example.com",
  "logo": "https://example.com/logo.png",
  "sameAs": [
    "https://twitter.com/exampleco",
    "https://www.linkedin.com/company/exampleco",
    "https://github.com/exampleco"
  ],
  "contactPoint": [{
    "@type": "ContactPoint",
    "telephone": "+1-555-123-4567",
    "contactType": "customer service",
    "areaServed": "US",
    "availableLanguage": ["en", "es"]
  }]
}
```

**Required**: `name`, `url`, `logo`.

Subtypes for specific kinds: `Corporation`, `NGO`, `EducationalOrganization`, `LocalBusiness` (see below).

Typically placed once on the site, in a shared layout. `WebSite` schema can reference it via `publisher`.

---

## Product

For e-commerce product pages.

```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Product name",
  "image": [
    "https://example.com/product-1x1.jpg",
    "https://example.com/product-4x3.jpg",
    "https://example.com/product-16x9.jpg"
  ],
  "description": "Product description",
  "brand": {
    "@type": "Brand",
    "name": "Brand Name"
  },
  "sku": "SKU-12345",
  "mpn": "MPN-12345",
  "gtin13": "0123456789012",
  "offers": {
    "@type": "Offer",
    "url": "https://example.com/products/sku-12345",
    "priceCurrency": "USD",
    "price": "49.99",
    "priceValidUntil": "2027-01-01",
    "availability": "https://schema.org/InStock",
    "itemCondition": "https://schema.org/NewCondition"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.6",
    "reviewCount": "142"
  },
  "review": [{
    "@type": "Review",
    "author": { "@type": "Person", "name": "Jane" },
    "reviewRating": { "@type": "Rating", "ratingValue": "5" },
    "reviewBody": "Great product."
  }]
}
```

**Required**: `name`, `image`, `offers` (with `price` + `priceCurrency` + `availability`).
**Strongly recommended for rich results**: `aggregateRating`, `review`, `brand`.

---

## LocalBusiness

For brick-and-mortar businesses (local SEO).

```json
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "@id": "https://example.com/#local-business",
  "name": "ExampleCo Store",
  "image": "https://example.com/store.jpg",
  "url": "https://example.com",
  "telephone": "+1-555-123-4567",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "123 Main St",
    "addressLocality": "San Francisco",
    "addressRegion": "CA",
    "postalCode": "94110",
    "addressCountry": "US"
  },
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": 37.7749,
    "longitude": -122.4194
  },
  "openingHoursSpecification": [
    {
      "@type": "OpeningHoursSpecification",
      "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      "opens": "09:00",
      "closes": "18:00"
    },
    {
      "@type": "OpeningHoursSpecification",
      "dayOfWeek": "Saturday",
      "opens": "10:00",
      "closes": "16:00"
    }
  ],
  "priceRange": "$$"
}
```

**Required**: `name`, `address`, `telephone`.
**Strongly recommended**: `openingHoursSpecification`, `geo`, `url`, `image`.

Use more specific subtypes when applicable: `Restaurant`, `Hotel`, `MedicalClinic`, `Store`, `AutoDealer`, etc.

---

## WebSite (with SearchAction)

Enables sitelinks search box in SERP.

```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "ExampleCo",
  "url": "https://example.com",
  "potentialAction": {
    "@type": "SearchAction",
    "target": {
      "@type": "EntryPoint",
      "urlTemplate": "https://example.com/search?q={search_term_string}"
    },
    "query-input": "required name=search_term_string"
  }
}
```

---

## Event

For conferences, concerts, webinars.

```json
{
  "@context": "https://schema.org",
  "@type": "Event",
  "name": "Event name",
  "startDate": "2026-06-15T09:00:00-07:00",
  "endDate": "2026-06-15T17:00:00-07:00",
  "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
  "eventStatus": "https://schema.org/EventScheduled",
  "location": {
    "@type": "Place",
    "name": "Venue Name",
    "address": { "@type": "PostalAddress", ... }
  },
  "image": ["https://example.com/event.jpg"],
  "description": "...",
  "offers": {
    "@type": "Offer",
    "url": "https://example.com/event",
    "price": "99.00",
    "priceCurrency": "USD",
    "availability": "https://schema.org/InStock",
    "validFrom": "2026-01-01T00:00:00-08:00"
  },
  "organizer": {
    "@type": "Organization",
    "name": "ExampleCo",
    "url": "https://example.com"
  }
}
```

**Required**: `name`, `startDate`, `location` (or `eventAttendanceMode: OnlineEventAttendanceMode`).

---

## Recipe

For food recipes.

```json
{
  "@context": "https://schema.org",
  "@type": "Recipe",
  "name": "Recipe name",
  "image": ["..."],
  "author": { "@type": "Person", "name": "Jane Doe" },
  "datePublished": "2026-04-09",
  "description": "...",
  "prepTime": "PT15M",
  "cookTime": "PT1H",
  "totalTime": "PT1H15M",
  "recipeYield": "8 servings",
  "recipeIngredient": ["2 cups flour", "1 tsp salt"],
  "recipeInstructions": [
    { "@type": "HowToStep", "text": "..." }
  ],
  "nutrition": {
    "@type": "NutritionInformation",
    "calories": "250 calories"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.8",
    "reviewCount": "42"
  }
}
```

---

## VideoObject

For video content.

```json
{
  "@context": "https://schema.org",
  "@type": "VideoObject",
  "name": "Video title",
  "description": "...",
  "thumbnailUrl": ["https://example.com/thumb-16x9.jpg"],
  "uploadDate": "2026-04-09T08:00:00+00:00",
  "duration": "PT5M30S",
  "contentUrl": "https://example.com/video.mp4",
  "embedUrl": "https://example.com/embed/video"
}
```

---

## Common Mistakes (flagged by Category 3)

1. **Missing `@context`** or wrong value (e.g., `http://` instead of `https://`).
2. **Wrong `@type`** (e.g., `article` lowercase — must be `Article`).
3. **Dates not in ISO 8601** (`2026-04-09` good; `April 9, 2026` bad).
4. **Relative URLs** for `image`, `logo`, `url` — must be absolute.
5. **Missing required properties** per type (see each section above).
6. **Markup doesn't match visible content** — violates Google guidelines.
7. **Duplicate JSON-LD blocks** with conflicting data — consolidate into one.
8. **Fake reviews / made-up aggregate ratings** — violates Google guidelines.

---

## Testing

- Google Rich Results Test: https://search.google.com/test/rich-results
- Schema.org validator: https://validator.schema.org/

---

## References

- Schema.org: https://schema.org/
- Google rich results: https://developers.google.com/search/docs/appearance/structured-data
- JSON-LD 1.1: https://www.w3.org/TR/json-ld11/
