"""
Utility functions for database operations to eliminate code duplication.
"""
import time
from typing import Any, Dict, List, Optional
from .logger import logger


async def timed_database_operation(operation_name: str, operation_func, *args, **kwargs):
    """Execute a database operation with timing and logging"""
    start_time = time.time()
    
    try:
        result = await operation_func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        logger.info(f"{operation_name} completed successfully", 
                   execution_time=f"{execution_time:.3f}s",
                   operation=operation_name)
        
        return result, execution_time
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"{operation_name} failed", 
                   execution_time=f"{execution_time:.3f}s",
                   operation=operation_name,
                   error=str(e))
        raise


async def batch_database_operations(operations: List[Dict[str, Any]]):
    """Execute multiple database operations with timing and return results with timing data"""
    results = {}
    total_time = 0
    
    for operation in operations:
        name = operation['name']
        func = operation['func']
        args = operation.get('args', [])
        kwargs = operation.get('kwargs', {})
        
        try:
            result, execution_time = await timed_database_operation(name, func, *args, **kwargs)
            results[name] = {
                'result': result,
                'execution_time': execution_time,
                'success': True
            }
            total_time += execution_time
            
        except Exception as e:
            results[name] = {
                'result': None,
                'execution_time': 0,
                'success': False,
                'error': str(e)
            }
    
    return results, total_time


def format_timing_metrics(operation_results: Dict[str, Any]) -> Dict[str, str]:
    """Format timing metrics for logging"""
    metrics = {}
    
    for operation_name, result in operation_results.items():
        if result['success']:
            metrics[f"{operation_name}_time"] = f"{result['execution_time']:.3f}s"
        else:
            metrics[f"{operation_name}_time"] = "failed"
    
    return metrics


async def safe_database_operation(operation_name: str, operation_func, 
                                fallback_value=None, *args, **kwargs):
    """Execute a database operation with fallback value if it fails"""
    try:
        result, execution_time = await timed_database_operation(operation_name, operation_func, *args, **kwargs)
        return result, execution_time, True
    except Exception as e:
        logger.warning(f"{operation_name} failed, using fallback value: {e}")
        return fallback_value, 0, False


async def validate_user_exists(database, user_id: str, username: str, 
                             create_if_missing: bool = True):
    """Validate user exists and create if missing"""
    user = await database.get_user(user_id)
    
    if not user and create_if_missing:
        await database.upsert_user(user_id, username)
        user = await database.get_user(user_id)
        logger.info(f"User created/updated during operation", 
                   user_id=user_id, 
                   username=username)
    
    return user


async def get_user_stats(database, user_id: str):
    """Get comprehensive user statistics in a single operation"""
    operations = [
        {'name': 'get_user', 'func': database.get_user, 'args': [user_id]},
        {'name': 'get_total_sand', 'func': database.get_user_total_sand, 'args': [user_id]},
        {'name': 'get_paid_sand', 'func': database.get_user_paid_sand, 'args': [user_id]}
    ]
    
    results, total_time = await batch_database_operations(operations)
    
    return {
        'user': results['get_user']['result'],
        'total_sand': results['get_total_sand']['result'],
        'paid_sand': results['get_paid_sand']['result'],
        'timing': results,
        'total_time': total_time
    }
