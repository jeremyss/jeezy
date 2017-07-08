#!/home/jscholz/PycharmProjects/VirtEnv/bin/python3.5
import datetime
import argparse
import getpass
import pexpect
import time

_author__ = "Jeremy Scholz"


def verify_commands(exCommands, args):
    """

    This function will verify commit commands on a device that supports candidate configurations.
    It will make sure that the order of the commands are correct to check for configuration failures.

    """
    #Check Juniper device commands
    if args.j:
        if "commit" in exCommands and "commit check" not in exCommands:
            commitid = exCommands.index("commit")
            exCommands.insert(commitid, "commit check")
        elif "commit" and "commit check" in exCommands:
            if exCommands.index("commit") < exCommands.index("commit check"):
                c1 = exCommands.index("commit")
                c2 = exCommands.index("commit check")
                exCommands[c1] = "commit check"
                exCommands[c2] = "commit"

def get_prompt(thisprompt, args, enablepass):
    """

    This function will match for the device prompt and send the enable password
    or prompt the user for it if it is not set from the command line

    """
    # Check cisco prompt
    if args.c:
        if thisprompt == b'>':
            session.sendline("enable")
            session.expect(r'assword.*')
            set_enable(session, enablepass)
        elif thisprompt == b'> ':
            session.sendline("enable")
            session.expect(r'assword.*')
            set_enable(session, enablepass)

    # TODO complete Aruba prompt
    # Check Aruba prompt
    elif args.a:
        if session.expect(r'> *'):
            session.sendline("enable")
            session.expect(r'assord *')
            session.sendline(enablepass)
            session.expect(r'# *')

def set_enable(session, enablepass):
    """

    This function will check if the enable password is set and send it,
    if it is not, prompt the user for it and sent it.

    """
    if enablepass != "":
        session.sendline(enablepass)
        session.expect(r'# *')
    else:
        interactpass = getpass.getpass("Please enter enable password: ")
        session.sendline(interactpass)
        session.expect(r'# *')

def set_paging(session, args):
    """

    This function will disable the terminal from paging the output

    """
    if args.a:
        session.sendline("no paging")
        session.expect(r'# *')
    elif args.c:
        try:
            session.sendline("term length 0")
            session.expect(r'# *')
        except:
            session.sendline("terminal pager 0")
            session.expect(r'# *')
    elif args.j:
        session.sendline("set cli screen-length 0")
        session.expect(r'> *')

def run_command(prompt, command, results, lineHost, session, args):
    """

    This function is the main device interpreter

    """
    commitfailed = False
    output = str()
    output += '\n' + '*'*30 + '\n' + 'Host -> ' + lineHost.strip() \
              + '\nCommand -> ' + command + '\nPrompt -> ' + prompt + '\nMatch -> ' + str(session.after) + '\n\n'
    session.sendline(command)
    time.sleep(.5)
    session.expect(prompt + r'> *$|# *$', timeout=120)
    output += session.before.decode("utf-8") + session.after.decode("utf-8")
    #check Juniper commit for failures
    if args.j:
        if command == "commit check":
            if "error: configuration check-out failed" in output:
                session.sendline("rollback 0")
                time.sleep(2)
                session.expect(prompt + r'> *$|# *$', timeout=120)
                output += session.before.decode("utf-8") + session.after.decode("utf-8")
                session.sendline("exit")
                time.sleep(2)
                session.expect(prompt + r'> *$|# *$', timeout=120)
                output += session.before.decode("utf-8") + session.after.decode("utf-8")
                commitfailed = True

    if args.v:
        print(output)
    results.write(output)
    return commitfailed

def main():

    parser = argparse.ArgumentParser(description='Remote networking device command processor')
    parser.add_argument('-v', action='store_true', help='Output results to terminal')
    parser.add_argument('-enable', action='store_true', help='Cisco enable password')
    parser.add_argument('-host', type=str, help='Host(s) to run command on, separate multiple hosts with comma')
    parser.add_argument('-command', type=str,
                        help='Command(s) to run enclosed in \'\', separate multiple commands with comma')
    reqarg = parser.add_mutually_exclusive_group(required=True)
    reqarg.add_argument('-a', action='store_true', help='Aruba Device')
    reqarg.add_argument('-c', action='store_true', help='Cisco IOS Device')
    reqarg.add_argument('-j', action='store_true', help='Juniper Device')
    args = parser.parse_args()

    command = []
    hostList = []
    exCommands = []
    commands = ''
    hosts = ''
    failedhosts = []
    rolledback = []
    now = datetime.datetime.now()
    currentDate = now.strftime('%m-%d-%Y')
    currentTime = now.strftime('%H-%M-%S')
    timestamp = currentDate + "-" + currentTime
    filesSaved = []

    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ")

    if args.enable:
        enablepass = getpass.getpass("Enter enable password: ")
    else:
        enablepass = ''
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
            verify_commands(exCommands, args)
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
                session.expect(r'> *|# *')
            except:
                print("Unable to connect to {host} using ssh... trying telnet".format(host=lineHost.strip()))
                try:
                    session = pexpect.spawn("telnet " + lineHost.strip(), timeout=5, maxread=65535)
                    session.expect('sername.')
                    session.sendline(username)
                    session.expect('.*assword.')
                    session.sendline(password)
                    session.expect(r'> *|# *')
                except:
                    print("Unable to connect to {host} using telnet... giving up\n".format(host=lineHost.strip()))
                    failedhosts.append(lineHost.strip())
                    continue
            filesSaved.append(lineHost.strip() + "-" + timestamp)
            results = open(lineHost.strip() + "-" + timestamp, 'w')
            #session.sendline("set cli screen-length 0")


            #session.expect(r'> *')
            prompt = session.before
            prompt = prompt.decode("utf-8")
            promptnew = prompt.split('\n')
            prompt = str(promptnew[-1])
            get_prompt(session.after, args, enablepass)
            set_paging(session, args)
            for lineCommand in exCommands:
                failedcommit = run_command(prompt, lineCommand, results, lineHost, session, args)
                if failedcommit:
                    rolledback.append(lineHost.strip())
                    break
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
        if len(rolledback) > 0:
            print("\nCommit rolled back on the following hosts:\n")
            for cfail in rolledback:
                print("{cfailed}".format(cfailed=cfail))
    else:
        exit(0)

if __name__ == '__main__':
    main()
