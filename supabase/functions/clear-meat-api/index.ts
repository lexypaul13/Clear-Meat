import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const PYTHON_API_URL = Deno.env.get('PYTHON_API_URL') || 'https://clear-meat-api-production.up.railway.app'

serve(async (req) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response('ok', {
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      },
    })
  }

  try {
    const url = new URL(req.url)
    const path = url.pathname.replace('/functions/v1/clear-meat-api', '') || '/'
    
    // Proxy all requests to Python API
    const targetUrl = `${PYTHON_API_URL}${path}${url.search}`
    
    // Only forward essential headers, completely skip auth headers
    const cleanHeaders = new Headers()
    cleanHeaders.set('Content-Type', 'application/json')
    cleanHeaders.set('Accept', 'application/json')
    
    // Get request body if it exists
    let body = null
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      body = await req.text()
    }
    
    const response = await fetch(targetUrl, {
      method: req.method,
      headers: cleanHeaders,
      body: body,
    })
    
    const responseBody = await response.text()
    
    return new Response(responseBody, {
      status: response.status,
      headers: {
        ...Object.fromEntries(response.headers.entries()),
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      },
    })
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    })
  }
})