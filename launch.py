import subprocess
import threading

def run_fastapi():
    subprocess.run(["uvicorn", "ai_tutor_platform.main_api:app", "--port", "8000", "--reload"])

def run_streamlit():
    subprocess.run(["streamlit", "run", "ai_tutor_platform/main.py"])

if __name__ == "__main__":
    t1 = threading.Thread(target=run_fastapi)
    t2 = threading.Thread(target=run_streamlit)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
