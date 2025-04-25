import time

print("Step 1 complete", flush=True)
time.sleep(1)
raise Exception("Test1 failed: Simulated error.")
