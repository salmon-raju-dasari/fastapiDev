# Products API Documentation

## Overview
Complete CRUD operations for the Products module with comprehensive validations.

## Table Schema

### Products Table Fields

| Field Name | Type | Required | Unique | Max Length | Description |
|------------|------|----------|--------|------------|-------------|
| id | Integer | Auto | Yes | - | Primary key (auto-generated) |
| productid | String | Yes | Yes | 100 | Unique product identifier |
| productname | String | Yes | No | 500 | Product name |
| barcode | String | Yes | No | 100 | Product barcode |
| sku | String | No | Yes | 100 | Stock Keeping Unit |
| description | String | No | No | 2000 | Product description |
| brand | String | No | No | 100 | Product brand |
| category | String | No | No | 100 | Product category |
| productimages | Array | No | No | Max 5 | Array of image URLs/paths |
| price | Decimal(10,2) | Yes | No | - | Product price (00.00 format) |
| unitvalue | BigInteger | No | No | - | Unit value in lakhs of rupees |
| unit | String | No | No | 50 | Unit of measurement |
| discount | Integer | No | No | 0-100 | Discount percentage |
| gst | Integer | No | No | 0-100 | GST percentage |
| openingstock | BigInteger | No | No | - | Opening stock quantity |
| quantity | Integer | No | No | - | Current quantity |
| mfgdate | String | No | No | 50 | Manufacturing date |
| expirydate | String | No | No | 50 | Expiry date |
| suppliername | String | No | No | 100 | Supplier name |
| suppliercontact | String | No | No | 100 | Supplier contact |
| customfields | JSON | No | No | - | Array of custom field objects |
| created_at | DateTime | Auto | No | - | Creation timestamp |
| updated_at | DateTime | Auto | No | - | Last update timestamp |
| updated_by | String | Auto | No | 50 | User who last updated |

## API Endpoints

### 1. Add Products (POST)
**Endpoint:** `POST /addProducts`

**Authentication:** Required (Owner, Admin, Manager roles)

**Request Body:**
```json
[
  {
    "productid": "PROD001",
    "productname": "Laptop Dell Inspiron 15",
    "barcode": "1234567890123",
    "sku": "LAPTOP001",
    "description": "High-performance laptop",
    "brand": "Dell",
    "category": "Electronics",
    "productimages": ["image1.jpg", "image2.jpg", "image3.jpg"],
    "price": 1499.99,
    "unitvalue": 1,
    "unit": "pieces",
    "discount": 10,
    "gst": 18,
    "openingstock": 50,
    "mfgdate": "2024-01-01",
    "expirydate": "2026-01-01",
    "suppliername": "ABC Suppliers",
    "suppliercontact": "+91 9876543210",
    "customfields": [
      {"warranty": "2 years"},
      {"color": "black"}
    ]
  }
]
```

**Validations:**
- `productid`: Required, 1-100 characters, unique
- `productname`: Required, 1-500 characters
- `barcode`: Required, 1-100 characters
- `price`: Required, > 0, stored as decimal with 2 places
- `productimages`: Maximum 5 images
- `discount`, `gst`: 0-100 range
- `openingstock`, `unitvalue`: >= 0

**Response:** `201 Created`
```json
[
  {
    "id": 1,
    "productid": "PROD001",
    "productname": "Laptop Dell Inspiron 15",
    "barcode": "1234567890123",
    "sku": "LAPTOP001",
    "price": 1499.99,
    "created_at": "2024-01-09T10:30:00Z",
    "updated_at": "2024-01-09T10:30:00Z",
    "updated_by": "admin"
  }
]
```

### 2. Get All Products (GET)
**Endpoint:** `GET /getProducts`

