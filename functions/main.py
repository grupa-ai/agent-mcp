#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import asyncio
import uuid

# Adjust path for Cloud Functions environment if necessary
if os.environ.get('FUNCTIONS_EMULATOR') != 'true' and '/workspace' not in sys.path:
    sys.path.insert(0, '/workspace')

import firebase_functions.options
from firebase_functions.https_fn import on_request, Request
# from firebase_functions.https_fn import AsgiRequestAdapter # Not available in 0.4.2
# from firebase_functions.storage_fn import StorageObjectData, on_object_finalized # Not needed

# Import your FastAPI app and Mangum
from fastapi import FastAPI
from mcp_network_server import router as network_router, find_firebase_key
from mangum import Mangum
import base64 # Needed for body encoding
import urllib.parse # Needed for query string parsing

firebase_functions.options.set_global_options(region=firebase_functions.options.SupportedRegion.EUROPE_WEST1)

# Initialize Firebase once
find_firebase_key()

# Create a FastAPI app
app = FastAPI()

# --- Root endpoint (Define BEFORE including router) ---
@app.get("/")
async def root():
    """Basic health check endpoint"""
    return {"message": "MCP Network Server is running!"}

# Include the router from the network server
app.include_router(network_router) # This adds routes like /register, /message/*, etc.

# Create a Mangum handler
handler = Mangum(app, lifespan="off") # lifespan="off" can sometimes help in simple cases

@on_request()
def mcp_server(req: Request) -> any:
    """Handles incoming HTTPS requests by passing them to the FastAPI app via Mangum.

    Manually constructs an AWS API Gateway V1 event dictionary for Mangum.
    """
    # Ensure an asyncio event loop exists for the current thread
    try:
        loop = asyncio.get_event_loop_policy().get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        print("Created new asyncio event loop for this thread.")

    # Manually construct an event dictionary resembling AWS API Gateway v1 format
    try:
        query_string = urllib.parse.urlencode(req.args)
        body = req.get_data()
        is_base64_encoded = False
        try:
            # Attempt to decode as UTF-8. If it fails, assume binary and base64 encode.
            body_str = body.decode('utf-8')
        except UnicodeDecodeError:
            body = base64.b64encode(body)
            body_str = body.decode('utf-8')
            is_base64_encoded = True

        # Process multi-value headers correctly by iterating over headers
        multi_value_headers_dict = {}
        for k, v in req.headers:
            # Normalize header keys to lowercase for consistency
            key_lower = k.lower()
            if key_lower not in multi_value_headers_dict:
                multi_value_headers_dict[key_lower] = []
            multi_value_headers_dict[key_lower].append(v)

        # Use the lowercase version for single-value headers as well for consistency
        single_value_headers_dict = {k.lower(): v for k, v in req.headers}

        event = {
            "httpMethod": req.method,
            "path": req.path,
            "queryStringParameters": req.args.to_dict(), # Simple dict for single values
            "headers": single_value_headers_dict, # Simple dict with lowercase keys
            "body": body_str,
            "isBase64Encoded": is_base64_encoded,
            # Minimal required context keys (might need more for complex apps)
            "requestContext": {
                "httpMethod": req.method,
                "path": req.path,
                "requestId": "firebase-function-invocation-" + str(uuid.uuid4()), # More unique ID
                "stage": "prod", # Dummy value
                "apiId": "dummyApiId", # Dummy value
                # Add source IP if available and non-internal
                "identity": {
                    "sourceIp": req.remote_addr if req.remote_addr else "127.0.0.1"
                }
            },
            "multiValueQueryStringParameters": {k: vlist for k, vlist in req.args.lists()},
            "multiValueHeaders": multi_value_headers_dict, # Use the correctly processed dict
            "resource": req.path, # Set resource to match the actual path
            "pathParameters": None, # Assuming no path parameters captured by Firebase Function trigger
        }

        # Minimal context object (often empty is fine)
        context = {}

        # Call Mangum handler
        response_data = handler(event, context)

        # Convert Mangum's response dict back to a Firebase/Flask Response object
        response_headers = response_data.get("headers", {})
        if "multiValueHeaders" in response_data:
            flat_headers = {}
            for key, values in response_data["multiValueHeaders"].items():
                # Use the last value for simplicity, matching typical WSGI behavior
                if values:
                    flat_headers[key] = values[-1]
            response_headers = flat_headers # Use the flattened headers

        response_body = response_data.get("body", "")
        if response_data.get("isBase64Encoded", False):
            # Decode body if Mangum base64 encoded it
            response_body = base64.b64decode(response_body).decode('utf-8')

        return {
            "statusCode": response_data.get("statusCode", 500),
            "headers": response_headers,
            "body": response_body,
        }

    except Exception as e:
        # Log the detailed error for debugging
        import traceback
        print(f"Error constructing event or calling handler: {e}")
        traceback.print_exc()
        # Return a generic 500 error
        from flask import Response
        return Response("Internal Server Error", status=500)

# Storage trigger placeholder - Removed