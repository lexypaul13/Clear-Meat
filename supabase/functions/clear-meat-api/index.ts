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
    let path = url.pathname
    
    // Handle multiple possible path prefixes
    const prefixes = ['/functions/v1/clear-meat-api', '/clear-meat-api']
    for (const prefix of prefixes) {
      if (path.startsWith(prefix)) {
        path = path.substring(prefix.length)
        break
      }
    }
    
    // Ensure path starts with /
    if (!path.startsWith('/')) {
      path = '/' + path
    }
    
    // If path is just /, default to /health
    if (path === '/') {
      path = '/health'
    }
    
    // Proxy all requests to Python API
    const targetUrl = `${PYTHON_API_URL}${path}${url.search}`
    
    // Log for debugging
    console.log('Edge Function Request:', {
      method: req.method,
      originalPath: url.pathname,
      processedPath: path,
      targetUrl: targetUrl,
    })
    
    // Forward more headers while filtering sensitive ones
    const headersToSkip = ['host', 'authorization', 'x-supabase-auth']
    const cleanHeaders = new Headers()
    
    // Add essential headers
    cleanHeaders.set('Accept', 'application/json')
    
    // Forward other safe headers from the request
    for (const [key, value] of req.headers.entries()) {
      const lowerKey = key.toLowerCase()
      if (!headersToSkip.includes(lowerKey)) {
        cleanHeaders.set(key, value)
      }
    }
    
    // Ensure content-type is set for requests with body
    if (req.method !== 'GET' && req.method !== 'HEAD' && !cleanHeaders.has('content-type')) {
      cleanHeaders.set('Content-Type', 'application/json')
    }
    
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
    
    // Log response status for debugging
    console.log('Edge Function Response:', {
      status: response.status,
      targetUrl: targetUrl,
    })
    
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
    console.error('Edge Function Error:', error)
    return new Response(JSON.stringify({ error: error.message, detail: 'Edge function error' }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    })
  }
})