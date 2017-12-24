#!/usr/bin/env python3
import datetime
import argparse
import getpass
import pexpect
import time
import re


_author__ = "Jeremy Scholz"


def verify_commands(exCommands, args):
    """
    This function will verify commit commands on a device that supports candidate configurations.
    It will make sure that the order of the commands are correct to check for configuration failures.

    :param exCommands:
    :param args:
    :return:

    """
    #Check Juniper device commands
    if args.j:
        findcommit = re.compile('^commit$|^commit comment.*')
        commandsre = filter(findcommit.match, exCommands)
        for commitidx in commandsre:
            if commitidx in exCommands and "commit check" not in exCommands:
                exCommands.insert(exCommands.index(commitidx), "commit check")
            if exCommands.index(commitidx) < exCommands.index("commit check"):
                cm1 = exCommands.index(commitidx)
                cm2 = exCommands.index("commit check")
                exCommands[cm2] = commitidx
                exCommands[cm1] = "commit check"


def get_os(session, afterprompt, fullmatch, args, enablepass):
    """
    This function will check that the correct device type was used

    :param session:
    :param afterprompt:
    :param fullmatch:
    :param args:
    :param enablepass:
    :return:

    """

    removeshow = re.compile('show version.*')

    # Check Aruba device
    if args.a:
        session.sendline("show version | include Aruba")
        session.expect(fullmatch, timeout=20)
        aos = session.before
        aos = re.sub(removeshow,'',aos)
        if "ArubaOS" not in aos:
            print("This is not a Aruba device\n")
            return True

    # Check Cisco device
    if args.c:
        session.sendline("show version | include Cisco")
        session.expect(fullmatch, timeout=20)
        cios = session.before
        cios = re.sub(removeshow, '', cios)
        if "Cisco Internetwork Operating System Software" not in cios:
            if "Cisco IOS Software" not in cios:
                if "Cisco Adaptive Security Appliance" not in cios:
                    if "Cisco Nexus" not in cios:
                        print("This is not a Cisco IOS/NX-OS device\n")
                        return True

    # Check Arista device
    if args.e:
        session.sendline("show version | include Arista")
        session.expect(fullmatch, timeout=20)
        eos = session.before
        eos = re.sub(removeshow, '', eos)
        if "Arista" not in eos:
            print("This is not a Arista device\n")
            return True

    # Check Juniper device
    if args.j:
        session.sendline("show version | match junos | no-more")
        session.expect(fullmatch, timeout=20)
        junos = session.before
        junos = re.sub(removeshow, '', junos)
        if "JUNOS" not in junos:
            print("This is not a Juniper device\n")
            return True

    # Check A10 device
    if args.a10:
        session.sendline("show version | include Advanced Core OS")
        session.expect(fullmatch, timeout=20)
        acos = session.before
        acos = re.sub(removeshow, '', acos)
        if "ACOS" not in acos:
            print("This is not a A10 device\n")
            return True

    # Check Brocade device
    if args.b:
        session.sendline("show version | include Brocade")
        session.expect(fullmatch, timeout=20)
        adx = session.before
        adx = re.sub(removeshow, '', adx)
        if "Brocade" not in adx:
            print("This is not a Brocade device\n")
            return True


def get_prompt(session, afterprompt, fullmatch, args, enablepass):
    """
    This function will match for the device prompt and send the enable password
    or prompt the user for it if it is not set from the command line

    :param session:
    :param afterprompt:
    :param fullmatch:
    :param args:
    :param enablepass:
    :return:

    """
    # Check cisco prompt
    if args.c:
        if (">" or "> ") in afterprompt:
            session.sendline("enable")
            session.expect(r'assword.*', timeout=20)
            set_enable(session, enablepass)

    # Check Aruba prompt
    elif args.a:
        if (">" or "> ") in afterprompt:
            session.sendline("enable")
            session.expect(r'assword.*', timeout=20)
            set_enable(session, enablepass)

    # Check Arista prompt
    elif args.e:
        if (">" or "> ") in afterprompt:
            session.sendline("enable")
            session.expect(r'assword.*', timeout=20)
            set_enable(session, enablepass)


