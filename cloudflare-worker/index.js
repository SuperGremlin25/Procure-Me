/**
 * Cloudflare Worker for PDF Processing Pipeline
 * 
 * This worker:
 * 1. Receives PDF uploads from the frontend
 * 2. Stores them in R2
 * 3. Sends to Mistral OCR API
 * 4. Returns structured JSON
 * 5. Triggers Python backend for GIS processing
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // CORS headers
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    };
    
    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }
    
    // Route handling
    if (url.pathname === '/api/upload-pdf' && request.method === 'POST') {
      return handlePDFUpload(request, env, corsHeaders);
    }
    
    if (url.pathname === '/api/process-gis' && request.method === 'POST') {
      return handleGISProcessing(request, env, corsHeaders);
    }
    
    if (url.pathname === '/api/status' && request.method === 'GET') {
      return handleStatusCheck(request, env, corsHeaders);
    }
    
    return new Response('Not Found', { status: 404, headers: corsHeaders });
  }
};

/**
 * Handle PDF upload and OCR processing
 */
async function handlePDFUpload(request, env, corsHeaders) {
  try {
    const formData = await request.formData();
    const pdfFile = formData.get('pdf');
    const utilityType = formData.get('utility_type') || 'generic';
    
    if (!pdfFile) {
      return new Response(JSON.stringify({ error: 'No PDF file provided' }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
    
    // Generate unique ID for this job
    const jobId = crypto.randomUUID();
    const timestamp = Date.now();
    const filename = `pdfs/${jobId}_${timestamp}.pdf`;
    
    // Store PDF in R2
    const pdfBuffer = await pdfFile.arrayBuffer();
    await env.REMEDY_BUCKET.put(filename, pdfBuffer, {
      httpMetadata: {
        contentType: 'application/pdf'
      },
      customMetadata: {
        jobId: jobId,
        utilityType: utilityType,
        uploadedAt: new Date().toISOString()
      }
    });
    
    // Send to Mistral OCR API
    const ocrResult = await processPDFWithMistral(pdfBuffer, utilityType, env.MISTRAL_API_KEY);
    
    // Store OCR result in R2
    const resultFilename = `results/${jobId}_result.json`;
    await env.REMEDY_BUCKET.put(resultFilename, JSON.stringify(ocrResult), {
      httpMetadata: {
        contentType: 'application/json'
      }
    });
    
    // Store job status in KV
    await env.JOB_STATUS.put(jobId, JSON.stringify({
      status: 'completed',
      jobId: jobId,
      pdfFile: filename,
      resultFile: resultFilename,
      utilityType: utilityType,
      completedAt: new Date().toISOString(),
      totalPoles: ocrResult.total_poles || 0
    }), {
      expirationTtl: 86400 // 24 hours
    });
    
    return new Response(JSON.stringify({
      success: true,
      jobId: jobId,
      result: ocrResult,
      message: 'PDF processed successfully'
    }), {
      status: 200,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    console.error('PDF upload error:', error);
    return new Response(JSON.stringify({
      error: 'Failed to process PDF',
      details: error.message
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Process PDF with Mistral OCR API
 */
async function processPDFWithMistral(pdfBuffer, utilityType, apiKey) {
  const mistralUrl = 'https://api.mistral.ai/v1/ocr/extract';
  
  // Create form data for Mistral
  const formData = new FormData();
  formData.append('file', new Blob([pdfBuffer], { type: 'application/pdf' }), 'remedy.pdf');
  formData.append('extraction_schema', JSON.stringify(getExtractionSchema(utilityType)));
  formData.append('prompt', getExtractionPrompt(utilityType));
  
  const response = await fetch(mistralUrl, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${apiKey}`
    },
    body: formData
  });
  
  if (!response.ok) {
    throw new Error(`Mistral OCR failed: ${response.statusText}`);
  }
  
  const result = await response.json();
  
  // Transform to our standard format
  return {
    utility_company: result.utility_company || utilityType,
    report_date: result.report_date,
    project_area: result.project_area,
    total_poles: result.poles?.length || 0,
    actions: result.poles || [],
    metadata: {
      ocr_confidence: result.confidence,
      processing_time: result.processing_time,
      extracted_at: new Date().toISOString()
    }
  };
}

/**
 * Get extraction schema for Mistral based on utility type
 */
function getExtractionSchema(utilityType) {
  return {
    type: 'object',
    properties: {
      utility_company: { type: 'string' },
      report_date: { type: 'string' },
      project_area: { type: 'string' },
      poles: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            pole_id: { type: 'string' },
            action_type: { type: 'string' },
            attachment_height: { type: 'number' },
            comm_move: { type: 'boolean' },
            pole_replace: { type: 'boolean' },
            notes: { type: 'string' },
            page_number: { type: 'integer' }
          },
          required: ['pole_id', 'action_type']
        }
      }
    },
    required: ['utility_company', 'poles']
  };
}

/**
 * Get extraction prompt for Mistral
 */
function getExtractionPrompt(utilityType) {
  const basePrompt = `
    Extract all utility pole remediation actions from this document.
    For each pole, identify:
    - Pole ID (may contain letters, numbers, hyphens)
    - Required action (ATTACH, DETACH, RELOCATE, REPLACE, INSPECT, MAINTAIN)
    - Attachment height in feet
    - Whether communication move is required
    - Whether pole replacement is required
    - Any additional notes
  `;
  
  const utilitySpecific = {
    'aep': 'AEP reports use codes like MR for make-ready. Extract these codes.',
    'comcast': 'Comcast reports include ticket numbers. Capture these.',
    'att': 'AT&T reports have detailed attachment heights. Extract all height data.',
    'spectrum': 'Spectrum reports include plant codes. Capture these codes.'
  };
  
  return basePrompt + (utilitySpecific[utilityType.toLowerCase()] || '');
}

/**
 * Handle GIS processing request
 * This triggers the Python backend on Render/Railway
 */
async function handleGISProcessing(request, env, corsHeaders) {
  try {
    const body = await request.json();
    const { jobId, shapefileUrl } = body;
    
    if (!jobId || !shapefileUrl) {
      return new Response(JSON.stringify({
        error: 'Missing jobId or shapefileUrl'
      }), {
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
    
    // Get OCR result from R2
    const resultFile = `results/${jobId}_result.json`;
    const ocrData = await env.REMEDY_BUCKET.get(resultFile);
    
    if (!ocrData) {
      return new Response(JSON.stringify({
        error: 'OCR result not found'
      }), {
        status: 404,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      });
    }
    
    const ocrResult = await ocrData.json();
    
    // Call Python backend for GIS processing
    const pythonBackendUrl = env.PYTHON_BACKEND_URL || 'https://your-app.railway.app';
    const response = await fetch(`${pythonBackendUrl}/api/spatial-join`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${env.BACKEND_API_KEY}`
      },
      body: JSON.stringify({
        jobId: jobId,
        remedyData: ocrResult,
        shapefileUrl: shapefileUrl
      })
    });
    
    if (!response.ok) {
      throw new Error(`Backend processing failed: ${response.statusText}`);
    }
    
    const result = await response.json();
    
    // Update job status
    await env.JOB_STATUS.put(jobId, JSON.stringify({
      status: 'gis_processed',
      jobId: jobId,
      gisResult: result,
      processedAt: new Date().toISOString()
    }), {
      expirationTtl: 86400
    });
    
    return new Response(JSON.stringify({
      success: true,
      result: result
    }), {
      status: 200,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
    
  } catch (error) {
    console.error('GIS processing error:', error);
    return new Response(JSON.stringify({
      error: 'Failed to process GIS data',
      details: error.message
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Check job status
 */
async function handleStatusCheck(request, env, corsHeaders) {
  const url = new URL(request.url);
  const jobId = url.searchParams.get('jobId');
  
  if (!jobId) {
    return new Response(JSON.stringify({ error: 'Missing jobId' }), {
      status: 400,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
  
  const status = await env.JOB_STATUS.get(jobId);
  
  if (!status) {
    return new Response(JSON.stringify({ error: 'Job not found' }), {
      status: 404,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    });
  }
  
  return new Response(status, {
    status: 200,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' }
  });
}
