from ._convert import pythonic
from ._importpy import wrap_pyfunc,convert4
from ._utils import fn

@fn("system")
@convert4()
def system(command: list[str]) -> tuple[str,str,int]:
    """
    Execute a system command from Awesome environment.

    Input: command as list[int] (ASCII)
    Returns: (stdout, stderr, returncode) as strings
    """

    import subprocess

    # Convert ASCII list to string

    # Execute the command
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate()
    returncode = process.returncode

    return stdout, stderr, returncode