def set_enable(session, enablepass):
    """
    This function will check if the enable password is set and send it, if it is not, prompt the user for it and sent it.

    :param session:
    :param enablepass:
    :return:

    """
    if enablepass != "":
        session.sendline(enablepass)
        try:
            session.expect(r'# *', timeout=20)
        except:
            session.close()
            print("\nUnable to get enable prompt... skipping this host\n")
    else:
        interactpass = getpass.getpass("Please enter enable password: ")
        session.sendline(interactpass)
        try:
            session.expect(r'# *', timeout=20)
        except:
            session.close()
            print("\nUnable to get enable prompt... skipping this host\n")


def set_paging(session, afterprompt, fullmatch, args):
    """
    This function will disable the terminal from paging the output

    :param session:
    :param afterprompt:
    :param fullmatch:
    :param args:
    :return:

    """
    if args.a:
        session.sendline("no paging")
        session.expect(fullmatch, timeout=20)
    if args.c:
        session.sendline("term length 0")
        session.expect(fullmatch, timeout=20)
        session.sendline("terminal pager 0")
        session.expect(fullmatch, timeout=20)
    if args.j:
        session.sendline("set cli screen-length 0")
        session.expect(fullmatch, timeout=20)
    if args.e:
        session.sendline("term length 0 ")
        session.expect(fullmatch, timeout=20)
    if args.a10:
        session.sendline("term length 0")
        session.expect(fullmatch, timeout=20)
    if args.b:
        session.sendline("term length 0")
        session.expect(fullmatch, timeout=20)


def run_command(fullmatch, command, results, lineHost, session, args):
    """
    This function is the main device interpreter

    :param fullmatch:
    :param command:
    :param results:
    :param lineHost:
    :param session:
    :param args:
    :return: commitfailed

    """
    commitfailed = False
    output = str()

    session.sendline(command)
    time.sleep(1.5)
    if session.isalive():
        session.expect(fullmatch + r'(> *$|# *$|% *$|(.*)> *$|(.*)# *$|(.*)% *$)', timeout=120)
        output += session.before + session.after
        #check Juniper commit for failures
        if args.j:
            if command == "commit check":
                if "error: configuration check-out failed" in output:
                    session.sendline("rollback 0")
                    time.sleep(2)
                    session.expect(fullmatch, timeout=120)
                    output += session.before + session.after
                    session.sendline("exit")
                    time.sleep(2)
                    session.expect(fullmatch, timeout=120)
                    output += session.before + session.after
                    commitfailed = True
        if args.v:
            print(output, end='')
        results.write(output)
        return commitfailed


