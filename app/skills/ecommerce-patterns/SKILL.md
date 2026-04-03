---
name: ecommerce-patterns
description: "Loaded when user asks about e-commerce or shopping cart features"
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
