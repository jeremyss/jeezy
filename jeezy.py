#!/home/jscholz/PycharmProjects/VirtEnv/bin/python3.5
import datetime
import argparse
import getpass
import pexpect

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

def _run_command(command, results, lineHost, session):
    output = str()
    prompt = session.before
    promptnew = prompt.split('\n')
    prompt = str(promptnew[-1])
    output += '\n******************************\n' + 'Host -> ' + lineHost.strip() \
              + '\n' + 'Command -> ' + command + '\n\n'
    session.sendline(command)
    session.expect(prompt + r'> $', timeout=120)
    output += session.before
    if args.v:
        print(output)
    results.write(output)

username = input("Enter your username: ")
password = getpass.getpass("Enter your password: ")

if not args.command:
    commands = input("Enter commands list filename: ")
if not args.host:
    hosts = input("Enter hosts filename: ")

print("Username:",username)
if args.command:
    print("Input commands:",args.command)
else:
    print("Input commands file:",commands)
if args.host:
    print("Host list:",args.host)
else:
    print("Host file:",hosts)
runScript = input("script will run with the above configuration... procede? Y/N: ")
runScript = str.lower(runScript)

if runScript == "y":
    # read commands into list
    if args.command:
        exCommands = args.command.split(',')
    else:
        try:
            commandsFile = open(commands, 'r')
            exCommands = commandsFile.readlines()
            exCommands = map(lambda s: s.strip(), exCommands)
            commandsFile.close()
        except IOError:
            print("ERROR::File not found",commands)
            exit(0)
    # read hosts into list
    if args.host:
        hostList = args.host.split(',')
    else:
        try:
            hostsFile = open(hosts, 'r')
            hostList = hostsFile.readlines()
            hostsFile.close()
        except IOError:
            print("ERROR::File not found",hosts)
            exit(0)
    for lineHost in hostList:
        print("Running commands for",lineHost.strip(),"...please wait")
        try:
            session = pexpect.spawn(
                "ssh -l " + username + " -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "
                "-o PubkeyAuthentication=no " + lineHost.strip(), timeout=3, maxread=65535)
            session.expect('.*assword.')
            session.sendline(password)
            session.expect(r'> $')
        except:
            print("Unable to connect to",lineHost.strip(),"using ssh... trying telnet")
            try:
                session = pexpect.spawn("telnet " + lineHost.strip(), timeout=3, maxread=65535)
                session.expect('sername.')
                session.sendline(username)
                session.expect('.*assword.')
                session.sendline(password)
                session.expect(r'> $')
            except:
                print("Unable to connect to",lineHost.strip(),"using telnet... giving up\n")
                failedhosts.append(lineHost.strip())
                continue
        filesSaved.append(lineHost.strip() + "-" + timestamp)
        results = open(lineHost.strip() + "-" + timestamp, 'w')
        session.sendline("set cli screen-length 0")
        session.expect(r'> $')
        for lineCommand in exCommands:
            _run_command(lineCommand, results, lineHost, session)
        session.sendline("exit")
        output = '\n******************************\n***********complete***********\n******************************\n'
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
            print(failed)
else:
    exit(0)
