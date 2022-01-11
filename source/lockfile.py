"""This module allows writing and reading files by preventing external 
programs from accessing the file while it is in use.

WARNING: At the moment a real blocking is only achieved on Windows, on the 
other platforms only a warning will be produced, so it will still be 
possible to manipulate the files from external programs. 

Example:
file = LockFile("file.txt", "w")
file.Write("text")
file.Close()
"""
__version__ = "0.1"
__author__ = "Frank Cedano <frankcedano64@gmail.com>"

__all__ = ["Open", "LockFile"]

from io import UnsupportedOperation
from os.path import exists, sep, splitdrive
from sys import platform

if platform.startswith("win32"):
    from ctypes import WinDLL, byref, cast, c_char, c_char_p, c_void_p, sizeof
    from ctypes.wintypes import (
        DWORD, BOOL, HANDLE, HLOCAL, LARGE_INTEGER, LPDWORD, LPWSTR,
        PLARGE_INTEGER)

    kernel32 = WinDLL("KERNEL32")

    # Manage files:
    _CreateFile = kernel32.CreateFileW
    _SetFilePointer = kernel32.SetFilePointerEx
    _WriteFile = kernel32.WriteFile
    _ReadFile = kernel32.ReadFile
    _CloseHandle = kernel32.CloseHandle

    # Other functions:
    _GetLastError = kernel32.GetLastError
    _FormatMessage = kernel32.FormatMessageW
    _LocalFree = kernel32.LocalFree
    _GetFileSize = kernel32.GetFileSizeEx

    # Set arguments and returns:
    _CreateFile.argtypes = (
        LPWSTR, DWORD, DWORD, c_void_p, DWORD, DWORD, HANDLE)
    _CreateFile.restype = HANDLE

    _SetFilePointer.argtypes = (HANDLE, LARGE_INTEGER, PLARGE_INTEGER, DWORD)
    _SetFilePointer.restype = BOOL

    _WriteFile.argtypes = (HANDLE, c_void_p, DWORD, LPDWORD, c_void_p)
    _WriteFile.restype = BOOL

    _ReadFile.argtypes = (HANDLE, c_void_p, DWORD, LPDWORD, c_void_p)
    _ReadFile.restype = BOOL

    _CloseHandle.argtypes = (HANDLE,)

    _GetLastError.restype = DWORD

    _FormatMessage.argtypes = (
        DWORD, c_void_p, DWORD, DWORD, LPWSTR, DWORD, c_void_p)
    _FormatMessage.restype = DWORD

    _LocalFree.argtypes = (HLOCAL,)
    _LocalFree.restype = HLOCAL

    _GetFileSize.argtypes = (HANDLE, PLARGE_INTEGER)
    _GetFileSize.restype = BOOL

    def _MAKELANGID(primary: int, sublang: int) -> int:
        # Gets the user's language code.
        return (primary & 0xFF) | (sublang & 0xFF) << 16

    def _GetMessageError() -> str:
        # Gets the error message corresponding to the action performed.
        errorcode = _GetLastError()
        if errorcode == 0: return None

        message = LPWSTR()

        out_FM = _FormatMessage(
            0x00000100 | 0x00001000 | 0x00000200,
            None, errorcode, _MAKELANGID(0x00, 0x01),
            cast(byref(message), LPWSTR), 0, None)

        if out_FM == 0: return None

        out = message.value
        _LocalFree(message)

        return out

    def _GetAddress(_object) -> int:
        # Gets the memory address of one of C.
        address = str(byref(_object))
        return int(address[address.find("(")+1:address.find(")")], 16)

    # Modes:
    WRITEMODE = 1073741824
    READMODE = -2147483648
    APPENDMODE = WRITEMODE
    WRITEANDREADMODE = WRITEMODE | READMODE

else:
    from fcntl import LOCK_EX, LOCK_NB, flock
    from io import IOBase
    from os.path import getsize

    # Modes:
    WRITEMODE = "w"
    READMODE = "r"
    APPENDMODE = "a"
    WRITEANDREADMODE = "r+"

# Maximum data per iteration
MAXDATAPERITE = 100000

