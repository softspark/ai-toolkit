---
name: ecommerce-patterns
description: "E-commerce domain patterns: cart, checkout flow, payment providers (Stripe/Adyen), order state machine, inventory, promotions, tax, B2B vs B2C. Triggers: cart, checkout, product, SKU, inventory, payment, Stripe, Shopify, Medusa, Magento, order status, promotion, tax calculation, coupon, refund. Load when working on any e-commerce feature."
effort: medium
user-invocable: false
allowed-tools: Read
---

# E-commerce Patterns Skill

## Platform Selection

| Scenario | Platform |
|----------|----------|
| Enterprise B2B | OroCommerce |
| Enterprise B2C | Magento 2 |
| Mid-market | Shopify Plus |
| Small business | WooCommerce, PrestaShop |
| Custom/Headless | Medusa, Saleor |

---

## Magento 2 Patterns

### Module Structure
```
app/code/Vendor/Module/
├── Api/
│   └── Data/
│       └── EntityInterface.php
├── Block/
├── Controller/
│   └── Index/
│       └── Index.php
├── etc/
│   ├── module.xml
│   ├── di.xml
│   ├── routes.xml
│   └── frontend/
├── Model/
│   └── ResourceModel/
├── Setup/
├── view/
│   └── frontend/
│       ├── layout/
│       └── templates/
├── registration.php
└── composer.json
```

### Dependency Injection
```xml
<!-- etc/di.xml -->
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="urn:magento:framework:ObjectManager/etc/config.xsd">
    <preference for="Vendor\Module\Api\ServiceInterface" type="Vendor\Module\Model\Service"/>
    <type name="Vendor\Module\Model\Service">
        <arguments>
            <argument name="logger" xsi:type="object">Psr\Log\LoggerInterface</argument>
        </arguments>
    </type>
</config>
```

### GraphQL
```graphql
type Query {
    customProducts(
        search: String
        pageSize: Int = 20
        currentPage: Int = 1
    ): CustomProductOutput @resolver(class: "Vendor\\Module\\Model\\Resolver\\Products")
}
```

---

## Cart & Checkout Patterns

### Cart State Machine
```
Empty → Has Items → Checkout Started → Payment → Order Placed
                  ↑                    ↓
                  └──── Abandoned ←────┘
```

### Checkout Flow
```
1. Cart Review
2. Shipping Address
3. Shipping Method
4. Payment Method
5. Order Review
6. Place Order
7. Confirmation
```

### Price Calculation
```
Base Price
- Catalog Discounts
= Adjusted Price
× Quantity
= Line Total
+ Tax (if exclusive)
= Line Total with Tax
Σ All Lines
= Subtotal
+ Shipping
- Cart Discounts
= Grand Total
```

---

## Inventory Patterns

### Stock Management
```python
class InventoryService:
    def reserve_stock(self, product_id: str, qty: int) -> bool:
        """Reserve stock during checkout."""
        with transaction.atomic():
            stock = Stock.select_for_update().get(product_id=product_id)
            if stock.available >= qty:
                stock.reserved += qty
                stock.available -= qty
                stock.save()
                return True
            return False

    def confirm_stock(self, reservation_id: str):
        """Confirm reservation after order placed."""
        reservation.status = 'confirmed'
        reservation.save()

    def release_stock(self, reservation_id: str):
        """Release stock if order cancelled."""
        # Return reserved qty to available
```

### Multi-Warehouse
```sql
-- Stock per warehouse
SELECT
    p.sku,
    w.name as warehouse,
    s.quantity,
    s.reserved
FROM stock s
JOIN products p ON s.product_id = p.id
JOIN warehouses w ON s.warehouse_id = w.id
WHERE p.sku = 'SKU-123';
```

---

## Search & Catalog

### Product Indexing
```
Product → Indexer → Search Index (Elasticsearch/OpenSearch)
                  → Price Index
                  → Category Index
                  → Stock Index
```

### Faceted Search
```json
{
  "aggs": {
    "categories": {
      "terms": { "field": "category_ids" }
    },
    "price_ranges": {
      "range": {
        "field": "price",
        "ranges": [
          { "to": 50 },
          { "from": 50, "to": 100 },
          { "from": 100 }
        ]
      }
    },
    "brands": {
      "terms": { "field": "brand" }
    }
  }
}
```

---

## Performance

### Caching Layers
| Layer | Cache |
|-------|-------|
| Page | Varnish, CDN |
| Block | Redis |
| Query | MySQL Query Cache |
| Full Page | Redis FPC |

### Optimization Checklist
- [ ] Enable production mode
- [ ] Enable full page cache
- [ ] Optimize images (WebP)
- [ ] Minify JS/CSS
- [ ] Enable flat tables
- [ ] Configure CDN
- [ ] Index optimization

## Rules

- **MUST** model order lifecycle as an explicit state machine (pending → authorized → captured → fulfilled → refunded) — ad-hoc booleans produce inconsistent states on retry
- **MUST** separate payment capture from inventory decrement — reserve stock on order placement, commit stock on payment success. Coupling them causes stuck-stock bugs during payment retries.
- **NEVER** store CVV, full PAN, or track data — ever. PCI scope expands to any system that sees them, even "temporarily in memory".
- **NEVER** use floating-point for money calculations. Use `decimal.Decimal`, `BigDecimal`, or integer minor units (cents). Float rounding produces $0.01 discrepancies that accumulate into angry customer emails.
- **CRITICAL**: every cart mutation is idempotent via an `Idempotency-Key` or natural key — users double-click checkout buttons, networks retry, and duplicate orders are expensive to reconcile.
- **MANDATORY**: tax and shipping calculations live in isolated services or modules. Inlining them into cart logic prevents caching and creates compliance drift.

## Gotchas

- Promotion codes with stackable rules explode combinatorially — "20% off + free shipping + first-time buyer" can produce negative totals if the ordering of applications is not defined. Always normalize to a pipeline with a fixed evaluation order.
- Tax jurisdictions change **after** the order is placed (shipping address edits). A cart that recalculates on every update but not on address change silently under-collects tax.
- Inventory reservations must expire — otherwise abandoned carts hold stock forever. 15-30 minutes is typical; longer reservations need explicit business approval.
- Currency rounding rules differ by locale. Japanese Yen has 0 decimal places, Kuwaiti Dinar has 3. Defaulting to 2 decimals produces off-by-one-unit bugs in non-USD markets.
- Refunds are **not** negative orders. Payment processors treat them as separate resources with their own state machine and timing (Stripe refunds can take 5-10 business days to settle). Model accordingly.
- Magento's flat-table option speeds reads but silently stops auto-syncing if a reindex fails — stale product data in production. Monitor reindex job success, not just page latency.

## When NOT to Load

- For **payment provider** protocol specifics (Stripe, Adyen, PayPal) — use the provider's SDK docs; this skill is pattern-level
- For generic API design — use `/api-patterns`
- For database schema of orders/inventory — use `/database-patterns`
- For promotions and segmentation at scale — use `/data-analyst` agent
- For PCI compliance audit — this skill flags the traps but is not a substitute for a QSA audit
