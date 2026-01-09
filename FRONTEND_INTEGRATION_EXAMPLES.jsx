// Frontend Integration Examples for Products API
// This file contains React code examples for integrating with the Products API

// ============================================
// 1. API SERVICE (Create this in src/services/api/products.js)
// ============================================

import axios from './axios'; // Your axios instance with auth

const ProductService = {
  // Get all products for card display
  getAllProducts: async () => {
    try {
      const response = await axios.get('/getProducts');
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data || 'Failed to fetch products'
      };
    }
  },

  // Get single product by ID (for edit form)
  getProductById: async (productId) => {
    try {
      const response = await axios.get(`/getProduct/${productId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data || 'Failed to fetch product'
      };
    }
  },

  // Add new products
  addProducts: async (products) => {
    try {
      const response = await axios.post('/addProducts', products);
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data || 'Failed to add products'
      };
    }
  },

  // Update product
  updateProduct: async (productId, productData) => {
    try {
      const response = await axios.put(`/updateProduct/${productId}`, productData);
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data || 'Failed to update product'
      };
    }
  },

  // Delete single product
  deleteProduct: async (productId) => {
    try {
      const response = await axios.delete(`/deleteProduct/${productId}`);
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data || 'Failed to delete product'
      };
    }
  },

  // Bulk delete products
  deleteProducts: async (productIds) => {
    try {
      const response = await axios.delete('/deleteProducts', { data: productIds });
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data || 'Failed to delete products'
      };
    }
  },

  // Search products
  searchProducts: async (filters) => {
    try {
      const params = new URLSearchParams();
      if (filters.query) params.append('query', filters.query);
      if (filters.category) params.append('category', filters.category);
      if (filters.brand) params.append('brand', filters.brand);
      if (filters.min_price) params.append('min_price', filters.min_price);
      if (filters.max_price) params.append('max_price', filters.max_price);
      
      const response = await axios.get(`/searchProducts?${params.toString()}`);
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data || 'Failed to search products'
      };
    }
  }
};

export default ProductService;

// ============================================
// 2. PRODUCT CARD COMPONENT
// ============================================

import React from 'react';
import { Card, CardContent, CardMedia, Typography, Button, Chip, Box } from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';

const ProductCard = ({ product, onEdit, onDelete }) => {
  const firstImage = product.productimages?.[0] || '/placeholder-product.jpg';
  const formattedPrice = new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR'
  }).format(product.price);

  return (
    <Card sx={{ maxWidth: 345, m: 2 }}>
      <CardMedia
        component="img"
        height="200"
        image={firstImage}
        alt={product.productname}
      />
      <CardContent>
        <Typography gutterBottom variant="h6" component="div">
          {product.productname}
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1, mb: 1 }}>
          {product.brand && (
            <Chip label={product.brand} size="small" color="primary" />
          )}
          {product.category && (
            <Chip label={product.category} size="small" variant="outlined" />
          )}
        </Box>

        <Typography variant="h5" color="primary" sx={{ mb: 1 }}>
          {formattedPrice}
          {product.discount > 0 && (
            <Chip 
              label={`${product.discount}% OFF`} 
              size="small" 
              color="error" 
              sx={{ ml: 1 }}
            />
          )}
        </Typography>

        {product.description && (
          <Typography variant="body2" color="text.secondary" noWrap>
            {product.description}
          </Typography>
        )}

        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
          <Button 
            variant="outlined" 
            startIcon={<EditIcon />}
            onClick={() => onEdit(product)}
            fullWidth
          >
            Edit
          </Button>
          <Button 
            variant="outlined" 
            color="error"
            startIcon={<DeleteIcon />}
            onClick={() => onDelete(product.id)}
            fullWidth
          >
            Delete
          </Button>
        </Box>

        <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid #eee' }}>
          <Typography variant="caption" display="block">
            Product ID: {product.productid}
          </Typography>
          <Typography variant="caption" display="block">
            Stock: {product.quantity} {product.unit || 'units'}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default ProductCard;

// ============================================
// 3. ALL PRODUCTS PAGE COMPONENT
// ============================================

import React, { useState, useEffect } from 'react';
import { Grid, Container, Typography, Button, CircularProgress, Alert } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import ProductCard from './ProductCard';
import ProductService from '../services/api/products';

const AllProductsPage = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch all products
  const fetchProducts = async () => {
    setLoading(true);
    setError(null);
    const result = await ProductService.getAllProducts();
    if (result.success) {
      setProducts(result.data);
    } else {
      setError(result.error?.message || 'Failed to load products');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  // Handle edit - navigate to add product page with product data
  const handleEdit = (product) => {
    // Store product in state/context or pass via navigation
    navigate('/add-product', { state: { product, isEdit: true } });
  };

  // Handle delete
  const handleDelete = async (productId) => {
    if (!window.confirm('Are you sure you want to delete this product?')) {
      return;
    }

    const result = await ProductService.deleteProduct(productId);
    if (result.success) {
      // Refresh products list
      fetchProducts();
      // Show success message
      alert('Product deleted successfully!');
    } else {
      alert(result.error?.message || 'Failed to delete product');
    }
  };

  if (loading) {
    return (
      <Container sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">All Products</Typography>
        <Button 
          variant="contained" 
          startIcon={<AddIcon />}
          onClick={() => navigate('/add-product')}
        >
          Add Product
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2}>
        {products.map((product) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={product.id}>
            <ProductCard 
              product={product}
              onEdit={handleEdit}
              onDelete={handleDelete}
            />
          </Grid>
        ))}
      </Grid>

      {products.length === 0 && !loading && (
        <Typography variant="h6" color="text.secondary" align="center" sx={{ mt: 4 }}>
          No products found. Click "Add Product" to create your first product.
        </Typography>
      )}
    </Container>
  );
};

export default AllProductsPage;

// ============================================
// 4. ADD/EDIT PRODUCT FORM
// ============================================

import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Container, Paper, Typography, TextField, Button, Grid,
  FormControl, InputLabel, Select, MenuItem, Box, Alert
} from '@mui/material';
import ProductService from '../services/api/products';

const AddEditProductPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const isEdit = location.state?.isEdit || false;
  const existingProduct = location.state?.product || null;

  const [formData, setFormData] = useState({
    productid: '',
    productname: '',
    barcode: '',
    sku: '',
    description: '',
    brand: '',
    category: '',
    price: '',
    unitvalue: '',
    unit: '',
    discount: 0,
    gst: 0,
    openingstock: 0,
    mfgdate: '',
    expirydate: '',
    suppliername: '',
    suppliercontact: '',
    productimages: ['', '', '', '', ''],
  });

  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);
  const [loading, setLoading] = useState(false);

  // Auto-populate form if editing
  useEffect(() => {
    if (isEdit && existingProduct) {
      setFormData({
        productid: existingProduct.productid || '',
        productname: existingProduct.productname || '',
        barcode: existingProduct.barcode || '',
        sku: existingProduct.sku || '',
        description: existingProduct.description || '',
        brand: existingProduct.brand || '',
        category: existingProduct.category || '',
        price: existingProduct.price || '',
        unitvalue: existingProduct.unitvalue || '',
        unit: existingProduct.unit || '',
        discount: existingProduct.discount || 0,
        gst: existingProduct.gst || 0,
        openingstock: existingProduct.openingstock || 0,
        mfgdate: existingProduct.mfgdate || '',
        expirydate: existingProduct.expirydate || '',
        suppliername: existingProduct.suppliername || '',
        suppliercontact: existingProduct.suppliercontact || '',
        productimages: existingProduct.productimages || ['', '', '', '', ''],
      });
    }
  }, [isEdit, existingProduct]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // Clear error for this field
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: null }));
    }
  };

  const handleImageChange = (index, value) => {
    const newImages = [...formData.productimages];
    newImages[index] = value;
    setFormData(prev => ({ ...prev, productimages: newImages }));
  };

  const validateForm = () => {
    const newErrors = {};

    // Required fields
    if (!formData.productid?.trim()) newErrors.productid = 'Product ID is required';
    if (!formData.productname?.trim()) newErrors.productname = 'Product name is required';
    if (!formData.barcode?.trim()) newErrors.barcode = 'Barcode is required';
    if (!formData.price || parseFloat(formData.price) <= 0) {
      newErrors.price = 'Price must be greater than 0';
    }

    // Range validations
    if (formData.discount < 0 || formData.discount > 100) {
      newErrors.discount = 'Discount must be between 0 and 100';
    }
    if (formData.gst < 0 || formData.gst > 100) {
      newErrors.gst = 'GST must be between 0 and 100';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitError(null);

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    // Prepare data (remove empty image URLs)
    const productData = {
      ...formData,
      productimages: formData.productimages.filter(img => img.trim() !== ''),
      price: parseFloat(formData.price),
      discount: parseInt(formData.discount) || 0,
      gst: parseInt(formData.gst) || 0,
      openingstock: parseInt(formData.openingstock) || 0,
      unitvalue: formData.unitvalue ? parseInt(formData.unitvalue) : null,
    };

    let result;
    if (isEdit) {
      // Update existing product
      result = await ProductService.updateProduct(existingProduct.id, productData);
    } else {
      // Add new product
      result = await ProductService.addProducts([productData]);
    }

    setLoading(false);

    if (result.success) {
      alert(`Product ${isEdit ? 'updated' : 'added'} successfully!`);
      navigate('/products');
    } else {
      setSubmitError(result.error?.message || `Failed to ${isEdit ? 'update' : 'add'} product`);
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom>
          {isEdit ? 'Edit Product' : 'Add New Product'}
        </Typography>

        {submitError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {submitError}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <Grid container spacing={3}>
            {/* Product ID */}
            <Grid item xs={12} sm={6}>
              <TextField
                required
                fullWidth
                label="Product ID"
                name="productid"
                value={formData.productid}
                onChange={handleChange}
                error={!!errors.productid}
                helperText={errors.productid}
                disabled={isEdit} // Don't allow changing product ID when editing
              />
            </Grid>

            {/* Product Name */}
            <Grid item xs={12} sm={6}>
              <TextField
                required
                fullWidth
                label="Product Name"
                name="productname"
                value={formData.productname}
                onChange={handleChange}
                error={!!errors.productname}
                helperText={errors.productname}
              />
            </Grid>

            {/* Barcode */}
            <Grid item xs={12} sm={6}>
              <TextField
                required
                fullWidth
                label="Barcode"
                name="barcode"
                value={formData.barcode}
                onChange={handleChange}
                error={!!errors.barcode}
                helperText={errors.barcode}
              />
            </Grid>

            {/* SKU */}
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="SKU"
                name="sku"
                value={formData.sku}
                onChange={handleChange}
              />
            </Grid>

            {/* Price */}
            <Grid item xs={12} sm={4}>
              <TextField
                required
                fullWidth
                type="number"
                label="Price"
                name="price"
                value={formData.price}
                onChange={handleChange}
                error={!!errors.price}
                helperText={errors.price}
                inputProps={{ step: "0.01", min: "0" }}
              />
            </Grid>

            {/* Discount */}
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="Discount (%)"
                name="discount"
                value={formData.discount}
                onChange={handleChange}
                error={!!errors.discount}
                helperText={errors.discount}
                inputProps={{ min: "0", max: "100" }}
              />
            </Grid>

            {/* GST */}
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                type="number"
                label="GST (%)"
                name="gst"
                value={formData.gst}
                onChange={handleChange}
                error={!!errors.gst}
                helperText={errors.gst}
                inputProps={{ min: "0", max: "100" }}
              />
            </Grid>

            {/* Brand */}
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Brand"
                name="brand"
                value={formData.brand}
                onChange={handleChange}
              />
            </Grid>

            {/* Category */}
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Category"
                name="category"
                value={formData.category}
                onChange={handleChange}
              />
            </Grid>

            {/* Description */}
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={4}
                label="Description"
                name="description"
                value={formData.description}
                onChange={handleChange}
              />
            </Grid>

            {/* Product Images */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Product Images (Max 5)
              </Typography>
              {formData.productimages.map((img, index) => (
                <TextField
                  key={index}
                  fullWidth
                  label={`Image URL ${index + 1}`}
                  value={img}
                  onChange={(e) => handleImageChange(index, e.target.value)}
                  sx={{ mb: 2 }}
                />
              ))}
            </Grid>

            {/* Additional fields... */}
            
            {/* Submit Buttons */}
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
                <Button
                  variant="outlined"
                  onClick={() => navigate('/products')}
                  disabled={loading}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={loading}
                >
                  {loading ? 'Saving...' : isEdit ? 'Update Product' : 'Add Product'}
                </Button>
              </Box>
            </Grid>
          </Grid>
        </form>
      </Paper>
    </Container>
  );
};

export default AddEditProductPage;

// ============================================
// 5. USAGE IN APP
// ============================================

/*
// In your App.jsx or Routes configuration:

import AllProductsPage from './pages/AllProductsPage';
import AddEditProductPage from './pages/AddEditProductPage';

// Add these routes:
<Route path="/products" element={<AllProductsPage />} />
<Route path="/add-product" element={<AddEditProductPage />} />
*/
