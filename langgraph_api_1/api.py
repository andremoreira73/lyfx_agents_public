from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import asyncio
import uuid
from asgiref.sync import sync_to_async

from .models import Thread, Message, Run
from .agent_registry import get_agent_executor, list_available_agents

import logging

logger = logging.getLogger(f'langgraph_api_1.api')

# Helper functions for async DB operations
get_thread = sync_to_async(lambda id: Thread.objects.get(id=id))
create_thread = sync_to_async(Thread.objects.create)
create_message = sync_to_async(Message.objects.create)
get_run = sync_to_async(lambda id: Run.objects.get(id=id))
create_run = sync_to_async(Run.objects.create)
get_messages = sync_to_async(lambda thread_id: list(Message.objects.filter(thread_id=thread_id).order_by('created_at')))


# =============================================================================
# CORE API ENDPOINTS
# =============================================================================

@csrf_exempt
async def threads(request):
    """Create or list threads"""
    if request.method == 'POST':
        data = json.loads(request.body)
        thread_obj = await create_thread(metadata=data.get('metadata', {}))
        
        return JsonResponse({
            'id': str(thread_obj.id),
            'created_at': thread_obj.created_at.isoformat(),
            'metadata': thread_obj.metadata,
            'object': 'thread'
        })
    
    elif request.method == 'GET':
        threads_list = await sync_to_async(list)(Thread.objects.all().order_by('-created_at'))
        return JsonResponse({
            'data': [{
                'id': str(t.id),
                'created_at': t.created_at.isoformat(),
                'metadata': t.metadata,
                'object': 'thread'
            } for t in threads_list],
            'object': 'list'
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
async def thread_messages(request, thread_id):
    """Create or list messages in a thread"""
    try:
        thread_obj = await get_thread(thread_id)
    except Thread.DoesNotExist:
        return JsonResponse({'error': 'Thread not found'}, status=404)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        message = await create_message(
            thread=thread_obj,
            role=data.get('role', 'user'),
            content=data.get('content', ''),
            metadata=data.get('metadata', {})
        )
        
        return JsonResponse(await sync_to_async(message.to_dict)())
    
    elif request.method == 'GET':
        messages = await get_messages(thread_id)
        return JsonResponse({
            'data': [await sync_to_async(msg.to_dict)() for msg in messages],
            'object': 'list'
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
async def thread_runs(request, thread_id):
    """Create a run for a thread"""
    try:
        thread_obj = await get_thread(thread_id)
    except Thread.DoesNotExist:
        return JsonResponse({'error': 'Thread not found'}, status=404)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        assistant_id = data.get('assistant_id', 'default')
        
        # Create the run object
        run = await create_run(
            thread=thread_obj,
            assistant_id=assistant_id,
            metadata=data.get('metadata', {})
        )
        
        # Start execution in background
        asyncio.create_task(execute_run(run.id, thread_id, assistant_id))
        
        return JsonResponse({
            'id': str(run.id),
            'thread_id': thread_id,
            'assistant_id': assistant_id,
            'status': 'queued',
            'created_at': run.created_at.isoformat(),
            'object': 'run'
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# =============================================================================
# SIMPLIFIED EXECUTION LOGIC
# =============================================================================

async def execute_run(run_id, thread_id, assistant_id):
    """Execute a LangGraph agent run - SIMPLIFIED"""
    logger.info(f"Starting execution of run {run_id} for thread {thread_id} with assistant {assistant_id}")
    
    try:
        run = await get_run(run_id)
        run.status = 'in_progress'
        await sync_to_async(run.save)()
        
        thread_obj = await get_thread(thread_id)
        
        # Get ALL messages (both user and assistant) for context
        all_messages = await get_messages(thread_id)
        
        # Prepare initial state with all messages
        initial_state = {
            "messages": [{'role': msg.role, 'content': msg.content} for msg in all_messages]
        }
        
        logger.info(f"Prepared initial state with {len(all_messages)} messages")
        
        # Get the agent executor
        agent_executor = get_agent_executor(assistant_id)
        if not agent_executor:
            raise ValueError(f"Unknown assistant_id: {assistant_id}")
        
        # Execute the agent
        logger.info("Executing agent workflow")
        result = await sync_to_async(agent_executor.execute)(
            initial_state=initial_state,
            thread_id=str(thread_id)
        )
        
        # Handle result - SIMPLIFIED
        if result.get("status") == "interrupted":
            logger.info("Agent workflow interrupted")
            
            # Extract assistant message
            interrupt_message = result["interrupt_data"]["message"]
            if isinstance(interrupt_message, list) and len(interrupt_message) > 0:
                message_content = interrupt_message[0].get('content', '')
            else:
                message_content = str(interrupt_message)
            
            # Create assistant message
            await create_message(
                thread=thread_obj,
                role='assistant',
                content=message_content,
                metadata={'awaiting_input': True}
            )
            
            # Update run status
            run.status = 'requires_action'
            await sync_to_async(run.save)()
            
            logger.info(f"Run {run_id} interrupted, awaiting user input")
            
        else:
            logger.info("Agent workflow completed")
            
            # Handle completion
            completion_message = result["interrupt_data"]["message"]
            #completion_message = result.get("final_message", "Workflow completed")
            
            await create_message(
                thread=thread_obj,
                role='assistant',
                content=completion_message,
                metadata={'awaiting_input': False}
            )
            
            run.status = 'completed'
            await sync_to_async(run.save)()
            
    except Exception as e:
        logger.error(f"Error in execute_run: {e}")
        run = await get_run(run_id)
        run.status = 'failed'
        run.metadata = {'error': str(e)}
        await sync_to_async(run.save)()


@csrf_exempt
async def submit_tool_outputs(request, run_id):
    """Resume an interrupted run with user input - SIMPLIFIED"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        run = await get_run(run_id)
    except Run.DoesNotExist:
        return JsonResponse({'error': 'Run not found'}, status=404)
    
    if run.status != 'requires_action':
        return JsonResponse({'error': 'Run is not waiting for input'}, status=400)
    
    # Extract user input
    data = json.loads(request.body)
    tool_outputs = data.get('tool_outputs', [])
    
    if not tool_outputs:
        return JsonResponse({'error': 'Missing tool_outputs'}, status=400)
    
    user_input = tool_outputs[0].get('content', '')
    if not user_input:
        return JsonResponse({'error': 'Missing user input content'}, status=400)
    
    # Add user message to thread
    thread_obj = await sync_to_async(lambda: run.thread)()
    await create_message(
        thread=thread_obj,
        role='user',
        content=user_input,
        metadata={}
    )
    
    # Resume execution
    try:
        agent_executor = get_agent_executor(run.assistant_id)
        if not agent_executor:
            return JsonResponse({'error': f'Unknown assistant: {run.assistant_id}'}, status=400)
        
        result = await sync_to_async(agent_executor.resume)(
            user_input=user_input,
            thread_id=str(thread_obj.id)
        )
        
        # Handle resume result
        if result.get("status") == "interrupted":
            # Another interrupt
            run.status = 'requires_action'
            await sync_to_async(run.save)()
            
            # Create assistant message
            interrupt_message = result["interrupt_data"]["message"]
            if isinstance(interrupt_message, list) and len(interrupt_message) > 0:
                message_content = interrupt_message[0].get('content', '')
            else:
                message_content = str(interrupt_message)
            
            await create_message(
                thread=thread_obj,
                role='assistant',
                content=message_content,
                metadata={'awaiting_input': True}
            )
            
            logger.info(f"Run {run_id} interrupted again, awaiting more input")
            
        else:
            # Completed
            completion_message = result["interrupt_data"]["message"]
            #completion_message = result.get("final_message", "Workflow completed")
            
            await create_message(
                thread=thread_obj,
                role='assistant',
                content=completion_message,
                metadata={'awaiting_input': False}
            )
            
            run.status = 'completed'
            await sync_to_async(run.save)()
            
            logger.info(f"Run {run_id} completed successfully")
            
    except Exception as e:
        logger.error(f"Error during resume: {e}")
        run.status = 'failed'
        run.metadata = {'error': str(e)}
        await sync_to_async(run.save)()
    
    return JsonResponse(await sync_to_async(run.to_dict)())


# =============================================================================
# SIMPLIFIED SSE STREAMING
# =============================================================================

async def run_events(request, thread_id, run_id):
    """Stream run events using Server-Sent Events - OPTIMIZED"""
    try:
        run = await get_run(run_id)
    except Run.DoesNotExist:
        return JsonResponse({'error': 'Run not found'}, status=404)
    
    async def event_stream():
        logger.info(f"Starting SSE stream for thread {thread_id}, run {run_id}")
        
        try:
            # Only send RECENT messages (last 5) to avoid overwhelming the stream
            existing_messages = await get_messages(thread_id)
            recent_messages = existing_messages[-5:] if len(existing_messages) > 5 else existing_messages
            
            logger.info(f"Sending {len(recent_messages)} recent messages (out of {len(existing_messages)} total)")
            
            for msg in recent_messages:
                msg_dict = await sync_to_async(msg.to_dict)()
                yield f"data: {json.dumps({'type': 'message.created', 'data': msg_dict})}\n\n"
            
            # Send initial run status
            current_run = await get_run(run_id)
            yield f"data: {json.dumps({'type': 'run.status', 'data': {'status': current_run.status}})}\n\n"
            
            # Track state for changes
            previous_status = current_run.status
            previous_msg_count = len(existing_messages)
            
            # Polling loop - simple and reliable
            for _ in range(600):  # 5 minutes max (600 * 0.5s)
                await asyncio.sleep(0.5)
                
                try:
                    # Check run status
                    current_run = await get_run(run_id)
                    if current_run.status != previous_status:
                        yield f"data: {json.dumps({'type': 'run.status', 'data': {'status': current_run.status}})}\n\n"
                        previous_status = current_run.status
                    
                    # Check for new messages
                    current_messages = await get_messages(thread_id)
                    if len(current_messages) > previous_msg_count:
                        new_messages = current_messages[previous_msg_count:]
                        
                        for msg in new_messages:
                            msg_dict = await sync_to_async(msg.to_dict)()
                            yield f"data: {json.dumps({'type': 'message.created', 'data': msg_dict})}\n\n"
                        
                        previous_msg_count = len(current_messages)
                    
                    # Exit if run is finished
                    if current_run.status in ['completed', 'failed', 'cancelled']:
                        logger.info(f"Run finished with status: {current_run.status}")
                        break
                        
                except Exception as e:
                    logger.error(f"Error in SSE loop: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"
                    break
            
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"
    
    return StreamingHttpResponse(
        event_stream(),
        content_type="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }
    )



# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

async def api_info(request):
    """Get API info"""
    return JsonResponse({
        'name': 'LangGraph API',
        'version': '1.0.0',
        'supported_assistants': list(list_available_agents().keys()),
        'endpoints': [
            'threads',
            'threads/{thread_id}/messages',
            'threads/{thread_id}/runs',
            'runs/{run_id}/submit_tool_outputs'
        ]
    })


async def run_detail(request, thread_id, run_id):
    """Get run details"""
    try:
        run = await get_run(run_id)
    except Run.DoesNotExist:
        return JsonResponse({'error': 'Run not found'}, status=404)
    
    return JsonResponse(await sync_to_async(run.to_dict)())