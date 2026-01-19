from google.cloud import storage
from google.oauth2 import service_account
from PIL import Image
import io
import os
from datetime import datetime
import uuid
from typing import Optional, Tuple
from fastapi import UploadFile

class StorageService:
    def __init__(self):
        credentials_path = os.getenv("GCS_CREDENTIALS_PATH")
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        self.cdn_base_url = os.getenv("CDN_BASE_URL")
        
        if not credentials_path or not self.bucket_name or not self.cdn_base_url:
            raise ValueError("GCS configuration missing in .env file")
        
        # Make path absolute if it's relative
        if not os.path.isabs(credentials_path):
            credentials_path = os.path.join(os.getcwd(), credentials_path)
        
        if not os.path.exists(credentials_path):
            raise ValueError(f"GCS credentials file not found at: {credentials_path}")
        
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        self.client = storage.Client(credentials=credentials)
        self.bucket = self.client.bucket(self.bucket_name)
    
    def _generate_filename(self, original_filename: str, prefix: str) -> str:
        """Generate unique filename"""
        ext = os.path.splitext(original_filename)[1].lower()
        if not ext:
            ext = '.jpg'
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{prefix}/{timestamp}_{unique_id}{ext}"
    
    def _optimize_image(self, file_content: bytes, max_size: Tuple[int, int] = (1920, 1920)) -> bytes:
        """Optimize and compress image"""
        image = Image.open(io.BytesIO(file_content))
        
        # Convert RGBA to RGB if needed
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if larger than max_size
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save optimized image
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=85, optimize=True)
        return output.getvalue()
    
    def _create_thumbnail(self, file_content: bytes, size: Tuple[int, int] = (300, 300)) -> bytes:
        """Create thumbnail"""
        image = Image.open(io.BytesIO(file_content))
        
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        image.thumbnail(size, Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=80, optimize=True)
        return output.getvalue()
    
    async def upload_image(
        self, 
        file: UploadFile, 
        folder: str,
        create_thumbnail: bool = False
    ) -> dict:
        """
        Upload image to GCS
        
        Args:
            file: FastAPI UploadFile
            folder: Folder name (avatars, logos, products)
            create_thumbnail: Whether to create thumbnail
            
        Returns:
            dict with 'url' and optionally 'thumbnail_url'
        """
        try:
            # Read file content
            content = await file.read()
            
            # Optimize main image
            optimized_content = self._optimize_image(content)
            
            # Generate filename
            filename = self._generate_filename(file.filename, folder)
            
            # Upload main image
            blob = self.bucket.blob(filename)
            blob.upload_from_string(
                optimized_content,
                content_type='image/jpeg'
            )
            blob.make_public()
            
            result = {
                "url": f"{self.cdn_base_url}/{filename}"
            }
            
            # Create and upload thumbnail if requested
            if create_thumbnail:
                thumbnail_content = self._create_thumbnail(content)
                # Create thumbs folder within the main folder
                thumbnail_filename = filename.replace(f"{folder}/", f"{folder}/thumbs/")
                
                thumb_blob = self.bucket.blob(thumbnail_filename)
                thumb_blob.upload_from_string(
                    thumbnail_content,
                    content_type='image/jpeg'
                )
                thumb_blob.make_public()
                
                result["thumbnail_url"] = f"{self.cdn_base_url}/{thumbnail_filename}"
            
            return result
            
        except Exception as e:
            raise Exception(f"Failed to upload image: {str(e)}")
    
    def delete_image(self, image_url: str) -> bool:
        """Delete image from GCS"""
        try:
            if not image_url or not image_url.startswith(self.cdn_base_url):
                return False
                
            # Extract filename from URL
            filename = image_url.replace(f"{self.cdn_base_url}/", "")
            blob = self.bucket.blob(filename)
            
            if blob.exists():
                blob.delete()
            
            # Delete thumbnail if exists
            if "/avatars/" in filename or "/products/" in filename:
                thumb_filename = filename.replace("/avatars/", "/avatars/thumbs/").replace("/products/", "/products/thumbs/")
                thumb_blob = self.bucket.blob(thumb_filename)
                if thumb_blob.exists():
                    thumb_blob.delete()
            
            return True
        except Exception as e:
            print(f"Failed to delete image: {str(e)}")
            return False
    
    def upload_base64_image(self, base64_data: str, folder: str = "products") -> str:
        """
        Upload base64 encoded image to GCS
        
        Args:
            base64_data: Base64 encoded image string (with or without data URI prefix)
            folder: Folder name (products, avatars, logos)
            
        Returns:
            Public URL of uploaded image
        """
        import base64
        import logging
        
        try:
            # Remove data URI prefix if present (e.g., "data:image/jpeg;base64,")
            if "," in base64_data and base64_data.startswith("data:"):
                base64_data = base64_data.split(",")[1]
            
            logging.info(f"Decoding base64 image (length: {len(base64_data)} chars)")
            
            # Decode base64 to bytes
            image_bytes = base64.b64decode(base64_data)
            logging.info(f"Decoded image size: {len(image_bytes)} bytes")
            
            # Optimize image
            optimized_content = self._optimize_image(image_bytes)
            logging.info(f"Optimized image size: {len(optimized_content)} bytes")
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{folder}/{timestamp}_{unique_id}.jpg"
            
            logging.info(f"Uploading image to GCS: {filename}")
            
            # Upload to GCS
            blob = self.bucket.blob(filename)
            blob.upload_from_string(optimized_content, content_type="image/jpeg")
            blob.make_public()
            
            url = f"{self.cdn_base_url}/{filename}"
            logging.info(f"Image uploaded successfully: {url}")
            
            return url
            
        except Exception as e:
            raise Exception(f"Failed to upload base64 image: {str(e)}")
    
    def upload_product_images(self, base64_images: list, max_images: int = 5) -> list:
        """
        Upload multiple product images from base64
        
        Args:
            base64_images: List of base64 encoded images
            max_images: Maximum number of images allowed (default: 5)
            
        Returns:
            List of public URLs
            
        Raises:
            ValueError: If more than max_images are provided
        """
        import logging
        
        if len(base64_images) > max_images:
            raise ValueError(f"Maximum {max_images} images allowed. You provided {len(base64_images)} images.")
        
        uploaded_urls = []
        failed_count = 0
        
        for base64_img in base64_images:
            try:
                url = self.upload_base64_image(base64_img, folder="products")
                uploaded_urls.append(url)
            except Exception as e:
                failed_count += 1
                logging.error(f"Failed to upload image: {str(e)}")
        
        # If all images failed, raise an exception
        if failed_count > 0 and len(uploaded_urls) == 0:
            raise Exception(f"Failed to upload all {len(base64_images)} images. Please check GCS credentials and permissions.")
        
        return uploaded_urls

# Singleton instance - initialized when first imported
try:
    storage_service = StorageService()
except Exception as e:
    import logging
    logging.error(f"Failed to initialize StorageService: {str(e)}")
    logging.error("Make sure GCS_CREDENTIALS_PATH, GCS_BUCKET_NAME, and CDN_BASE_URL are set in .env file")
    storage_service = None
