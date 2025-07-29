import asyncio
import os
import json
import time
import uuid
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
import openai
from agents.models import Agent
from django.conf import settings
from asgiref.sync import sync_to_async  # Add this import

# In-memory store for async requests
request_store = {}
TIMEOUT_SECONDS = 120  # 2 minutes timeout
CLEANUP_INTERVAL = 60  # Check for expired requests every minute

# Wrap database queries with sync_to_async
get_agent = sync_to_async(Agent.objects.get)

async def is_authenticated(request):
    return await sync_to_async(lambda: request.user.is_authenticated)()

async def cleanup_expired_requests():
    """Periodically clean up expired requests to prevent memory leaks"""
    while True:
        try:
            current_time = time.time()
            expired_ids = []
            
            for request_id, data in list(request_store.items()):
                # Check if request has timed out
                if current_time - data.get('timestamp', 0) > TIMEOUT_SECONDS:
                    expired_ids.append(request_id)
            
            # Remove expired requests
            for request_id in expired_ids:
                request_store[request_id] = {
                    'status': 'error',
                    'reply': f'Request timed out after {TIMEOUT_SECONDS} seconds',
                    'timestamp': current_time  # Update timestamp so it can be retrieved once
                }
                
            # Wait before next cleanup
            await asyncio.sleep(CLEANUP_INTERVAL)
        except Exception as e:
            print(f"Error in cleanup task: {e}")
            await asyncio.sleep(CLEANUP_INTERVAL)

async def process_openai_request_async(request_id, message, assistant_id, vector_store_id, api_key):
    """Process OpenAI request asynchronously"""
    # Use a thread pool executor since OpenAI's SDK is synchronous
    loop = asyncio.get_event_loop()
    
    def run_openai_call():
        try:
            client = openai.OpenAI(api_key=api_key, default_headers={"OpenAI-Beta": "assistants=v2"})
            thread = client.beta.threads.create()
            
            assistant = client.beta.assistants.update(
                assistant_id=assistant_id,
                tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
            )
            
            message_obj = client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=message
            )
            
            run = client.beta.threads.runs.create_and_poll(
              thread_id=thread.id, assistant_id=assistant_id
            )
            
            messages = client.beta.threads.messages.list(
                thread_id=thread.id
            )
            
            return {
                'status': 'completed',
                'reply': messages.data[0].content[0].text.value,
                'timestamp': time.time()
            }
        except Exception as e:
            return {
                'status': 'error',
                'reply': f"Error: {str(e)}",
                'timestamp': time.time()
            }
    
    # Run the synchronous OpenAI call in a thread pool
    result = await loop.run_in_executor(None, run_openai_call)
    request_store[request_id] = result

@csrf_exempt
@require_POST
async def chat_async(request):
    """Async API endpoint for chat interaction"""
    # Parse request data
    try:
        data = json.loads(request.body)
        user_message = data.get('message')
        agent_name = data.get('agent_name')
        assistant_id = data.get('assistant_id')
        vector_store_id = data.get('vector_store')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    # Validate required fields
    if not all([user_message, agent_name, assistant_id, vector_store_id]):
        return JsonResponse({'error': 'Missing required fields'}, status=400)
    
    # Check agent access permissions - use sync_to_async for database access
    try:
        # Use sync_to_async to get the agent
        agent = await get_agent(name=agent_name)
        user_authenticated = await is_authenticated(request)
        if not agent.public and not user_authenticated:
            return JsonResponse({'error': 'Authentication required for this agent'}, status=403)
    except Agent.DoesNotExist:
        return JsonResponse({'error': 'Agent not found'}, status=404)
    
    # Generate unique ID for this request
    request_id = str(uuid.uuid4())
    current_time = time.time()
    
    # Store with timestamp
    request_store[request_id] = {
        'status': 'processing',
        'timestamp': current_time
    }
    
    # Start the async processing task without awaiting completion
    oai_key = os.environ.get("OPENAI_API_KEY", "")
    asyncio.create_task(
        process_openai_request_async(
            request_id, 
            user_message, 
            assistant_id, 
            vector_store_id, 
            oai_key
        )
    )
    
    # Return immediately with the request ID
    return JsonResponse({'request_id': request_id})

@require_GET
async def check_status_async(request):
    """Check the status of an async chat request"""
    request_id = request.GET.get('request_id')
    
    if not request_id or request_id not in request_store:
        return JsonResponse({'error': 'Invalid or expired request ID'}, status=404)
    
    result = request_store[request_id]
    
    if result['status'] in ['completed', 'error']:
        # Return the result and clean up
        response_data = {
            'status': result['status'],
            'reply': result['reply']
        }
        # Keep the result for a short time before deleting to handle page reloads
        asyncio.create_task(delete_after_delay(request_id))
        return JsonResponse(response_data)
    else:
        # Still processing
        return JsonResponse({'status': 'processing'})

@csrf_exempt
@require_POST
async def cancel_request(request):
    """Cancel an in-progress request"""
    try:
        data = json.loads(request.body)
        request_id = data.get('request_id')
        
        if request_id in request_store:
            request_store[request_id] = {
                'status': 'cancelled',
                'reply': 'Request was cancelled by the user',
                'timestamp': time.time()
            }
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

async def delete_after_delay(request_id, delay=30):
    """Delete a request from the store after a delay to handle page reloads"""
    await asyncio.sleep(delay)
    if request_id in request_store:
        del request_store[request_id]

# Start the cleanup task
def start_cleanup_task():
    try:
        asyncio.create_task(cleanup_expired_requests())
    except RuntimeError:
        # If there's no running event loop, we're probably in a synchronous context
        # The task will be started by the AppConfig.ready method instead
        pass
        
# Try to start the cleanup task, but don't worry if it fails
start_cleanup_task()