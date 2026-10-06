"""Builds the GraphQL requests for draft products. Pure functions: they build, they do not send.

All four operations were checked with the Shopify schema validator on 5 Oct 2026 (against the
current schema, not a pinned version, so re-check after pinning SHOPIFY_API_VERSION).
Products are always created as DRAFT. One variant per product for now.
"""
from __future__ import annotations

import mimetypes
from pathlib import Path

STAGED_UPLOADS = """mutation StagedUploads($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets { url resourceUrl parameters { name value } }
    userErrors { field message }
  }
}"""

CREATE_PRODUCT = """mutation CreateProduct($product: ProductCreateInput!, $media: [CreateMediaInput!]) {
  productCreate(product: $product, media: $media) {
    product { id handle status variants(first: 1) { nodes { id } } }
    userErrors { field message }
  }
}"""

SET_VARIANT = """mutation SetVariant($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkUpdate(productId: $productId, variants: $variants) {
    productVariants { id price sku }
    userErrors { field message }
  }
}"""

CREATE_FILES = """mutation CreateFiles($files: [FileCreateInput!]!) {
  fileCreate(files: $files) {
    files { id fileStatus alt }
    userErrors { field message }
  }
}"""


def staged_upload_variables(image_dir: Path, filenames: list[str]) -> dict:
    """Variables for stagedUploadsCreate. Reads only file sizes. Rejects names that escape the folder."""
    inputs = []
    for name in filenames:
        path = (image_dir / name).resolve()
        if path.parent != image_dir.resolve():
            raise ValueError(f"{name!r} is not directly inside the image folder")
        if not path.is_file():
            raise FileNotFoundError(f"image not found: {name}")
        inputs.append({
            "filename": name,
            "mimeType": mimetypes.guess_type(name)[0] or "application/octet-stream",
            "httpMethod": "POST",
            "resource": "IMAGE",
            "fileSize": str(path.stat().st_size),
        })
    return {"input": inputs}


def product_variables(item: dict, resource_urls: dict[str, str]) -> dict:
    """Variables for productCreate. `resource_urls` maps an image file name to its staged resourceUrl."""
    product = {"title": item["title"], "handle": item["handle"], "status": "DRAFT"}
    for src, dst in (("description_html", "descriptionHtml"), ("vendor", "vendor"),
                     ("product_type", "productType"), ("tags", "tags")):
        if item.get(src):
            product[dst] = item[src]
    media = []
    for image in item.get("images", []):
        if image["file"] not in resource_urls:
            raise KeyError(f"no staged upload for {image['file']}")
        media.append({"originalSource": resource_urls[image["file"]], "mediaContentType": "IMAGE", "alt": image["alt"]})
    return {"product": product, "media": media}


def variant_variables(product_id: str, variant_id: str, item: dict) -> dict:
    variant = {"id": variant_id, "price": item["price"]}
    if item.get("compare_at_price"):
        variant["compareAtPrice"] = item["compare_at_price"]
    if item.get("sku"):
        variant["inventoryItem"] = {"sku": item["sku"]}
    return {"productId": product_id, "variants": [variant]}
