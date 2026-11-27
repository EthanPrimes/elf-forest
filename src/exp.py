# import sys
# import select
# import subprocess
# floor = 0.0
# timeout = 1.0
# while True:
#     rlist, wlist, xlist = select.select([sys.stdin], [], [], timeout)
#     if len(rlist):
#         floor = float(sys.stdin.readline().rstrip('\n'))
#         print('New value received.')
#     subprocess.run(["clear; clear"], shell=True)
#     print(floor)

print("\033[42m \033[0m\033[43m \033[0m\033[42mT\033[0m")
print("\033[38;5;206m     #That is, \033[38;5;<FG COLOR>m\033[0m")
print("\033[48;2;139;69;19m mud! \033[0m")
