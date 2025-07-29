"""
Simple checkpoint cleanup: Delete threads inactive for more than 7 days
Usage: python cleanup_checkpoints.py [max_days_inactive]
"""

import sqlite3
import sys
import os
import msgpack
from datetime import datetime, timedelta


DB_PATH_GLOBAL = "./checkpoints.sqlite"


def cleanup_old_threads(max_days_inactive=7):
    """Delete entire threads that haven't been active for max_days_inactive days"""
    
    db_path = DB_PATH_GLOBAL
    
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return
    
    cutoff_date = datetime.now() - timedelta(days=max_days_inactive)
    
    print(f"Deleting threads with no activity since {cutoff_date.strftime('%Y-%m-%d')}")
    print(f"Database: {db_path}")
    
    try:
        with sqlite3.connect(db_path) as conn:
            # Count before cleanup
            cursor = conn.execute("SELECT COUNT(*) FROM checkpoints")
            before_checkpoints = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(DISTINCT thread_id) FROM checkpoints")
            before_threads = cursor.fetchone()[0]
            
            print(f"Before cleanup:")
            print(f"  Total checkpoints: {before_checkpoints}")
            print(f"  Total threads: {before_threads}")
            
            # Find threads to delete by checking their most recent activity
            cursor = conn.execute("""
                SELECT thread_id, checkpoint 
                FROM checkpoints 
                WHERE checkpoint_id IN (
                    SELECT MAX(checkpoint_id) 
                    FROM checkpoints 
                    GROUP BY thread_id
                )
            """)
            
            threads_to_delete = []
            
            for thread_id, checkpoint_blob in cursor.fetchall():
                try:
                    # Extract timestamp from msgpack
                    decoded = msgpack.unpackb(checkpoint_blob, raw=False)
                    ts_str = decoded.get('ts', '')
                    if ts_str:
                        last_activity = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        if last_activity < cutoff_date:
                            threads_to_delete.append(thread_id)
                except:
                    # If we can't parse the timestamp, consider it old
                    threads_to_delete.append(thread_id)
            
            print(f"Found {len(threads_to_delete)} inactive threads to delete")
            
            # Delete inactive threads
            if threads_to_delete:
                placeholders = ','.join(['?' for _ in threads_to_delete])
                
                # Delete checkpoints
                cursor = conn.execute(f"""
                    DELETE FROM checkpoints 
                    WHERE thread_id IN ({placeholders})
                """, threads_to_delete)
                deleted_checkpoints = cursor.rowcount
                
                # Delete associated writes
                cursor = conn.execute("""
                    DELETE FROM writes 
                    WHERE checkpoint_id NOT IN (SELECT checkpoint_id FROM checkpoints)
                """)
                deleted_writes = cursor.rowcount
                
                print(f"Deleted {deleted_checkpoints} checkpoints")
                print(f"Deleted {deleted_writes} writes")
            else:
                print("No inactive threads found")
            
            # Count after cleanup (before vacuum)
            cursor = conn.execute("SELECT COUNT(*) FROM checkpoints")
            after_checkpoints = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(DISTINCT thread_id) FROM checkpoints")
            after_threads = cursor.fetchone()[0]
            
        # Vacuum outside the transaction to reclaim space
        with sqlite3.connect(db_path) as conn:
            conn.execute("VACUUM")
            
            print(f"After cleanup:")
            print(f"  Total checkpoints: {after_checkpoints}")
            print(f"  Total threads: {after_threads}")
            print(f"  Threads deleted: {len(threads_to_delete)}")
            
    except Exception as e:
        print(f"Error during cleanup: {e}")
        sys.exit(1)

def show_stats():
    """Show current database statistics"""
    
    db_path = DB_PATH_GLOBAL
    
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM checkpoints")
            total_checkpoints = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(DISTINCT thread_id) FROM checkpoints")
            total_threads = cursor.fetchone()[0]
            
            print(f"Database Statistics:")
            print(f"  Total checkpoints: {total_checkpoints}")
            print(f"  Total threads: {total_threads}")
            
            if total_threads > 0:
                avg_checkpoints = total_checkpoints / total_threads
                print(f"  Average checkpoints per thread: {avg_checkpoints:.1f}")
                    
    except Exception as e:
        print(f"Error reading database: {e}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "stats":
            show_stats()
        else:
            try:
                max_days = int(sys.argv[1])
                cleanup_old_threads(max_days)
            except ValueError:
                print("Usage: python cleanup_checkpoints.py [max_days_inactive | stats]")
                print("Examples:")
                print("  python cleanup_checkpoints.py 7     # Delete threads inactive for >7 days")
                print("  python cleanup_checkpoints.py 3     # Delete threads inactive for >3 days")
                print("  python cleanup_checkpoints.py stats # Show database statistics")
                sys.exit(1)
    else:
        # Default: delete threads inactive for more than 7 days
        cleanup_old_threads(7)