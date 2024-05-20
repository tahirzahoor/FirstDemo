from celery import Celery
from celery.utils.log import get_task_logger
from datetime import datetime
import requests
# from background_task import background
logger = get_task_logger(__name__)
app = Celery('tasks', broker='redis://localhost:6379/0')

@app.task
def perform_action():
    # Perform your action here
    logger.info('Action performed at %s', datetime.now())
    
    # # Example: Call your API endpoint
    # response = requests.get('http://127.0.0.1:8000/your-api-endpoint/')
    # if response.status_code == 200:
    #     logger.info('API call successful')
    # else:
    #     logger.error('API call failed: %s', response.text)





# @background(schedule=60)  # Schedule the task to run every 60 seconds
# def my_scheduled_task():
#     # Your task code goes here
#     print("Executing scheduled task now...")
#     logger.info('Action performed at %s', datetime.now())
    
#     # This function will be executed at the scheduled time