class LockFile:
    def __init__(self, filename: str=None, 
                    mode: str=None, encoding: str=None):
        self.__modes = ('w', 'r', 'a', 'rw',
                        'wb', 'rb', 'ab', 'rwb')
        self._filename = ""
        self._mode = None
        self.__file = None
        self.__binary = False

        if filename != None or mode != None:
            self.Open(filename, mode, encoding)

    def Open(self, filename: str, mode: str, encoding: str=None):
        """Opens the specified file.

        Arguments: 
        filename: A string with the name of the file to be manipulated.

        mode: A string with the mode in which you want to manipulate the 
        file. Valid modes are:

            w: To open files in write mode. If the file exists it will be 
            replaced by a new one that is completely empty.
            wb: Same as "w" mode but in binary.
            r: To open files in read mode. If the file does not exist an 
            exception is thrown.
            rb: Same as "r" mode but in binary.
            a: To open files in write mode. Unlike the "w" mode when a file 
            is opened in this mode the data contained in the file is kept 
            and the cursor is positioned on the last character, and if the 
            file does not exist an exception is thrown.
            ab: Same as "a" mode but in binary.
            rw: To open files in write and read mode. If the file does not 
            exist it is created and if it does exist it is opened without 
            altering its content, positioning the cursor at the beginning.
            rwb: Same as "rw" mode but in binary.

        encoding: This argument is only used on non-Windows operating 
        systems. On Windows, UTF-8 is used by default or ISO-8859-1 if 
        UTF-8 fails. If this argument is left None, UTF-8 will be used by 
        default.
        """

        if platform.startswith("win32"):
            if isinstance(self.__file, HANDLE) and self._filename != "":
                raise UnsupportedOperation(
                    "Close the file first before opening another one.")

        else:
            if isinstance(self.__file, IOBase) and self._filename != "":
                raise UnsupportedOperation(
                    "Close the file first before opening another one.")

        if type(filename) != str:
            raise TypeError('Only "str" and "bytes" data types are accepted.')

        if not _ValidateFileName(filename):
            raise ValueError(
                "The file name has characters that are not allowed.")

        self._filename = filename

        if not mode in self.__modes:
            raise ValueError(
                f'The "{mode}" mode is invalid. Valid modes: ' \
                + 'w, r, a, rw, wb, rb, ab and rwb')

        elif mode.startswith('rw'): # Create new or open existing.
            self._mode = WRITEANDREADMODE
            if platform.startswith("win32"):
                if not exists(filename): createdisposition = 2
                else: createdisposition = 3

        elif mode.startswith('w'): # Create new.
            self._mode = WRITEMODE
            if platform.startswith("win32"): createdisposition = 2

        elif mode.startswith('r'): # Read existing.
            if not exists(filename):
                raise FileNotFoundError(
                    f'The file "{filename}" does not exist.')

            self._mode = READMODE
            if platform.startswith("win32"): createdisposition = 3

        elif mode.startswith('a'): # Create new or open existing.    
            self._mode = APPENDMODE
            if platform.startswith("win32"):
                if not exists(filename): createdisposition = 2
                else: createdisposition = 3

        # Habilite binary mode.
        if not platform.startswith("win32") and mode.endswith("b"):
            self._mode += "b"
            self.__binary = True

        elif mode.endswith("b"):
            self.__binary = True

        if platform.startswith("win32"):
            self.__file = HANDLE(_CreateFile(
                self._filename, self._mode, 0, None,
                createdisposition, 128, None)
                )

            if self.__file == 4294967295: raise OSError(_GetMessageError())

            if mode == 'a': self.Seek(0, "end")
        
        else: # Other systems
            if encoding == None:
                encoding = "UTF-8"
            elif type(encoding) != str:
                raise TypeError('The "encoding" argument must be a string.')

            if self._mode.startswith("r+") and not exists(filename):
                open(filename, "w").close()

            if self.__binary: self.__file = open(filename, self._mode)
            else: self.__file = open(
                                filename, self._mode, encoding = encoding)

            flock(self.__file, LOCK_EX | LOCK_NB)

            self._mode = self._mode.replace("b", "")

    def Write(self, data):
        """This method is used to write data to the file, accepting byte 
        literals and strings, depending on whether the file was opened in 
        binary mode or not.
        """
        self._HaveFileOpen()

        if self.__binary and type(data) != bytes:
            raise TypeError("Only byte literals can be written.")
        elif not self.__binary and type(data) != str:
            raise TypeError("Only string literals can be written.")

        if self._mode == READMODE:
            raise UnsupportedOperation(
                "The file was not opened in write mode.")

        if platform.startswith("win32"):
            if type(data) == str: data = bytes(data, encoding = "UTF-8")
            count = 0

            while len(data) != count:
                if (len(data)-count) > MAXDATAPERITE:
                    _return = _WriteFile(
                        self.__file, data[count:], MAXDATAPERITE,
                        byref(DWORD()), None)

                    count += MAXDATAPERITE

                else:
                    _return = _WriteFile(
                        self.__file, data[count:], len(data[count:]),
                        byref(DWORD()), None)

                    count = len(data)

                if not _return: raise OSError(_GetMessageError())

        else:
            self.__file.write(data)

    def Read(self, n_chars: int=-1) -> str:
        """This method is to read the data or characters contained in the 
        file, returning a byte or string literal depending on whether the 
        file was opened in binary mode or not.

        In Windows if the file was opened in non-binary read mode the data 
        or characters read will be encoded in UTF-8 or ISO-8859-1 and in
         other systems such as Linux they will be encoded in the one chosen 
         by the user.

        Argument:
        n_chars: An integer that can be positive or negative, which will 
        determine the number of characters that will be read.
        """
        self._HaveFileOpen()

        if self._mode == WRITEMODE:
            raise UnsupportedOperation(
                "The file was not opened in read mode.")

        if type(n_chars) != int:
            raise TypeError('"n_chars" must be a integer.')

        if self.Seek(0) >= self.GetFileSize():
            n_chars = 0
        elif (self.GetFileSize()-self.Seek(0)+n_chars+1) < 0:
            n_chars = 0
        elif n_chars < 0:
            n_chars = self.GetFileSize() - self.Seek(0) + (n_chars + 1)
        elif (self.Seek(0)+n_chars) > self.GetFileSize():
            n_chars = self.GetFileSize() - self.Seek(0)

        if platform.startswith("win32"):
            out = (c_char * (sizeof(c_char)*n_chars))()
            count = 0

            while (n_chars-count) != 0:
                if (n_chars-count) > MAXDATAPERITE:
                    address = _GetAddress(out) + (sizeof(c_char)*count)

                    _return = _ReadFile(
                        self.__file, address, MAXDATAPERITE, 
                        byref(DWORD()), None)

                    count += MAXDATAPERITE

                else:
                    address = _GetAddress(out) + (sizeof(c_char)*count)

                    _return = _ReadFile(
                        self.__file, address, n_chars-count, 
                        byref(DWORD()), None)

                    count = n_chars

                if _return == False: raise OSError(_GetMessageError())

            if self.__binary: return out.raw
            else: return self._BytesToStr(out.raw)

        else:
            return self.__file.read(n_chars)

    def Seek(self, offset: int, startpoint: str="current") -> int:
        """This method is to position the file cursor where desired. Returns
         an integer with the new position.

        Arguments:
        offset: A positive or negative integer that will indicate how 
            many characters the cursor should be moved.

        startpoint: A string to determine where to start moving the cursor 
        from, the keywords that can be used are the following:
            
            begin: To start from the zero position or the beginning.
            current: To start from the current cursor position.
            end: To start from the end.
        """
        self._HaveFileOpen()

        if type(offset) != int:
            raise TypeError(
                'The argument "offset" must be a positive or negative ' \
                + 'integer.')

        if platform.startswith("win32"):
            LARGE_INTEGER_size = 2 ** (sizeof(LARGE_INTEGER) * 8)

            last_offset = self.__Seek(0, 1)

            if offset < 0 and startpoint == "begin":
                offset = 0 
            elif offset < 0 and startpoint == "end":
                self.__Seek(0, 2)
                return self.Seek(offset, "current")
            elif offset < 0 and (last_offset+offset) < 0:
                offset = -last_offset
            elif offset > (LARGE_INTEGER_size//2-1+last_offset):
                offset = LARGE_INTEGER_size // 2 - 1 - last_offset

            if startpoint == "begin": startpoint = 0
            elif startpoint == "current": startpoint = 1
            elif startpoint == "end": startpoint = 2
            else: raise ValueError(
                "Invalid value, only begin, current and end are accepted.")

            return self.__Seek(offset, startpoint)

        else:
            if startpoint == "begin":
                self.__file.seek(0)
                return self.Seek(offset, "current")

            elif startpoint == "current":
                last_offset = self.__file.tell()

                if offset < 0 and (last_offset+offset) < 0:
                    return self.__file.seek(0)
                elif offset < 0:
                    return self.__file.seek(last_offset + offset)
                elif offset == 0:
                    return self.__file.tell()
                else:
                    return self.__file.seek(last_offset + offset)

            elif startpoint == "end":
                self.__file.seek(self.GetFileSize())
                return self.Seek(offset, "current")

            else:
                raise ValueError(
                    "Invalid value, only begin, current and end are " \
                    + "accepted.")

    def Seek2(self, pos: int) -> int:
        """Unlike the "Seek" method, this method positions the cursor at the
         specified position and not in a scrolling manner. Returns an 
        integer with the new position.

        It works in the same way as the "seek" method of "open", also this 
        is equivalent to Seek(pos, "begin").
        """
        return self.Seek(pos, "begin")

    def Close(self):
        # Close the file.
        if platform.startswith("win32"):
            if isinstance(self.__file, HANDLE): _CloseHandle(self.__file)
        else:
            if isinstance(self.__file, IOBase): self.__file.close()

        self._filename = b""
        self._mode = None
        self.__file = None
        self.__binary = False

    def GetFileSize(self) -> int:
        """ The current file size is obtained. Returns an integer with the 
        new position.
        """
        self._HaveFileOpen()

        if platform.startswith("win32"):
            out = LARGE_INTEGER()
            _return = _GetFileSize(self.__file, byref(out))
            if not _return: raise OSError(_GetMessageError())
            return out.value

        else:
            return getsize(self._filename)

    def GetCursorPos(self) -> int:
        """The current cursor position is obtained, it is equivalent to 
        calling Seek(0, "current"). Returns an integer with the new 
        position.
        """
        if platform.startswith("win32"): return self.__Seek(0, 1)
        else: return self.__file.tell()

    def IsWriteable(self) -> bool: return self._mode != READMODE

    def IsReadable(self) -> bool: return self._mode != WRITEMODE

    def IsBinary(self) -> bool: return self.__binary

    def _BytesToStr(self, l_bytes: bytes) -> str:
        # Converts a byte literal to a string literal. Windows only.
        try:
            return str(l_bytes, encoding = "UTF-8")
        except UnicodeDecodeError:
            return str(l_bytes, encoding = "ISO-8859-1")

    def _HaveFileOpen(self):
        # Check if the file is open.
        if platform.startswith("win32"):
            if not isinstance(self.__file, HANDLE):
                raise UnsupportedOperation(
                    "The action cannot be performed until a file is opened.")

        else:
            if not isinstance(self.__file, IOBase):
                raise UnsupportedOperation(
                    "The action cannot be performed until a file is opened.")

    def __Seek(self, offset: int, startpoint: str) -> int:
        """Method that is called after validating everything in "Seek". 
        Windows only.
        """
        out = LARGE_INTEGER()
        _return = _SetFilePointer(self.__file, offset, byref(out), startpoint)
        if not _return: raise OSError(_GetMessageError())
        return out.value

    def __str__(self):
        return f"File: {self._filename} | Size: {self.GetFileSize()} Bytes"

    def __repr__(self): return self.__str__()

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_value, traceback): self.Close()

    def __del__(self): self.Close()


def Open(filename: str, mode: str, encoding: str=None) -> LockFile:
    """ This is the same as LockFile("file", "mode", "encoding") or 
    LockFile.Open("file", "mode", "encoding"). Returns a LockFile object.
    """
    return LockFile(filename, mode, encoding)

def _ValidateFileName(filename: str) -> bool:
    # Check if the file name is valid.
    for c in range(32):
        if chr(c) in filename: return False

    if not platform.startswith("win32"): return True

    # Windows:
    for name in (
            "CON", "PRN", "AUX", "CLOCK$", "NUL", "COM0", "COM1", "COM2",
            "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT0",
            "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8",
            "LPT9"):

        for part in filename.split(sep):
            if part.upper().startswith(name): return False

    if splitdrive(filename)[0] != '':
        filename = filename[len(splitdrive(filename)[0])+1:]
    filename = filename.split(sep)

    if platform.startswith("win32"):
        for c in ("<", ">", ":", '"', "/", "|", "?", "*"):
            for part in filename:
                if c in part: return False
    
    return True
