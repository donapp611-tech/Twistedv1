import time
import turtle

print("click enter to start...")
input()  
print("big.py is now running.")
time.sleep(1)
run_code = input("run code:(yes/no)")
if run_code.lower() == "yes":
    print("Running code...")
    code_to_run = input("Enter code to run:")
    if input("Run the code? (yes/no)").lower() == "yes":
        exec(code_to_run)
    else:
        print("waiting for next command...")
else:
    print("Code execution skipped.")
current_time = time.time()
print(f"Current time: converted to human-readable format: {time.ctime(current_time)}")
if current_time:
    print("Time printed")
input()
display = turtle.Screen()
display.title("Turtle Graphics")
display.bgcolor("lightyellow")
display.setup(width=800, height=600)
head = turtle.Turtle()
head.shape("turtle")
head.color("blue")
head.speed(2)
head.forward(100)
head.left(90)
head.forward(100)
head.left(90)
head.forward(100)
head.left(90)
head.forward(100)
turtle.done()