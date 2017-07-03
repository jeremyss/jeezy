#!/home/jscholz/PycharmProjects/VirtEnv/bin/python3.5
import datetime
import argparse
import getpass
import pexpect
import time

_author__ = "Jeremy Scholz"

parser = argparse.ArgumentParser(description='Remote networking device command processor')
parser.add_argument('-v', action='store_true', help='Output results to terminal')
parser.add_argument('-host', type=str, help='Host(s) to run command on, separate multiple hosts with comma')
parser.add_argument('-command', type=str,
                    help='Command(s) to run enclosed in \'\', separate multiple commands with comma')
args = parser.parse_args()

command = []
hostList = []
exCommands = []
commands = ''
hosts = ''
failedhosts = []
now = datetime.datetime.now()
currentDate = now.strftime('%m-%d-%Y')
currentTime = now.strftime('%H-%M-%S')
timestamp = currentDate + "-" + currentTime
filesSaved = []

def _run_command(prompt, command, results, lineHost, session):
    output = str()
    output += '\n' + '*'*30 + '\n' + 'Host -> ' + lineHost.strip() \
              + '\nCommand -> ' + command + '\nPrompt -> ' + prompt + '\n\n'
    session.sendline(command)
    time.sleep(2)
    session.expect(prompt + r'>.*|#.*', timeout=120)
    output += session.before.decode("utf-8")
    if args.v:
        print(output)
    results.write(output)

username = input("Enter your username: ")
password = getpass.getpass("Enter your password: ")

if not args.command:
    commands = input("Enter commands list filename: ")
if not args.host:
    hosts = input("Enter hosts filename: ")

print("Username: {user}".format(user=username))
if args.command:
    print("Input commands: {command}".format(command=args.command))
else:
    print("Input commands file: {inputcommands}".format(inputcommands=commands))
if args.host:
    print("Host list: {hostlist}".format(hostlist=args.host))
else:
    print("Host file: {hostfile}".format(hostfile=hosts))
runScript = input("script will run with the above configuration... procede? Y/N: ")
runScript = str.lower(runScript)

if runScript == "y":
    # read commands into list
    if args.command:
        exCommands = args.command.split(',')
    else:
        try:
            with open (commands, 'r') as exCommands:
                exCommands = exCommands.read().splitlines()
        except IOError:
            print("ERROR::File not found {commandserror}".format(commandserror=commands))
            exit(0)
    # read hosts into list
    if args.host:
        hostList = args.host.split(',')
    else:
        try:
            with open (hosts, 'r') as hostList:
                hostList = hostList.read().splitlines()
        except IOError:
            print("ERROR::File not found {hostserror}".format(hostserror=hosts))
            exit(0)
    for lineHost in hostList:
        print("Running commands for {currenthost}...please wait".format(currenthost=lineHost.strip()))
        try:
            session = pexpect.spawn(
                "ssh -l " + username + " -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "
                "-o PubkeyAuthentication=no " + lineHost.strip(), timeout=5, maxread=65535)
            session.expect('.*assword.')
            session.sendline(password)
            session.expect(r'>.*')
        except:
            print("Unable to connect to {host} using ssh... trying telnet".format(host=lineHost.strip()))
            try:
                session = pexpect.spawn("telnet " + lineHost.strip(), timeout=5, maxread=65535)
                session.expect('sername.')
                session.sendline(username)
                session.expect('.*assword.')
                session.sendline(password)
                session.expect(r'>.*')
            except:
                print("Unable to connect to {host} using telnet... giving up\n".format(host=lineHost.strip()))
                failedhosts.append(lineHost.strip())
                continue
        filesSaved.append(lineHost.strip() + "-" + timestamp)
        results = open(lineHost.strip() + "-" + timestamp, 'w')
        session.sendline("set cli screen-length 0")
        session.expect(r'>.*')
        prompt = session.before
        prompt = prompt.decode("utf-8")
        promptnew = prompt.split('\n')
        prompt = str(promptnew[-1])
        for lineCommand in exCommands:
            _run_command(prompt, lineCommand, results, lineHost, session)
        session.sendline("exit")
        output = '\n' + '*'*30 + '\n' + '*'*11 + 'complete' + '*'*11 + '\n' + '*'*30 + '\n'
        if args.v:
            print(output)
        results.write(output)
        results.close()
    if len(filesSaved) > 0:
        if len(hostList) > 1:
            print("\nFiles saved to\n")
        else:
            print("\nFile saved to\n")
        for i in filesSaved:
            print(i)
    if len(failedhosts) > 0:
        print("Unable to connect to the following hosts:\n")
        for failed in failedhosts:
            print("{fhost}".format(fhost=failed))
else:
    exit(0)
