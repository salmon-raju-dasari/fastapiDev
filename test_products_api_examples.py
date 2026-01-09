"""
Example API Request Bodies for Testing Products API

Use these examples with tools like Postman, Thunder Client, or curl
"""

# ============================================
# 1. ADD PRODUCTS (POST /addProducts)
# ============================================

# Example 1: Complete Product with All Fields
complete_product = [
    {
        "productid": "PROD001",
        "productname": "Dell Inspiron 15 Laptop",
        "barcode": "1234567890123",
        "sku": "LAPTOP-DELL-001",
        "description": "High-performance laptop with 16GB RAM and 512GB SSD",
        "brand": "Dell",
        "category": "Electronics",
        "productimages": [
            "https://example.com/images/laptop1.jpg",
            "https://example.com/images/laptop2.jpg",
            "https://example.com/images/laptop3.jpg"
        ],
        "price": 1499.99,
        "unitvalue": 1,
        "unit": "pieces",
        "discount": 10,
        "gst": 18,
        "openingstock": 50,
        "mfgdate": "2024-01-15",
        "expirydate": "2026-01-15",
        "suppliername": "Tech Suppliers Ltd",
        "suppliercontact": "+91 9876543210",
        "customfields": [
            {"warranty": "2 years"},
            {"color": "Silver"},
            {"processor": "Intel i7"}
        ]
    }
]

# Example 2: Minimal Product (Only Required Fields)
minimal_product = [
    {
        "productid": "PROD002",
        "productname": "Samsung Galaxy S24",
        "barcode": "9876543210987",
        "price": 999.99
    }
]

# Example 3: Multiple Products at Once
multiple_products = [
    {
        "productid": "PROD003",
        "productname": "Apple iPhone 15",
        "barcode": "1111222233334",
        "price": 1299.00,
        "brand": "Apple",
        "category": "Electronics",
        "discount": 5,
        "gst": 18
    },
    {
        "productid": "PROD004",
        "productname": "Sony Headphones WH-1000XM5",
        "barcode": "5555666677778",
        "price": 349.99,
        "brand": "Sony",
        "category": "Accessories",
        "discount": 15,
        "gst": 18
    }
]

# ============================================
# 2. UPDATE PRODUCT (PUT /updateProduct/{id})
# ============================================

# Example: Partial Update (only updating price and discount)
update_product = {
    "price": 1199.99,
    "discount": 20
}

# Example: Update Multiple Fields
update_multiple_fields = {
    "productname": "Dell Inspiron 15 - Updated Model",
    "price": 1399.99,
    "discount": 15,
    "description": "Updated high-performance laptop with better specs",
    "openingstock": 75
}

# ============================================
# 3. SEARCH PRODUCTS (GET /searchProducts)
# ============================================

# Example query parameters:
search_examples = {
    "search_by_name": "?query=laptop",
    "search_by_category": "?category=Electronics",
    "search_by_brand": "?brand=Dell",
    "search_with_price_range": "?min_price=1000&max_price=2000",
    "combined_search": "?query=laptop&category=Electronics&min_price=1000&max_price=2000&brand=Dell"
}

# ============================================
# 4. DELETE PRODUCTS (DELETE /deleteProducts)
# ============================================

# Example: Bulk Delete by IDs
delete_multiple = [1, 2, 3, 4, 5]

# ============================================
# CURL EXAMPLES
# ============================================

"""
# 1. Add Products
curl -X POST "http://localhost:8000/addProducts" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '[
    {
      "productid": "PROD001",
      "productname": "Dell Laptop",
      "barcode": "1234567890123",
      "price": 1499.99
    }
  ]'

# 2. Get All Products
curl -X GET "http://localhost:8000/getProducts" \\
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. Get Product by ID
curl -X GET "http://localhost:8000/getProduct/1" \\
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. Update Product
curl -X PUT "http://localhost:8000/updateProduct/1" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "price": 1399.99,
    "discount": 15
  }'

# 5. Delete Product
curl -X DELETE "http://localhost:8000/deleteProduct/1" \\
  -H "Authorization: Bearer YOUR_TOKEN"

# 6. Search Products
curl -X GET "http://localhost:8000/searchProducts?query=laptop&category=Electronics" \\
  -H "Authorization: Bearer YOUR_TOKEN"

# 7. Bulk Delete
curl -X DELETE "http://localhost:8000/deleteProducts" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '[1, 2, 3]'
"""

# ============================================
# VALIDATION TEST CASES
# ============================================

# Test 1: Missing Required Field (should fail)
missing_barcode = [
    {
        "productid": "PROD005",
        "productname": "Test Product",
        # "barcode": "missing",  # This will cause validation error
        "price": 100.00
    }
]

# Test 2: Invalid Price (should fail)
invalid_price = [
    {
        "productid": "PROD006",
        "productname": "Test Product",
        "barcode": "1234567890",
        "price": -100.00  # Negative price not allowed
    }
]

# Test 3: Too Many Images (should fail)
too_many_images = [
    {
        "productid": "PROD007",
        "productname": "Test Product",
        "barcode": "1234567890",
        "price": 100.00,
        "productimages": [
            "img1.jpg", "img2.jpg", "img3.jpg",
            "img4.jpg", "img5.jpg", "img6.jpg"  # 6 images, max is 5
        ]
    }
]

# Test 4: Invalid Discount Range (should fail)
invalid_discount = [
    {
        "productid": "PROD008",
        "productname": "Test Product",
        "barcode": "1234567890",
        "price": 100.00,
        "discount": 150  # Discount must be 0-100
    }
]

# Test 5: Duplicate ProductID (should fail if PROD001 exists)
duplicate_productid = [
    {
        "productid": "PROD001",  # Assuming this already exists
        "productname": "Another Product",
        "barcode": "9999999999",
        "price": 200.00
    }
]

print("Product API Test Examples Ready!")
print("Copy the examples above to test your API endpoints")
