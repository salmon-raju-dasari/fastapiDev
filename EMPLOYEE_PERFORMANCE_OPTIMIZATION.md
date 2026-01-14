# Employee Endpoint Performance Optimization

## Issues Identified

Compared to products and stores endpoints, the employees endpoint was slower due to:

### 1. **Avatar Base64 Encoding** (BIGGEST BOTTLENECK)
- **Before**: Every avatar blob was encoded to base64 for ALL employees in the list
- **Impact**: If you have 100 employees with 1MB avatars each, that's 100MB of data being encoded on every request
- **Fix**: 
  - Added size limit (500KB) for automatic encoding
  - Created separate `/avatar/{emp_id}` endpoint for large avatars
  - Frontend should fetch avatars separately only when needed

### 2. **Duplicate Store Lookups**
- **Before**: Building list of store_ids with duplicates `[emp.store_id for emp in employees if emp.store_id]`
- **Impact**: If 50 employees share 5 stores, still querying same stores multiple times
- **Fix**: Use `list(set([...]))` to deduplicate store IDs before query

### 3. **Missing Database Indexes**
- **Impact**: Slow queries on filtered fields (role, store_id, email, custom fields)
- **Fix**: Created `optimize_employee_queries.py` to add indexes

## Performance Improvements Applied

### Code Changes

1. **Avatar Optimization** (lines 493-495)
   ```python
   # Only encode avatar if it exists and is under 500KB
   if emp.avatar_blob and len(emp.avatar_blob) < 500000:
       avatar_base64 = base64.b64encode(emp.avatar_blob).decode('utf-8')
   ```

2. **Deduplicate Store IDs** (line 471)
   ```python
   store_ids = list(set([emp.store_id for emp in employees if emp.store_id]))
   ```

3. **New Avatar Endpoint** (lines 737-768)
   - GET `/employees/avatar/{emp_id}` - Fetch avatar separately
   - Reduces payload size in main list endpoint

### Database Indexes

Run this script to add indexes:
```bash
python optimize_employee_queries.py
```

**Indexes Added:**
- `idx_employees_business_role` - Fast filtering by business and role
- `idx_employees_business_store` - Fast filtering by business and store
- `idx_employees_email` - Fast email lookups
- `idx_employee_labels_emp_business` - Fast custom field queries
- `idx_employee_labels_name_value` - Fast label filtering
- `idx_employee_labels_business_name` - Fast label name lookups

## Expected Performance Gain

- **Without avatars**: ~60-80% faster (similar to products/stores)
- **With small avatars (<500KB)**: ~40-50% faster
- **Large avatars (>500KB)**: Fetch separately via new endpoint

## Frontend Updates Needed

If employees have large avatars, update your frontend to:

1. **Load avatar separately when needed:**
   ```javascript
   // Instead of using avatar_base64 from list response
   // Fetch it separately
   const avatar = await fetch(`/employees/avatar/${emp_id}`)
   ```

2. **Lazy load avatars:**
   - Load avatars only when scrolling to view
   - Use placeholder image initially

## Testing

1. **Run optimization script:**
   ```bash
   python optimize_employee_queries.py
   ```

2. **Test endpoint speed:**
   ```bash
   # Before optimization
   curl -w "@time.txt" http://localhost:8000/employees/
   
   # After optimization (should be much faster)
   curl -w "@time.txt" http://localhost:8000/employees/
   ```

3. **Check avatar endpoint:**
   ```bash
   curl http://localhost:8000/employees/avatar/1000
   ```

## Additional Recommendations

1. **Add pagination caching** - Cache results for common queries
2. **Use Redis** - Cache employee lists for faster repeated queries
3. **Implement GraphQL** - Let frontend request only needed fields
4. **Compress responses** - Enable gzip compression in FastAPI
5. **Database connection pooling** - Already configured in database.py

## Monitoring

Monitor these metrics:
- Query execution time (should be < 100ms)
- Payload size (should be < 1MB for 100 employees without avatars)
- Database connection pool usage
- Memory usage during avatar encoding