def main():
    parser = argparse.ArgumentParser(description='Remote networking device command processor')
    parser.add_argument('-v', action='store_true', help='Output results to terminal')
    parser.add_argument('-enable', action='store_true', help='Enable password')
    reqarg = parser.add_mutually_exclusive_group(required=True)
    reqarg.add_argument('-a', action='store_true', help='Aruba Device')
    reqarg.add_argument('-c', action='store_true', help='Cisco IOS Device')
    reqarg.add_argument('-j', action='store_true', help='Juniper Device')
    reqarg.add_argument('-e', action='store_true', help='Arista Device')
    reqarg.add_argument('-a10', action='store_true', help='A10 Device')
    reqarg.add_argument('-b', action='store_true', help='Brocade Device')
    parser.add_argument('-y', action='store_true', help='Confirm script execution')
    reqhost = parser.add_mutually_exclusive_group(required=True)
    reqhost.add_argument('-host', type=str, help='Host(s) to run command on, separate multiple hosts with comma')
    reqhost.add_argument('-d', type=str, help='Host file')
    reqcommand = parser.add_mutually_exclusive_group(required=True)
    reqcommand.add_argument('-command', type=str,
                        help='Command(s) to run enclosed in \'\', separate multiple commands with comma')
    reqcommand.add_argument('-l', type=str, help='Commands file')

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
    wrongdevicetype = []
    noenable = []
    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ")

    firstlogin = "[^#*][>#] ?$"


    if args.enable:
        enablepass = getpass.getpass("Enter enable password: ")
    else:
        enablepass = ''

    if args.y:
        runScript = "y"
    else:
        print("Username: {user}".format(user=username))
        if args.command:
            print("Input commands: {command}".format(command=args.command))
        elif args.l:
            print("Input commands file: {inputcommands}".format(inputcommands=args.l))
        if args.host:
            print("Host list: {hostlist}".format(hostlist=args.host))
        elif args.d:
            print("Host file: {hostfile}".format(hostfile=args.d))
        runScript = input("script will run with the above configuration... procede? Y/N: ")
        runScript = str.lower(runScript)

    if runScript == "y":
        # read commands into list
        if args.command:
            exCommands = args.command.split(',')
            verify_commands(exCommands, args)
        elif args.l:
            try:
                with open (args.l, 'r') as exCommands:
                    exCommands = exCommands.read().splitlines()
                    verify_commands(exCommands, args)
            except IOError:
                print("ERROR::File not found {commandserror}".format(commandserror=args.l))
                exit(0)
        # read hosts into list
        if args.host:
            hostList = args.host.split(',')
        elif args.d:
            try:
                with open (args.d, 'r') as hostList:
                    hostList = hostList.read().splitlines()
            except IOError:
                print("ERROR::File not found {hostserror}".format(hostserror=args.d))
                exit(0)

        for lineHost in hostList:
            print("Running commands for {currenthost}...please wait".format(currenthost=lineHost.strip()))
            try:
                session = pexpect.spawn(
                    "ssh -l " + username + " -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "
                    "-o PubkeyAuthentication=no " + lineHost.strip(), timeout=10, maxread=65535, encoding="utf-8")
                session.expect('.*assword.', timeout=20)
                session.sendline(password)
                session.expect(firstlogin, timeout=20)
            except:
                print("Unable to connect to {host} using ssh... trying telnet".format(host=lineHost.strip()))
                try:
                    session = pexpect.spawn("telnet " + lineHost.strip(), timeout=10, maxread=65535, encoding="utf-8")
                    session.expect('sername.|ogin.')
                    session.sendline(username)
                    session.expect('.*assword.', timeout=20)
                    session.sendline(password)
                    session.expect(firstlogin, timeout=20)
                except:
                    print("Unable to connect to {host} using telnet... giving up\n".format(host=lineHost.strip()))
                    failedhosts.append(lineHost.strip())
                    continue
            #NEXUS doesn't seem to like this...
            if not args.c:
                session.setwinsize(80, 280)
            prompt = session.before
            promptnew = prompt.split('\n')
            prompt = str(promptnew[-1]).strip()
            #strip out Arista stuff
            prompt = prompt.replace("\x1b[5n","")
            #Build prompt for expect
            afterprompt = session.after
            runmatch = prompt + afterprompt
            stripprompt = "[>#] ?"
            runmatchfull = runmatch.strip(stripprompt)
            fullmatch = prompt + ".*[>#] ?"
            if get_os(session, afterprompt, fullmatch, args, enablepass):
                if session.isalive():
                    session.sendline("exit")
                wrongdevicetype.append(lineHost.strip())
                continue

            if args.enable or not args.enable:
                get_prompt(session, afterprompt, fullmatch, args, enablepass)
                if not session.isalive():
                    noenable.append(lineHost.strip())
                    continue
            set_paging(session, afterprompt, fullmatch, args)
            filesSaved.append(lineHost.strip() + "-" + timestamp)
            results = open(lineHost.strip() + "-" + timestamp, 'w')
            session.sendline('')
            for lineCommand in exCommands:
                failedcommit = run_command(runmatchfull, lineCommand, results, lineHost, session, args)
                if failedcommit:
                    rolledback.append(lineHost.strip())
                    break
            if session.isalive():
                session.sendline("exit")

            if args.v:
                print('\n' + '*'*30 + '\n' + '*'*11 + 'complete' + '*'*11 + '\n' + '*'*30 + '\n')
            output = "\n"
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
        if len(wrongdevicetype) > 0:
            print("\nThe following hosts were specified as the wrong device type:\n")
            for wrongdevice in wrongdevicetype:
                print("{wdevice}".format(wdevice=wrongdevice))
        if len(noenable) > 0:
            print("\nThe following hosts were not able to set the enable prompt:\n")
            for notenabled in noenable:
                print("{nenable}".format(nenable=notenabled))
    else:
        exit(0)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        exit(130)