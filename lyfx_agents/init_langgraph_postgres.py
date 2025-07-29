# lyfx_agents/init_langgraph_postgres.py
"""
Initialize PostgreSQL tables for LangGraph checkpointer on Django startup.
This module ensures the required tables exist for all LangGraph agents.
"""

import logging
from django.conf import settings
from langgraph.checkpoint.postgres import PostgresSaver

logger = logging.getLogger('lyfx_agents.init_langgraph_postgres')


def initialize_langgraph_tables():
    """
    Initialize PostgreSQL tables required for LangGraph checkpointer.
    Uses the official PostgresSaver.setup() method to create tables.
    This is safe to run multiple times - setup() is idempotent.
    """
    try:
        db_settings = settings.DATABASES['default']
        
        # Build the connection string
        DB_URI = f"postgresql://{db_settings['USER']}:{db_settings['PASSWORD']}@{db_settings['HOST']}:{db_settings['PORT']}/{db_settings['NAME']}?sslmode=disable"
        
        logger.info(f"Initializing LangGraph tables in database: {db_settings['NAME']}")
        
        # Use the official setup method
        with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
            checkpointer.setup()
            logger.info("LangGraph PostgreSQL tables initialized successfully")
            
            # Verify by attempting a test operation
            try:
                test_config = {"configurable": {"thread_id": "init-test"}}
                # Try to get a checkpoint (should return None for non-existent)
                checkpoint = checkpointer.get(test_config)
                logger.debug(f"Checkpointer verification successful (test checkpoint: {checkpoint})")
            except Exception as e:
                logger.warning(f"Checkpointer verification failed, but tables may still be OK: {e}")
            
    except Exception as e:
        # Log the error but don't crash Django startup
        logger.error(f"Failed to initialize LangGraph tables: {e}", exc_info=True)
        logger.warning("LangGraph agents may not function properly without these tables")
        # You might want to re-raise here if you want Django to fail fast
        # raise


####################################
def cleanup_old_checkpoints(days=7):
    """
    Optional: Clean up old checkpoints to prevent table bloat.
    Call this periodically (e.g., from a Celery task or cron job).
    
    Note: The PostgresSaver doesn't have a built-in cleanup method,
    so we need to use raw SQL for this maintenance task.
    """
    try:
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                DELETE FROM checkpoints 
                WHERE created_at < NOW() - INTERVAL '%s days'
                RETURNING thread_id
            """, (days,))
            
            deleted_threads = cursor.fetchall()
            deleted_count = len(deleted_threads)
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old checkpoint threads")
                
                # Also clean up orphaned blobs and writes
                cursor.execute("""
                    DELETE FROM checkpoint_blobs 
                    WHERE thread_id NOT IN (
                        SELECT DISTINCT thread_id FROM checkpoints
                    )
                """)
                
                cursor.execute("""
                    DELETE FROM checkpoint_writes 
                    WHERE thread_id NOT IN (
                        SELECT DISTINCT thread_id FROM checkpoints
                    )
                """)
                
    except Exception as e:
        logger.error(f"Failed to cleanup old checkpoints: {e}")


#####################################
def check_langgraph_tables_health():
    """
    Check if LangGraph tables are healthy and accessible.
    Useful for monitoring/health endpoints.
    """
    try:
        db_settings = settings.DATABASES['default']
        DB_URI = f"postgresql://{db_settings['USER']}:{db_settings['PASSWORD']}@{db_settings['HOST']}:{db_settings['PORT']}/{db_settings['NAME']}?sslmode=disable"
        
        with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
            # Try a simple operation
            test_config = {"configurable": {"thread_id": "health-check"}}
            checkpointer.get(test_config)
            return True, "LangGraph tables are healthy"
            
    except Exception as e:
        return False, f"LangGraph tables check failed: {str(e)}"