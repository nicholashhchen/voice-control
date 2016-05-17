# voice-control

## Configuration

1. Create a private application on your Shopify store

2. Create a `.env` file with the following contents:
```
SHOPIFY_KEY=<your-shopify-api-key>
SHOPIFY_PASS=<your-shopify-password>
APIAI_TOKEN=<your-api.ai-token>
APIAI_KEY=<your-api.ai-subscription-key>
```

3. You'll also need to update `SHOP_URL` in `voice_demo.py` to point to your own Shopify store.
