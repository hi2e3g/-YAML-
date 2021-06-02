
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def warning(message, *args):
    print(f"{bcolors.WARNING}{message}{args}{bcolors.ENDC}")


def error(message, *args):
    print(f"{bcolors.FAIL}{message}{args}{bcolors.ENDC}")


def debug(message, *args):
    print(f"{bcolors.OKGREEN}{message}{args}{bcolors.ENDC}")