**Authentication:** Required (All roles)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "productid": "PROD001",
    "productname": "Laptop Dell Inspiron 15",
    "barcode": "1234567890123",
    "sku": "LAPTOP001",
    "description": "High-performance laptop",
    "brand": "Dell",
    "category": "Electronics",
    "productimages": ["image1.jpg", "image2.jpg"],
    "price": 1499.99,
    "unitvalue": 1,
    "unit": "pieces",
    "discount": 10,
    "gst": 18,
    "openingstock": 50,
    "quantity": 50,
    "mfgdate": "2024-01-01",
    "expirydate": "2026-01-01",
    "suppliername": "ABC Suppliers",
    "suppliercontact": "+91 9876543210",
    "customfields": [{"warranty": "2 years"}],
    "created_at": "2024-01-09T10:30:00Z",
    "updated_at": "2024-01-09T10:30:00Z",
    "updated_by": "admin"
  }
]
```

### 3. Get Product by ID (GET)
**Endpoint:** `GET /getProduct/{product_id}`

**Authentication:** Required (All roles)

**Path Parameter:** `product_id` - Integer (database ID)

**Use Case:** Populate edit form with product details

**Response:** `200 OK` - Single product object

### 4. Get Product by Product ID (GET)
**Endpoint:** `GET /getProductByProductId/{productid}`

**Authentication:** Required (All roles)

**Path Parameter:** `productid` - String (product identifier)

**Use Case:** Search/filter products by productid

**Response:** `200 OK` - Single product object

### 5. Update Product (PUT)
**Endpoint:** `PUT /updateProduct/{product_id}`

**Authentication:** Required (Owner, Admin, Manager roles)

**Path Parameter:** `product_id` - Integer (database ID)

**Request Body:** (All fields optional - only send fields to update)
```json
{
  "productname": "Updated Laptop Name",
  "price": 1299.99,
  "discount": 15,
  "gst": 18
}
```

**Validations:**
- Checks for duplicate `productid`, `barcode`, `sku` if being updated
- All field validations apply as in create
- At least one field must be provided

**Response:** `200 OK` - Updated product object

### 6. Delete Product (DELETE)
**Endpoint:** `DELETE /deleteProduct/{product_id}`

**Authentication:** Required (Owner, Admin, Manager roles)

**Path Parameter:** `product_id` - Integer (database ID)

**Response:** `200 OK`
```json
{
  "status": "success",
  "message": "Product deleted successfully",
  "deleted_product": {
    "id": 1,
    "productid": "PROD001",
    "productname": "Laptop Dell Inspiron 15"
  }
}
```

### 7. Bulk Delete Products (DELETE)
**Endpoint:** `DELETE /deleteProducts`

**Authentication:** Required (Owner, Admin, Manager roles)

**Request Body:**
```json
[1, 2, 3, 4, 5]
```

**Response:** `200 OK`
```json
{
  "summary": {
    "total": 5,
    "successful": 4,
    "failed": 1
  },
  "results": [
    {
      "product_index": 0,
      "product_id": 1,
      "status": "success",
      "message": "Product 'Laptop' deleted successfully"
    },
    {
      "product_index": 1,
      "product_id": 2,
      "status": "failed",
      "error": "Product with ID 2 not found",
      "type": "not_found"
    }
  ]
}
```

### 8. Search Products (GET)
**Endpoint:** `GET /searchProducts`

**Authentication:** Required (All roles)

**Query Parameters:**
- `query`: Search in productname, productid, barcode, SKU
- `category`: Filter by category
- `brand`: Filter by brand
- `min_price`: Minimum price filter
- `max_price`: Maximum price filter

**Example:**
```
GET /searchProducts?query=laptop&category=Electronics&min_price=1000&max_price=2000
```

**Response:** `200 OK` - Array of matching products

## Error Responses

### 400 Bad Request
```json
{
  "error": "ValidationError",
  "message": "Product data validation failed",
  "type": "validation_error",
  "validation_details": [...]
}
```

### 404 Not Found
```json
{
  "error": "NotFoundError",
  "message": "Product with ID 123 not found",
  "type": "not_found"
}
```

### 409 Conflict (Duplicate Entry)
```json
{
  "error": "DuplicateEntryError",
  "message": "Product with productid 'PROD001' already exists",
  "field": "productid",
  "type": "duplicate_entry"
}
```

### 500 Internal Server Error
```json
{
  "error": "InternalServerError",
  "message": "An unexpected error occurred",
  "type": "server_error",
  "suggestion": "Please try again or contact support"
}
```

## Frontend Integration Guide

### Display All Products (Cards)
1. Call `GET /getProducts` to fetch all products
2. Display each product in a card showing:
   - Product image (first image from `productimages` array)
   - Product name
   - Price (formatted with currency)
   - Brand, Category
   - Discount badge if applicable
   - Edit and Delete buttons

### Edit Product Flow
1. User clicks Edit button on product card
2. Call `GET /getProduct/{product_id}` to get complete product details
3. Auto-populate the Add Products form with fetched data
4. User modifies fields
5. Call `PUT /updateProduct/{product_id}` with only changed fields

### Delete Product Flow
1. User clicks Delete button on product card
2. Show confirmation dialog
3. Call `DELETE /deleteProduct/{product_id}`
4. Refresh product list

### Add Product Flow
1. User fills the Add Products form
2. Validate all required fields:
   - productid (required, unique)
   - productname (required)
   - barcode (required)
   - price (required, > 0)
3. Call `POST /addProducts` with product data
4. Show success/error message
5. Refresh product list

## Migration Instructions

1. **Backup existing data:**
   ```bash
   # Backup is automatically created by migration script
   ```

2. **Run migration:**
   ```bash
   cd C:\fastapiDev
   python migrate_products_table.py
   ```

3. **Verify migration:**
   - Check that the new table structure is created
   - Verify existing products are migrated
   - Test API endpoints

4. **Drop backup (after verification):**
   ```sql
   DROP TABLE products_backup;
   ```

## Testing Checklist

- [ ] Add single product with all fields
- [ ] Add single product with only required fields
- [ ] Add multiple products in one request
- [ ] Validate required field errors
- [ ] Validate duplicate productid/barcode/sku errors
- [ ] Validate price format (2 decimal places)
- [ ] Validate productimages array (max 5)
- [ ] Validate discount/gst range (0-100)
- [ ] Get all products
- [ ] Get single product by ID
- [ ] Get single product by productid
- [ ] Update product (partial update)
- [ ] Update product with duplicate checks
- [ ] Delete single product
- [ ] Bulk delete products
- [ ] Search products with various filters
- [ ] Test role-based access control
